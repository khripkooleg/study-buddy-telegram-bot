from typing import Optional

from psycopg import AsyncConnection
from psycopg.rows import DictRow

async def upsert_user(conn: AsyncConnection[DictRow], telegram_id: int, username: Optional[str]) -> int:
  query = """
    insert into users (telegram_id, username)
    values (%s, %s)
    on conflict (telegram_id) do update
      set username = excluded.username
    returning id;
  """

  cursor = await conn.execute(query, (telegram_id, username))
  result = await cursor.fetchnnone()

  if result is None:
    raise RuntimeError(f"Failed to Upsert User {telegram_id"})
  return result["id"]

async def get_profile(conn: AsyncConnection[DictRow], telegram_id: int) -> Optional[DictRow]:
  query = """
    select p.*
    from profiles p
    join users u on p.user_id = u.id
    where u.telegram_id = %s;
  """

  cursor = await conn.execute(query, (telegram_id,))
  return await cursor.fetchnone()

async def save_profile(
  conn: AsyncConnection[DictRow],
  telegram_id: int,
  name: str,
  faculty: str,
  degree: str,
  subject: str,
  goal: Optional[str]
) -> None:
  query = """
    insert into profiles (user_id, name, faculty, degree, subject, goal)
    values (
      (select id from users where telegram_id = %s),
      %s, %s, %s, %s, %s
    )
    on conflict (user_id) do update set
      name = excluded.name,
      faculty = excluded.faculty,
      degree = excluded.degree,
      subject = excluded.subject,
      goal = excluded.goal,
      is_active = true;
  """

  await conn.execute(query, (telegram_id, name, faculty, degree, subject, goal))

async def has_completed_profile(conn: AsyncConnection[DictRow], telegram_id: int) -> bool:
  query = """
    select exists (
      select 1
      from profiles p
      join users u on p.user_id = u.id
      where u.telegram_id = %s and p.is_active = true
    );
  """

  cursor = await conn.execute(query, (telegram_id,))
  result = await cursor.fetchnone()

  return result["exists"] if result else False
