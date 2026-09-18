from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PriceObservation(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    instrument_key: str = Field(min_length=1, max_length=200)
    date: date
    available_on: date
    raw_open: float | None = None
    raw_high: float | None = None
    raw_low: float | None = None
    raw_close: float | None = None
    adjusted_open: float | None = None
    adjusted_high: float | None = None
    adjusted_low: float | None = None
    adjusted_close: float | None = None
    total_return_close: float | None = None
    volume: float | None = None
    quality_valid: bool = False
    adjustment_valid: bool = False
    unresolved_corporate_action: bool = False
    corporate_action_flag: bool = False
    suspended: bool = False
    adjustment_source: str | None = None
    adjustment_version: str | None = None
    terminal_status: str | None = None
    risk_free_return: float | None = None

    @model_validator(mode='after')
    def availability(self):
        if self.available_on < self.date:
            raise ValueError('A completed daily candle cannot be known before its session')
        return self


class Eligibility(BaseModel):
    model_config = ConfigDict(extra='forbid')
    instrument_key: str
    date: date
    available_on: date
    eligible_horizons: list[int] = Field(max_length=30)
    universe_id: str | None = None
    sector_id: str | None = None
    benchmark_id: str | None = None
    sector_benchmark_id: str | None = None
    industry_benchmark_id: str | None = None


class ReturnsRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    snapshot_id: str = Field(min_length=1, max_length=200)
    calendar_version: str = Field(min_length=1, max_length=200)
    as_of: date
    sessions: list[date] = Field(min_length=1, max_length=10000)
    prices: list[PriceObservation] = Field(min_length=1, max_length=20000)
    eligibility: list[Eligibility] = Field(default_factory=list, max_length=20000)
    instrument_keys: list[str] = Field(min_length=1, max_length=500)
    price_basis: Literal['adjusted', 'total_return', 'raw'] = 'adjusted'
    cumulative_start: date | None = None
    gap_threshold: float = Field(default=0.005, ge=0, le=1)
    outlier_threshold: float = Field(default=0.3, gt=0, le=10)
    winsor_lower: float = Field(default=0.01, ge=0, lt=0.5)
    winsor_upper: float = Field(default=0.99, gt=0.5, le=1)
    minimum_rank_count: int = Field(default=3, ge=2, le=10000)

    @model_validator(mode='after')
    def bounded_calendar(self):
        if len(self.sessions) != len(set(self.sessions)) or self.sessions != sorted(self.sessions):
            raise ValueError('Sessions must be unique and sorted')
        if len(self.instrument_keys) != len(set(self.instrument_keys)):
            raise ValueError('instrument_keys must be unique')
        if len(self.sessions) * len(self.instrument_keys) > 20000:
            raise ValueError('Request exceeds 20000 instrument-session observations')
        identities = [(e.instrument_key, e.date) for e in self.eligibility]
        if len(identities) != len(set(identities)):
            raise ValueError('Duplicate eligibility mapping for instrument/date')
        return self


class LabelRequest(BaseModel):
    run_id: str = Field(min_length=1, max_length=64)
    horizons: list[int] = Field(default_factory=lambda: [1, 2, 5, 10, 21, 63], min_length=1, max_length=20)

    @model_validator(mode='after')
    def horizons_valid(self):
        if any(h < 1 or h > 1260 for h in self.horizons) or len(set(self.horizons)) != len(self.horizons):
            raise ValueError('Label horizons must be unique integers from 1 to 1260')
        return self
