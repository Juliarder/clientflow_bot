import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from sqlalchemy import select

from .config import settings
from .database import SessionLocal, init_db
from .models import Booking


dp = Dispatcher()


class BookingForm(StatesGroup):
    service = State()
    customer_name = State()
    phone = State()
    preferred_time = State()


def service_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Консультация")],
            [KeyboardButton(text="Услуга A"), KeyboardButton(text="Услуга B")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить номер телефона", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


@dp.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(BookingForm.service)

    await message.answer(
        "Здравствуйте! Я помогу оформить заявку.\n\nВыберите услугу:",
        reply_markup=service_keyboard(),
    )


@dp.message(BookingForm.service)
async def choose_service(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Пожалуйста, выберите услугу.")
        return

    await state.update_data(service=message.text)
    await state.set_state(BookingForm.customer_name)

    await message.answer(
        "Как вас зовут?",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(BookingForm.customer_name)
async def enter_name(message: Message, state: FSMContext) -> None:
    if not message.text or len(message.text.strip()) < 2:
        await message.answer("Введите имя текстом.")
        return

    await state.update_data(customer_name=message.text.strip())
    await state.set_state(BookingForm.phone)

    await message.answer(
        "Отправьте номер телефона или введите его вручную:",
        reply_markup=phone_keyboard(),
    )


@dp.message(BookingForm.phone)
async def enter_phone(message: Message, state: FSMContext) -> None:
    if message.contact:
        phone = message.contact.phone_number
    elif message.text:
        phone = message.text.strip()
    else:
        await message.answer("Введите номер телефона текстом.")
        return

    await state.update_data(phone=phone)
    await state.set_state(BookingForm.preferred_time)

    await message.answer(
        "Когда вам удобно? Например: завтра после 18:00",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(BookingForm.preferred_time)
async def enter_time(message: Message, state: FSMContext, bot: Bot) -> None:
    if not message.text:
        await message.answer("Напишите удобную дату или время текстом.")
        return

    await state.update_data(preferred_time=message.text.strip())
    data = await state.get_data()

    async with SessionLocal() as session:
        booking = Booking(
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            service=data["service"],
            customer_name=data["customer_name"],
            phone=data["phone"],
            preferred_time=data["preferred_time"],
        )
        session.add(booking)
        await session.commit()
        await session.refresh(booking)

    await message.answer(
        f"Готово! Заявка №{booking.id} принята.\n"
        "Администратор свяжется с вами.",
        reply_markup=ReplyKeyboardRemove(),
    )

    if settings.admin_telegram_id:
        username = (
            f"@{message.from_user.username}"
            if message.from_user.username
            else "не указан"
        )

        await bot.send_message(
            settings.admin_telegram_id,
            "Новая заявка\n\n"
            f"№: {booking.id}\n"
            f"Услуга: {booking.service}\n"
            f"Имя: {booking.customer_name}\n"
            f"Телефон: {booking.phone}\n"
            f"Время: {booking.preferred_time}\n"
            f"Telegram: {username}",
        )

    await state.clear()


@dp.message(Command("admin"))
async def admin(message: Message) -> None:
    if not settings.admin_telegram_id or message.from_user.id != settings.admin_telegram_id:
        await message.answer("Команда доступна только администратору.")
        return

    async with SessionLocal() as session:
        result = await session.execute(
            select(Booking).order_by(Booking.id.desc()).limit(10)
        )
        bookings = list(result.scalars())

    if not bookings:
        await message.answer("Заявок пока нет.")
        return

    lines = ["Последние заявки:\n"]

    for booking in bookings:
        lines.append(
            f"#{booking.id} | {booking.customer_name} | "
            f"{booking.service} | {booking.phone} | "
            f"{booking.preferred_time} | {booking.status}"
        )

    await message.answer("\n".join(lines))


async def main() -> None:
    await init_db()

    bot = Bot(token=settings.bot_token)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
