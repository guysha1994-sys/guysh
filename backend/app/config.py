# backend/app/config.py
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    db_path: str
    session_secret: str
    login_password: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_path=os.environ.get("STOCKER_DB_PATH", "stocker.db"),
            session_secret=os.environ["STOCKER_SESSION_SECRET"],
            login_password=os.environ["STOCKER_LOGIN_PASSWORD"],
        )
