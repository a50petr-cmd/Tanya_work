from __future__ import annotations

import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo


def _split_employees(raw: str) -> tuple[str, ...]:
    names = []
    for part in raw.split(","):
        name = " ".join(part.split())
        if name and name != "-":
            names.append(name)
    return tuple(names)


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    telegram_chat_id: str
    forms_webhook_secret: str
    employees: tuple[str, ...]
    summary_hour: int
    summary_minute: int
    timezone: str
    database_path: str
    host: str
    port: int

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "").strip(),
            forms_webhook_secret=os.getenv("FORMS_WEBHOOK_SECRET", "").strip(),
            employees=_split_employees(os.getenv("EMPLOYEES", "")),
            summary_hour=int(os.getenv("SUMMARY_HOUR", "18")),
            summary_minute=int(os.getenv("SUMMARY_MINUTE", "0")),
            timezone=os.getenv("TZ", "Europe/Moscow"),
            database_path=os.getenv("DATABASE_PATH", "data/reports.db"),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8080")),
        )
