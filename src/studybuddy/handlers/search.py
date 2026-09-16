from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from psycopg import AsyncConnection
from psycopg.rows import DictRow

from studybuddy.queries.profiles import get_profile, find_matching_profiles

search_router = Router(name="search")


@search_router.message(Command("search"))
async def handle_search(
    message: Message,
    db_conn: AsyncConnection[DictRow]
) -> None:
    telegram_id = message.from_user.id

    user_profile = await get_profile(db_conn, telegram_id)
    if not user_profile or not user_profile["is_active"]:
        await message.answer(
            "⚠️ <b>У тебе ще немає анкет!</b>\n\n"
            "Спочатку створи свій профіль за допомогою команди /profile, щоб шукати напарників."
        )
        return

    matches = await find_matching_profiles(db_conn, telegram_id)

    if not matches:
        await message.answer(
            "🔍 <b>На жаль, релевантних анкети поки не знайдено.</b>\n\n"
            "Спробуй перевірити пізніше або оновити свій профіль через /profile!"
        )
        return

    await message.answer(f"🎉 <b>Знайдено {len(matches)} релевантних напарників:</b>")

    for match in matches:
        username_str = f"@{match['username']}" if match["username"] else f"tg://user?id={match['telegram_id']}"
        card = (
            f"👤 <b>Ім'я:</b> {match['name']}\n"
            f"🏛 <b>Факультет:</b> {match['faculty'].upper()}\n"
            f"🎓 <b>Курс:</b> {match['degree'].upper()}\n"
            f"📚 <b>Предмет:</b> {match['subject'].title()}\n"
            f"🎯 <b>Мета:</b> {match['goal'] or 'Не вказано'}\n\n"
            f"💬 <b>Зв'язок:</b> {username_str}"
        )
        await message.answer(card)
