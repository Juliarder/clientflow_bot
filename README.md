# ClientFlow

Telegram-бот для приёма заявок, записи клиентов и базового администрирования малого бизнеса.

## MVP v0.5

Первая версия умеет:

- запускаться по команде /start;
- предлагать клиенту выбрать услугу;
- запрашивать имя;
- принимать номер телефона;
- запрашивать удобное время;
- сохранять заявку в локальную базу SQLite;
- уведомлять администратора в Telegram;
- показывать администратору последние заявки по команде /admin.

## Стек

- Python 3.11+
- aiogram 3
- SQLAlchemy 2
- SQLite (локальная разработка)
- PostgreSQL (production-ready конфигурация)
- pydantic-settings
- FastAPI
- Uvicorn

Для локальной разработки можно использовать SQLite. Для развёртывания ClientFlow подготовлен PostgreSQL через asyncpg.

## Быстрый запуск

1. Клонировать репозиторий:

```bash
git clone https://github.com/Juliarder/clientflow_bot.git
cd clientflow_bot
```

2. Создать виртуальное окружение:

```bash
python -m venv .venv
```

3. Активировать его в Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

4. Установить зависимости:

```bash
pip install -r requirements.txt
```

5. Скопировать `.env.example` в `.env` и заполнить:

```env
BOT_TOKEN=...
ADMIN_TELEGRAM_ID=...
DATABASE_URL=sqlite+aiosqlite:///./clientflow.db
ADMIN_WEB_USERNAME=admin
ADMIN_WEB_PASSWORD=замени_на_свой_пароль
```

6. Запустить бота:

```bash
python -m app.bot
```

7. Во втором терминале запустить веб-админку:

```bash
python -m uvicorn app.admin:app --reload
```

После запуска админка доступна по адресу `http://127.0.0.1:8000`.
Браузер запросит логин и пароль из `.env`.

## Сценарий клиента

```text
/start
  ↓
Выбор услуги
  ↓
Имя
  ↓
Телефон
  ↓
Желаемая дата/время
  ↓
Заявка сохраняется
  ↓
Администратор получает уведомление
```

## План развития

- [x] Базовый Telegram-бот
- [x] Сохранение заявок
- [x] Уведомление администратора
- [x] Просмотр последних заявок через /admin
- [x] Веб-админка
- [x] Статусы заявок
- [x] Telegram-уведомления клиента при изменении статуса
- [x] Поддержка PostgreSQL
- [x] Облачная PostgreSQL-база (Neon)
- [x] Production webhook для Telegram
- [x] Render Blueprint для облачного деплоя
- [ ] Публичный production deploy
- [ ] Управление услугами
- [ ] Календарь свободных слотов
- [ ] Аналитика
- [ ] AI FAQ

## Цель проекта

ClientFlow создаётся как демонстрационный коммерческий кейс: небольшая система, которую можно адаптировать под салон, частного специалиста, сервисный бизнес, консультации и другие сценарии записи клиентов.


### PostgreSQL

ClientFlow автоматически принимает обычную строку подключения вида:

```env
DATABASE_URL=postgresql://user:password@host/database
```

Внутри приложения она преобразуется в асинхронный SQLAlchemy URL для `asyncpg`.

Локальный SQLite остаётся доступен для разработки и быстрых тестов.


### Render deployment

Репозиторий содержит `render.yaml` для развёртывания одного web service.

Production-сервис одновременно:

- отдаёт веб-админку;
- принимает Telegram webhook;
- работает с PostgreSQL;
- предоставляет `/health` для health check.

Render автоматически предоставляет `RENDER_EXTERNAL_URL`, и ClientFlow использует его для регистрации Telegram webhook при старте.
