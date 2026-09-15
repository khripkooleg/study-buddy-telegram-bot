from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv
from pydantic import (
  BaseModel,
  ConfigDict,
  Field,
  SecretStr,
  ValidationError,
  field_validator,
)

_VALID_LOG_LEVELS: Final[frozenset[str]] = frozenset(
  {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
)

_ENV_PATH: Final[Path] = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)

class BotConfig(BaseModel):
  model_config = ConfigDict(frozen=True)

  token: SecretStr

  @field_validator("token")
  @classmethod
  def _token_not_blank(cls, value: SecretStr) -> SecretStr:
    if not value.get_secret_value().strip():
      raise ValueError("BOT_TOKEN must NOT be empty!")
    return value

class DBConfig(BaseModel):
  model_config = ConfigDict(froze=True)

  host: str = Field(min_length=1)
  port: int = Field(default=5432, ge=1, le=65535)
  name: str = Field(min_length=1)
  user: str = Field(min_length=1)
  password: SecretStr

  def as_connect_kwargs(self) -> dict[str, str | int]:
    return {
      "host": self.host,
      "port": self.port,
      "dbname": self.name,
      "user": self.user,
      "password": self.password.get_secret_value(),
    }

class LoggingConfig(BaseModel):
  model_config = ConfigDict(frozen=True)

  level: str = "INFO"

  @field_validator("level")
  @classmethod
  def _level_is_known(cls, value: str) -> str:
    upper = value.upper()
    if upper not in _VALID_LOG_LEVELS:
      raise ValueError(
        f"LOG_LEVEL must be one of {sorted(_VALID_LOG_LEVELS)}, got {value!r}"
      )
    return upper

class Config(BaseModel):
  model_config = ConfigDict(frozen=True)

  bot: BotConfig
  db: DBConfig
  logging: LoggingConfig

  @classmethod
  def load(cls) -> Config:
    try:
      return cls(
        bot = BotConfig(token = SecretStr(os.getenv("BOT_TOKEN", ""))),
        db = DBConfig(
          host = os.getenv("POSTGRES_HOST", "localhost"),
          port = int(os.getenv("POSTGRES_PORT", "5432")),
          name = os.getenv("POSTGRES_DB", ""),
          user = os.getenv("POSTGRES_USER", ""),
          password = SecretStr(os.getenv("POSTGRES_PASSWORD", "")),
        ),
        logging = LoggingConfig(level = os.getenv("LOG_LEVEL", "INFO")),
      )
    except ValidationError as exc:
      raise RuntimeError(f"Invalid configuration:\n{exc}") from exc
    except ValueError as exc:
      raise RuntimeError(f"Invalid configuration: {exc}") from exc

config: Final[Config] = Config.load()
