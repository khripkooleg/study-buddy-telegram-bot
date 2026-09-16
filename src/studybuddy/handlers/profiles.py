from typing import Optional

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from psycopg import AsyncConnection
from psycopg.rows import DictRow

from studybuddy.queries.profiles import (
  get_profile, save_profile,
  deactivate_profile, delete_profile
)
from studybuddy.states import ProfileForm

profile_router = Router(name="profile")

def get_degree_keyboard():
  builder = InlineKeyboardBuilder()
  for course in ["1 курс", "2 курс", "3 курс", "4 курс", "Магістр"]:
    builder.button(text=course, callback_data=f"degree:{course}")
  builder.adjust(2)
  return builder.as_markup()

def get_profile_manage_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Перезаповнити", callback_data="profile:refill")
    builder.button(text="🙈 Деактивувати", callback_data="profile:deactivate")
    builder.button(text="🗑 Видалити", callback_data="profile:delete")
    builder.adjust(1)
    return builder.as_markup()

@profile_router.message(Command("profile"))
async def handle_profile_start(
    message: Message,
    state: FSMContext,
    db_conn: AsyncConnection[DictRow]
) -> None:
    existing = await get_profile(db_conn, message.from_user.id)

    if existing:
        status_icon = "🟢 Активний" if existing["is_active"] else "🔴 Деактивований"
        current_info = (
            f"<b>Твій поточний профіль ({status_icon}):</b>\n\n"
            f"👤 <b>Ім'я:</b> {existing['name']}\n"
            f"🏛 <b>Факультет:</b> {existing['faculty'].upper()}\n"
            f"🎓 <b>Курс:</b> {existing['degree']}\n"
            f"📚 <b>Предмет:</b> {existing['subject'].title()}\n"
            f"🎯 <b>Мета:</b> {existing['goal'] or 'Не вказано'}\n\n"
            f"Обери дію нижче:"
        )
        await message.answer(current_info, reply_markup=get_profile_manage_keyboard())
        return

    await state.set_state(ProfileForm.name)
    await message.answer("Як до тебе звертатися? Введи своє ім'я:")


@profile_router.message(ProfileForm.name)
async def process_name(message: Message, state: FSMContext) -> None:
    if not message.text or len(message.text.strip()) > 50:
        await message.answer("Будь ласка, введи коректне ім'я (до 50 символів):")
        return

    await state.update_data(name=message.text.strip())
    await state.set_state(ProfileForm.faculty)
    await message.answer("На якому факультеті ти навчаєшся? (скорочено, наприклад: ФІПТ)")


@profile_router.message(ProfileForm.faculty)
async def process_faculty(message: Message, state: FSMContext) -> None:
    if not message.text or len(message.text.strip()) > 10:
        await message.answer("Будь ласка, введи назву факультету (до 10 символів):")
        return

    await state.update_data(faculty=message.text.strip())
    await state.set_state(ProfileForm.degree)

    await message.answer(
      "Вкажи свій курс або освітній рівень:",
      reply_markup=get_degree_keyboard(),
    )

@profile_router.callback_query(ProfileForm.degree, F.data.startswith("degree:"))
async def process_degree(callback: CallbackQuery, state: FSMContext) -> None:
  selected_degree = callback.data.split(":")[1]

  await state.update_data(degree=selected_degree)
  await state.set_state(ProfileForm.subject)

  await callback.answer()
  await callback.message.answer(
    f"Обрано: <b>{selected_degree}</b>\n\nЯкий предмет зараз у пріоритеті для вивчення?"
  )


@profile_router.message(ProfileForm.subject)
async def process_subject(message: Message, state: FSMContext) -> None:
    if not message.text or len(message.text.strip()) > 50:
        await message.answer("Введи назву предмета (до 50 символів):")
        return

    await state.update_data(subject=message.text.strip())
    await state.set_state(ProfileForm.goal)
    await message.answer(
        "Яка твоя мета підготовки? (наприклад: <i>Здати сесію, Підготувати лабораторну, Написати диплом</i>)\n\n"
        "Або напиши '<b>-</b>' щоб пропустити."
    )


@profile_router.message(ProfileForm.goal)
async def process_goal(
    message: Message,
    state: FSMContext,
    db_conn: AsyncConnection[DictRow]
) -> None:
    goal_text: Optional[str] = message.text.strip() if message.text else None
    if goal_text == "-":
        goal_text = None

    data = await state.get_data()

    await save_profile(
        conn=db_conn,
        telegram_id=message.from_user.id,
        name=data["name"],
        faculty=data["faculty"],
        degree=data["degree"],
        subject=data["subject"],
        goal=goal_text,
    )
    await db_conn.commit()

    await state.clear()

    await message.answer(
        "🎉 <b>Твій профіль успішно збережено!</b>\n\n"
        "Тепер ти можеш шукати напарників для навчання за допомогою команди /search.",
        reply_markup=ReplyKeyboardRemove(),
    )

@profile_router.callback_query(F.data == "profile:refill")
async def process_profile_refill(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProfileForm.name)
    await callback.answer()
    await callback.message.answer("Розпочнемо перезаповнення! Введи своє ім'я:")


@profile_router.callback_query(F.data == "profile:deactivate")
async def process_profile_deactivate(
    callback: CallbackQuery, 
    db_conn: AsyncConnection[DictRow]
) -> None:
    success = await deactivate_profile(db_conn, callback.from_user.id)
    await db_conn.commit()
    await callback.answer()

    if success:
        await callback.message.answer(
            "🙈 <b>Твій профіль деактивовано!</b>\n\n"
            "Тебе більше не буде видно у пошуку. Щоб відновити анкету, просто натисни /profile та перествори її."
        )
    else:
        await callback.message.answer("⚠️ Не вдалося деактивувати профіль.")


@profile_router.callback_query(F.data == "profile:delete")
async def process_profile_delete(
    callback: CallbackQuery, 
    db_conn: AsyncConnection[DictRow]
) -> None:
    success = await delete_profile(db_conn, callback.from_user.id)
    await db_conn.commit()
    await callback.answer()

    if success:
        await callback.message.answer(
            "🗑 <b>Твій профіль повністю видалено з бази даних.</b>"
        )
    else:
        await callback.message.answer("⚠️ Не вдалося видалити профіль.")
