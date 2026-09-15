"""Bounded validation requests; raw values remain uncoerced for diagnostics."""
from datetime import date, datetime
from typing import Any, Literal
from math import isfinite

from pydantic import BaseModel, Field, model_validator


class OhlcvQualityRequest(BaseModel):
    instrument_key: str = Field(min_length=1, max_length=200)
    sessions: list[date] = Field(min_length=1, max_length=10000)
    records: list[dict[str, Any]] = Field(default_factory=list, max_length=20000)
    corporate_actions: list[dict[str, Any]] = Field(default_factory=list, max_length=10000)
    stale_sessions: int = Field(default=5, ge=2, le=1000)
    critical_missing_streak: int = Field(default=10, ge=2, le=1000)
    gap_threshold: float = Field(default=0.3, gt=0, le=10, allow_inf_nan=False)
    action_tolerance: float = Field(default=0.1, ge=0, le=0.5, allow_inf_nan=False)
    confirmed_market_moves: list[date] = Field(default_factory=list, max_length=10000)


class StoredQualityRequest(BaseModel):
    instrument_key: str = Field(min_length=1, max_length=200)
    # Explicit eligible sessions avoid guessing holiday coverage or IPO dates.
    sessions: list[date] | None = Field(default=None, min_length=1, max_length=10000)
    start_date: date | None = None
    end_date: date | None = None
    exchange: Literal['NSE', 'BSE'] = 'NSE'
    listing_date: date | None = None
    delisting_date: date | None = None
    instrument_source: Literal['current', 'expired'] = 'current'
    candle_mode: Literal['historical', 'intraday'] = 'historical'

    @model_validator(mode='after')
    def date_range(self):
        if self.sessions is None:
            if not self.start_date or not self.end_date or self.end_date < self.start_date:
                raise ValueError('Supply sessions or an ordered start_date/end_date range')
            if (self.end_date - self.start_date).days > 36600:
                raise ValueError('Date range exceeds 100 years')
        if self.listing_date and self.delisting_date and self.delisting_date < self.listing_date:
            raise ValueError('Delisting precedes listing')
        return self


class RecordsQualityRequest(BaseModel):
    dataset: Literal['fundamentals', 'news', 'corporate_actions', 'reference']
    records: list[dict[str, Any]] = Field(default_factory=list, max_length=20000)
    reference: dict[str, str] | None = None
    as_of: datetime | None = None
    expected_periods: list[date] = Field(default_factory=list, max_length=1000)
    ratio_bounds: dict[str, tuple[float | None, float | None]] | None = None

    @model_validator(mode='after')
    def validate_ratio_objects(self):
        for lower, upper in (self.ratio_bounds or {}).values():
            if any(value is not None and not isfinite(value) for value in (lower, upper)) or (lower is not None and upper is not None and lower > upper):
                raise ValueError('Ratio bounds must be finite and ordered')
        for row in self.records:
            for field in ('instrument_key', 'trading_symbol', 'url', 'title', 'published_at',
                          'action_type', 'statement_type', 'period_type', 'revision', 'currency'):
                if isinstance(row.get(field), (list, dict)):
                    raise ValueError(f'{field} must be a scalar value')
        if self.dataset == 'fundamentals' and any(
            not isinstance(row.get('ratios', {}), dict) for row in self.records
        ):
            raise ValueError('ratios must be an object of named values')
        return self


class StoredRecordsRequest(BaseModel):
    dataset: Literal['fundamentals', 'news', 'corporate_actions', 'reference']
    instrument_key: str = Field(min_length=1, max_length=200)
    expected_periods: list[date] = Field(default_factory=list, max_length=1000)
    as_of: datetime | None = None
    source: Literal['collected', 'legacy'] = 'collected'
