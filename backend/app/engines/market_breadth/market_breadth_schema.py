from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class BreadthObservation(Model):
    date: date
    available_on: date
    universe_id: str = Field(min_length=1, max_length=120)
    instrument_key: str = Field(min_length=1, max_length=200)
    eligible: bool = True
    membership_available_on: date
    return_1d: float | None = None
    adjusted_close: float | None = Field(None, gt=0)
    sma20: float | None = Field(None, gt=0)
    sma50: float | None = Field(None, gt=0)
    sma100: float | None = Field(None, gt=0)
    sma200: float | None = Field(None, gt=0)
    prior_high_20d: float | None = Field(None, gt=0)
    prior_low_20d: float | None = Field(None, gt=0)
    prior_high_252d: float | None = Field(None, gt=0)
    prior_low_252d: float | None = Field(None, gt=0)
    volume: float | None = Field(None, ge=0)
    traded_value: float | None = Field(None, ge=0)
    sector: str | None = Field(None, max_length=160)
    industry: str | None = Field(None, max_length=160)
    market_cap_bucket: str | None = Field(None, max_length=80)
    trend_state: str | None = Field(None, max_length=80)
    momentum_state: str | None = Field(None, max_length=80)
    trading_status: Literal['ACTIVE', 'SUSPENDED', 'DELISTED', 'UNKNOWN'] = 'ACTIVE'
    stale_price_flag: bool = False
    quality_valid: bool = True

    @model_validator(mode='after')
    def point_in_time(self):
        if self.available_on > self.date or self.membership_available_on > self.date:
            raise ValueError('breadth inputs and membership must be known on the observation date')
        return self


class IndexObservation(Model):
    date: date
    available_on: date
    universe_id: str = Field(min_length=1, max_length=120)
    index_price: float | None = Field(None, gt=0)
    index_return_1d: float | None = None

    @model_validator(mode='after')
    def point_in_time(self):
        if self.available_on > self.date:
            raise ValueError('index data must be known on the observation date')
        return self


class MarketBreadthRequest(Model):
    snapshot_id: str = Field(min_length=1, max_length=200)
    as_of: date
    sessions: list[date] = Field(min_length=1, max_length=10000)
    observations: list[BreadthObservation] = Field(min_length=1, max_length=500000)
    index_observations: list[IndexObservation] = Field(default_factory=list, max_length=10000)
    minimum_coverage: float = Field(.8, gt=0, le=1)
    unchanged_tolerance: float = Field(1e-10, ge=0, le=.01)
    minimum_sector_count: int = Field(3, ge=2, le=10000)

    @model_validator(mode='after')
    def consistent(self):
        if self.sessions != sorted(set(self.sessions)):
            raise ValueError('sessions must be sorted and unique')
        if self.as_of < self.sessions[-1]:
            raise ValueError('as_of cannot precede requested sessions')
        identities = [(row.date, row.universe_id, row.instrument_key) for row in self.observations]
        if len(identities) != len(set(identities)):
            raise ValueError('breadth observations must be unique')
        index_ids = [(row.date, row.universe_id) for row in self.index_observations]
        if len(index_ids) != len(set(index_ids)):
            raise ValueError('index observations must be unique')
        if any(row.date not in self.sessions for row in self.observations+self.index_observations):
            raise ValueError('all observations require an authoritative session')
        return self
