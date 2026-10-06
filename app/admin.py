import secrets
from typing import Literal

from aiogram import Bot
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from sqlalchemy import select

from .config import settings
from .database import SessionLocal, init_db
from .models import Booking


app = FastAPI(title="ClientFlow Admin", version="0.3.0")
security = HTTPBasic()
bot = Bot(token=settings.bot_token)


class StatusUpdate(BaseModel):
    status: Literal["new", "in_progress", "completed", "cancelled"]


def require_admin(
    credentials: HTTPBasicCredentials = Depends(security),
) -> str:
    username_ok = secrets.compare_digest(
        credentials.username,
        settings.admin_web_username,
    )
    password_ok = secrets.compare_digest(
        credentials.password,
        settings.admin_web_password,
    )

    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


@app.on_event("startup")
async def startup() -> None:
    await init_db()


@app.on_event("shutdown")
async def shutdown() -> None:
    await bot.session.close()


@app.get("/", response_class=HTMLResponse)
async def admin_page(_: str = Depends(require_admin)) -> str:
    return ADMIN_HTML


@app.get("/api/bookings")
async def list_bookings(_: str = Depends(require_admin)) -> list[dict]:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Booking).order_by(Booking.id.desc())
        )
        bookings = list(result.scalars())

    return [
        {
            "id": booking.id,
            "customer_name": booking.customer_name,
            "phone": booking.phone,
            "service": booking.service,
            "preferred_time": booking.preferred_time,
            "status": booking.status,
            "created_at": booking.created_at.isoformat()
            if booking.created_at
            else None,
            "telegram_user_id": booking.telegram_user_id,
            "username": booking.username,
        }
        for booking in bookings
    ]


@app.patch("/api/bookings/{booking_id}/status")
async def update_booking_status(
    booking_id: int,
    payload: StatusUpdate,
    _: str = Depends(require_admin),
) -> dict:
    async with SessionLocal() as session:
        booking = await session.get(Booking, booking_id)

        if booking is None:
            raise HTTPException(status_code=404, detail="Booking not found")

        booking.status = payload.status
        await session.commit()

    status_messages = {
        "new": "Ваша заявка снова отмечена как новая.",
        "in_progress": "Ваша заявка принята в работу.",
        "completed": "Ваша заявка отмечена как завершённая.",
        "cancelled": "Ваша заявка отменена. Если это ошибка, свяжитесь с администратором.",
    }

    try:
        await bot.send_message(
            booking.telegram_user_id,
            f"ClientFlow\\n\\nЗаявка №{booking.id}: "
            f"{status_messages[payload.status]}",
        )
    except Exception:
        # Изменение статуса не должно ломаться, даже если пользователь
        # заблокировал бота или Telegram временно недоступен.
        pass

    return {"id": booking_id, "status": payload.status}


ADMIN_HTML = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ClientFlow Admin</title>
  <style>
    :root{--bg:#f4f7fb;--panel:#fff;--text:#172033;--muted:#6d7890;--line:#e6ebf2;--accent:#2f6fed;--shadow:0 12px 40px rgba(26,39,72,.08)}
    *{box-sizing:border-box} body{margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:var(--bg);color:var(--text)}
    header{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:28px 34px 18px;max-width:1500px;margin:0 auto}
    .brand h1{margin:0;font-size:28px}.brand p{margin:6px 0 0;color:var(--muted)}
    .refresh{border:0;background:var(--accent);color:#fff;padding:11px 16px;border-radius:12px;font-weight:700;cursor:pointer}
    main{max-width:1500px;margin:0 auto;padding:0 34px 40px}
    .stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-bottom:18px}
    .stat,.panel{background:var(--panel);border:1px solid var(--line);box-shadow:var(--shadow)} .stat{border-radius:16px;padding:18px}
    .stat span{display:block;color:var(--muted);font-size:13px;margin-bottom:7px}.stat strong{font-size:28px}
    .panel{border-radius:18px;overflow:hidden}.toolbar{display:flex;gap:12px;align-items:center;padding:16px 18px;border-bottom:1px solid var(--line)}
    .toolbar input,.toolbar select,.status-select{border:1px solid var(--line);border-radius:10px;padding:10px 12px;background:#fff;color:var(--text)}
    .toolbar input{flex:1;min-width:180px}.table-wrap{overflow-x:auto} table{width:100%;border-collapse:collapse;min-width:1050px}
    th,td{padding:14px 16px;text-align:left;border-bottom:1px solid var(--line);vertical-align:middle}
    th{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);background:#fafbfd} td{font-size:14px}
    .badge{display:inline-flex;border-radius:999px;padding:6px 10px;font-size:12px;font-weight:800}
    .new{background:#edf4ff;color:#235bc5}.in_progress{background:#fff6df;color:#916000}.completed{background:#eaf8ef;color:#207347}.cancelled{background:#fdecec;color:#a23a3a}
    .empty{padding:46px 20px;text-align:center;color:var(--muted)}
    @media(max-width:800px){header,main{padding-left:16px;padding-right:16px}.stats{grid-template-columns:repeat(2,1fr)}.toolbar{flex-direction:column;align-items:stretch}}
  </style>
</head>
<body>
<header>
  <div class="brand"><h1>ClientFlow</h1><p>Панель управления заявками</p></div>
  <button class="refresh" onclick="loadBookings()">Обновить</button>
</header>
<main>
  <section class="stats">
    <div class="stat"><span>Всего</span><strong id="stat-total">0</strong></div>
    <div class="stat"><span>Новые</span><strong id="stat-new">0</strong></div>
    <div class="stat"><span>В работе</span><strong id="stat-progress">0</strong></div>
    <div class="stat"><span>Завершены</span><strong id="stat-completed">0</strong></div>
  </section>
  <section class="panel">
    <div class="toolbar">
      <input id="search" placeholder="Поиск по имени, телефону или услуге" oninput="render()">
      <select id="filter" onchange="render()">
        <option value="">Все статусы</option>
        <option value="new">Новые</option>
        <option value="in_progress">В работе</option>
        <option value="completed">Завершены</option>
        <option value="cancelled">Отменены</option>
      </select>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>№</th><th>Клиент</th><th>Телефон</th><th>Услуга</th><th>Желаемое время</th><th>Создана</th><th>Статус</th><th>Изменить</th></tr></thead>
        <tbody id="rows"></tbody>
      </table>
      <div id="empty" class="empty" hidden>Заявок пока нет.</div>
    </div>
  </section>
</main>
<script>
  let bookings = [];
  const statusLabels = {new:"Новая",in_progress:"В работе",completed:"Завершена",cancelled:"Отменена"};

  async function loadBookings(){
    const response=await fetch("/api/bookings");
    if(!response.ok){alert("Не удалось загрузить заявки");return}
    bookings=await response.json();updateStats();render();
  }

  function updateStats(){
    document.getElementById("stat-total").textContent=bookings.length;
    document.getElementById("stat-new").textContent=bookings.filter(x=>x.status==="new").length;
    document.getElementById("stat-progress").textContent=bookings.filter(x=>x.status==="in_progress").length;
    document.getElementById("stat-completed").textContent=bookings.filter(x=>x.status==="completed").length;
  }

  function formatDate(v){return v?new Date(v).toLocaleString("ru-RU"):"—"}

  function escapeHtml(v){
    return String(v??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;");
  }

  function render(){
    const query=document.getElementById("search").value.trim().toLowerCase();
    const filter=document.getElementById("filter").value;
    const filtered=bookings.filter(item=>{
      const haystack=[item.customer_name,item.phone,item.service,item.preferred_time].join(" ").toLowerCase();
      return(!query||haystack.includes(query))&&(!filter||item.status===filter);
    });
    const rows=document.getElementById("rows");const empty=document.getElementById("empty");
    rows.innerHTML="";empty.hidden=filtered.length!==0;
    for(const item of filtered){
      const tr=document.createElement("tr");
      tr.innerHTML=`
        <td>#${item.id}</td>
        <td><strong>${escapeHtml(item.customer_name)}</strong></td>
        <td>${escapeHtml(item.phone)}</td>
        <td>${escapeHtml(item.service)}</td>
        <td>${escapeHtml(item.preferred_time)}</td>
        <td>${formatDate(item.created_at)}</td>
        <td><span class="badge ${item.status}">${statusLabels[item.status]??item.status}</span></td>
        <td>
          <select class="status-select" onchange="changeStatus(${item.id},this.value)">
            <option value="new" ${item.status==="new"?"selected":""}>Новая</option>
            <option value="in_progress" ${item.status==="in_progress"?"selected":""}>В работе</option>
            <option value="completed" ${item.status==="completed"?"selected":""}>Завершена</option>
            <option value="cancelled" ${item.status==="cancelled"?"selected":""}>Отменена</option>
          </select>
        </td>`;
      rows.appendChild(tr);
    }
  }

  async function changeStatus(id,newStatus){
    const response=await fetch(`/api/bookings/${id}/status`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({status:newStatus})});
    if(!response.ok){alert("Не удалось изменить статус");await loadBookings();return}
    const item=bookings.find(x=>x.id===id);if(item)item.status=newStatus;updateStats();render();
  }

  loadBookings();
</script>
</body>
</html>
"""
