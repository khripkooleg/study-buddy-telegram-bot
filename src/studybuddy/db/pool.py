from typing import TypeAlias

from psycopg import AsyncConnection
from psycopg.rows import DictRow, dict_row
from psycopg_pool import AsyncConnectionPool

from studybuddy.config import config

DbPool: TypeAlias = AsyncConnectionPool[AsyncConnection[DictRow]]

def create_pool() -> DbPool:
  return AsyncConnectionPool(
    conninfo = "",
    connection_class = AsyncConnection,
    kwargs = {
      "row_factory": dict_row,
      **config.db.as_connect_kwargs(),
    },
    min_size = 2,
    max_size = 15,
    max_idle = 300,
    max_lifetime = 3600,
    timeout = 30.0,
    open = False,
  )
