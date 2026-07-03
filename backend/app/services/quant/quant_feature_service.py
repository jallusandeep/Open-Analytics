"""Feature generation engine for quant research.

First real implementation should read OHLCV daily candles and write rows into
quant_features_daily.
"""

from __future__ import annotations


def build_quant_features() -> dict:
    """Placeholder for daily OHLCV feature generation."""
    return {
        "status": "not_implemented",
        "message": "Quant feature build is not implemented yet.",
        "next_step": "Read OHLCV rows, compute returns/momentum/volatility/volume features, and save quant_features_daily.",
    }
