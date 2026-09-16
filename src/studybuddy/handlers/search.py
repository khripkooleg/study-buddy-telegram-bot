from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from psycopg import AsyncConnection
from psycopg.rows import DictRow

from studybuddy.queries.profiles import find_matching_profiles, get_profile
from studybuddy.states import SearchState

search_router = Router(name="search")

SEARCH_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Наступний"),
            KeyboardButton(text="Назад"),
        ]
    ],
    resize_keyboard=True,
    is_persistent=True,
)

MAIN_MENU_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="/profile"),
            KeyboardButton(text="/search"),
        ]
    ],
    resize_keyboard=True,
    is_persistent=True,
)


async def send_profile_card(message: Message, match: dict) -> None:
    username_str = f"@{match['username']}" if match["username"] else f"tg://user?id={match['telegram_id']}"
    card = (
        f"👤 <b>Ім'я:</b> {match['name']}\n"
        f"🏛 <b>Факультет:</b> {match['faculty'].upper()}\n"
        f"🎓 <b>Курс:</b> {match['degree'].upper()}\n"
        f"📚 <b>Предмет:</b> {match['subject'].title()}\n"
        f"🎯 <b>Мета:</b> {match['goal'] or 'Не вказано'}\n\n"
        f"💬 <b>Зв'язок:</b> {username_str}"
    )
    await message.answer(card, reply_markup=SEARCH_KEYBOARD)


@search_router.message(Command("search"))
@search_router.message(F.text == "/search")
async def handle_search(
    message: Message,
    state: FSMContext,
    db_conn: AsyncConnection[DictRow],
) -> None:
    telegram_id = message.from_user.id

    user_profile = await get_profile(db_conn, telegram_id)
    if not user_profile or not user_profile["is_active"]:
        await message.answer(
            "⚠️ <b>У тебе ще немає анкет!</b>\n\n"
            "Спочатку створи свій профіль за допомогою команди /profile, щоб шукати напарників.",
            reply_markup=MAIN_MENU_KEYBOARD,
        )
        return

    matches = await find_matching_profiles(db_conn, telegram_id)

    if not matches:
        await message.answer(
            "🔍 <b>На жаль, релевантних анкет поки не знайдено.</b>\n\n"
            "Спробуй перевірити пізніше або оновити свій профіль через /profile!",
            reply_markup=MAIN_MENU_KEYBOARD,
        )
        return

    await state.set_state(SearchState.browsing)
    await state.update_data(matches=matches, index=0)

    await message.answer(f"🎉 <b>Знайдено {len(matches)} релевантних напарників:</b>")
    await send_profile_card(message, matches[0])


@search_router.message(SearchState.browsing, F.text == "Наступний")
async def handle_next_match(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    matches = data.get("matches", [])
    current_index = data.get("index", 0) + 1

    if current_index >= len(matches):
        await state.clear()
        await message.answer(
            "🏁 <b>Це були всі доступні анкети за вашим запитом!</b>\n\n"
            "Повертаємось до головного меню.",
            reply_markup=MAIN_MENU_KEYBOARD,
        )
        return

    await state.update_data(index=current_index)
    await send_profile_card(message, matches[current_index])


@search_router.message(SearchState.browsing, F.text == "Назад")
async def handle_go_back(
    message: Message,
    state: FSMContext,
    db_conn: AsyncConnection[DictRow],
) -> None:
    await state.clear()
    existing = await get_profile(db_conn, message.from_user.id)

    if existing:
        status_icon = "🟢 Активний" if existing["is_active"] else "🔴 Деактивований"
        current_info = (
            f"<b>Твій поточний профіль ({status_icon}):</b>\n\n"
            f"👤 <b>Ім'я:</b> {existing['name']}\n"
            f"🏛 <b>Факультет:</b> {existing['faculty'].upper()}\n"
            f"🎓 <b>Курс:</b> {existing['degree'].upper()}\n"
            f"📚 <b>Предмет:</b> {existing['subject'].title()}\n"
            f"🎯 <b>Мета:</b> {existing['goal'] or 'Не вказано'}"
        )
        await message.answer(current_info, reply_markup=MAIN_MENU_KEYBOARD)
    else:
        await message.answer("Головне меню:", reply_markup=MAIN_MENU_KEYBOARD)
