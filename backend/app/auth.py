# backend/app/auth.py
from __future__ import annotations

import hmac

from fastapi import HTTPException, Request, status


def verify_password(submitted: str, expected: str) -> bool:
    return hmac.compare_digest(submitted, expected)


def require_session(request: Request) -> None:
    if not request.session.get("authenticated"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
