from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from psycopg import AsyncConnection
from psycopg.rows import DictRow

from studybuddy.db.pool import DbPool

class DbSessionMiddleware(BaseMiddleware):
  async def __call__(
    self,
    handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
    event: TelegramObject,
    data: dict[str, Any],
  ) -> Any:
    pool: DbPool = data["db_pool"]
    async with pool.connection() as conn:
      db_conn: AsyncConnection[DictRow] = conn
      data["db_conn"] = db_conn
      return await handler(event, data)
