"""Pydantic schemas for quant research APIs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class QuantActionResponse(BaseModel):
    status: str
    message: str | None = None
    data: dict[str, Any] | None = None
