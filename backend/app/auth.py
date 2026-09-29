# backend/app/auth.py
from __future__ import annotations

import hmac

from fastapi import HTTPException, Request, status


def verify_password(submitted: str, expected: str) -> bool:
    # hmac.compare_digest raises TypeError on non-ASCII str input, so compare
    # UTF-8 bytes instead — this keeps a wrong Hebrew/emoji password a clean
    # 401 instead of a 500.
    return hmac.compare_digest(submitted.encode("utf-8"), expected.encode("utf-8"))


def require_session(request: Request) -> None:
    if not request.session.get("authenticated"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
