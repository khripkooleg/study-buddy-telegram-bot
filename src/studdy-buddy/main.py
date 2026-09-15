from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message

from studdy-buddy.config import config

logget = logging.getLogger(__name__)

core_router = Router(name="core")

WELCOME_TEXT = (
  "Hi! Test message!"
)

@core_router.message(CommandStart())
async def handle_start(message: Message) -> None:
  await message.answer(WELCOME_TEXT)

async def main() -> None:
  logging.basicConfig(
    level = config.logging.level,
    format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
  )

  dispatcher = Dispatcher()
  dispatcher.include_router(core_router)

  async with Bot(
    token = config.bot.token.get_secret_value(),
    default = DefaultBotProperties(parse_mdoe=ParseMode.HTML),
  ) as bot:
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("StudyBuddy Bot Is Polling!...")
    try:
      await dispatcher.start_polling(bot)
    finally:
      logger.info("StudyBuddy Bot Stopped!...")

if __name__ = "__main__":
  try:
    asyncio.run(main())
  except KeyboardInterrput:
    logger.info("Interrupted by user, shutting down!...")
