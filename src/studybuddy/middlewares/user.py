from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from psycopg import AsyncConnection
from psycopg.rows import DictRow

class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        event_user: User | None = data.get("event_from_user")
        db_conn: AsyncConnection[DictRow] | None = data.get("db_conn")

        if event_user and db_conn:
            cursor = await db_conn.execute(
                """
                insert into users (telegram_id, username)
                values (%s, %s)
                on conflict (telegram_id) do update set
                    username = excluded.username
                returning id;
                """,
                (event_user.id, event_user.username),
            )
            row = await cursor.fetchone()
            if row:
                data["user_db_id"] = row["id"]

            await db_conn.commit()

        return await handler(event, data)
