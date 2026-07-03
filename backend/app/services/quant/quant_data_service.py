"""Data access helpers for quant research.

This module is intentionally small at creation time. It should later read clean OHLCV,
instruments, corporate actions, fundamentals, news, index, and sector data from DuckDB.
"""

from __future__ import annotations


def get_quant_data_readiness() -> dict:
    """Return a placeholder readiness response for the quant data layer."""
    return {
        "status": "not_implemented",
        "message": "Quant data readiness checks are not implemented yet.",
        "required_data": [
            "ohlcv_daily",
            "current_instruments",
            "expired_instruments",
            "corporate_actions",
            "market_holidays",
            "sector_mapping",
            "index_ohlcv",
            "fundamentals",
        ],
    }
