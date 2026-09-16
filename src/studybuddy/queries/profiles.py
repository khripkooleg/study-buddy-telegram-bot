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
  result = await cursor.fetchone()

  if result is None:
    raise RuntimeError(f"Failed to Upsert User {telegram_id}")
  return result["id"]

async def get_profile(conn: AsyncConnection[DictRow], telegram_id: int) -> Optional[DictRow]:
  query = """
    select p.*
    from profiles p
    join users u on p.user_id = u.id
    where u.telegram_id = %s;
  """

  cursor = await conn.execute(query, (telegram_id,))
  return await cursor.fetchone()

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
      %s,LOWER(%s), LOWER(%s), LOWER(%s), %s
    )
    on conflict (user_id) do update set
      name = excluded.name,
      faculty = excluded.faculty,
      degree = excluded.degree,
      subject = excluded.subject,
      goal = excluded.goal,
      is_active = true;
  """

  await conn.execute(
    query,
    (telegram_id, name.strip(), faculty.strip(), degree.strip(), subject.strip(), goal.strip() if goal else None)
  )

async def find_matching_profiles(
  conn: AsyncConnection[DictRow],
  telegram_id: int,
  limit: int = 10
) -> list[DictRow]:
  query = """
    with current_user_profile AS (
      select p.*
      from profiles p
      join users u on p.user_id = u.id
      where u.telegram_id = %s and p.is_active = true
    )
    select
      p.name,
      p.faculty,
      p.degree,
      p.subject,
      p.goal,
      u.username,
      u.telegram_id
    from profiles p
    join users u on p.user_id = u.id
    cross join current_user_profile cur
    where p.user_id != cur.user_id
      and p.is_active = true
      and (
        (
          p.faculty = cur.faculty
          AND (
                p.degree = cur.degree
                or p.degree like '%' || cur.degree || '%'
                or cur.degree like '%' || p.degree || '%'
          )
        )
        or
        (
          p.degree = cur.degree
          or p.degree like '%' || cur.degree || '%'
          or cur.degree like '%' || p.degree || '%'
        )
        and p.subject = cur.subject
      )
      order by
        (case when p.faculty = cur.faculty and p.degree = cur.degree and p.subject = cur.subject then 1 else 2 end)
      limit %s;
  """

  cursor = await conn.execute(query, (telegram_id, limit))
  return await cursor.fetchall()

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
  result = await cursor.fetchone()

  return result["exists"] if result else False

async def deactivate_profile(conn: AsyncConnection[DictRow], telegram_id: int) -> bool:
    query = """
        update profiles p
        set is_active = false
        from users u
        where p.user_id = u.id and u.telegram_id = %s;
    """
    cursor = await conn.execute(query, (telegram_id,))
    return cursor.rowcount > 0


async def delete_profile(conn: AsyncConnection[DictRow], telegram_id: int) -> bool:
    query = """
        delete from profiles p
        using users u
        where p.user_id = u.id and u.telegram_id = %s;
    """
    cursor = await conn.execute(query, (telegram_id,))
    return cursor.rowcount > 0
