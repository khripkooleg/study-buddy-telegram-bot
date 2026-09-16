from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup

from psycopg import AsyncConnection
from psycopg.rows import DictRow

from studybuddy.config import config
from studybuddy.db.pool import create_pool
from studybuddy.middlewares.db import DbSessionMiddleware
from studybuddy.middlewares.user import UserMiddleware
from studybuddy.queries.profiles import upsert_user
from studybuddy.handlers.profiles import profile_router
from studybuddy.handlers.search import search_router

logger = logging.getLogger(__name__)

core_router = Router(name="core")

PROFILE_KEYBOARD = ReplyKeyboardMarkup(
  keyboard = [
    [
      KeyboardButton(text="/profile"),
      KeyboardButton(text="/search"),
    ]
  ],
  resize_keyboard = True,
  is_persistent = True,
)

WELCOME_TEXT = (
  "Вітаю! 🎓\n\n"
  "Тут ти зможеш знайти з ким готуватися до сесії, робити спільні проєкти та лабораторні роботи!\n"
  "Простими словами - тут зможеш знайти собі ідеального напарника з університету!\n\n"
  "Що для цього потрібно:\n"
  "1. Створити профіль ( свій факультет, курс, предмет )\n"
  "2. За допомогою пошукової системи підібрати найбільш релевантні анкети серед інших.\n"
  "3. Знайти спільну мову та досягти навчальних цілей!\n\n"
  "Якщо готовий(а) розпочинати, то тисни кнопку нижче, або пиши /profile , щоб створити анкету!"
)

@core_router.message(CommandStart())
async def handle_start(
  message: Message,
  db_conn: AsyncConnection[DictRow]
) -> None:
  user_id = await upsert_user(
    conn = db_conn,
    telegram_id = message.from_user.id,
    username = message.from_user.username
  )

  await db_conn.commit()

  logger.info(f"User Synced: Telegram ID {message.from_user.id} -> Internal ID {user_id}")
  await message.answer(WELCOME_TEXT, reply_markup=PROFILE_KEYBOARD)

async def main() -> None:
  logging.basicConfig(
    level = config.logging.level,
    format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
  )

  db_pool = create_pool()

  dispatcher = Dispatcher()

  dispatcher.workflow_data.update({"db_pool": db_pool})
  dispatcher.update.middleware(DbSessionMiddleware())
  dispatcher.update.middleware(UserMiddleware())

  dispatcher.include_router(core_router)
  dispatcher.include_router(profile_router)
  dispatcher.include_router(search_router)

  async with Bot(
    token = config.bot.token.get_secret_value(),
    default = DefaultBotProperties(parse_mode=ParseMode.HTML),
  ) as bot:
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Opening Database Connection Pool!...")
    await db_pool.open()
    await db_pool.wait()

    logger.info("StudyBuddy Bot Is Polling!...")
    try:
      await dispatcher.start_polling(bot)
    finally:
      logger.info("Closing Database Connection Pool!...")
      await db_pool.close()
      logger.info("StudyBuddy Bot Stopped!...")

if __name__ == "__main__":
  try:
    asyncio.run(main())
  except KeyboardInterrupt:
    logger.info("Interrupted by user, shutting down!...")
