from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class FuturesQuote(Model):
    instrument_key: str = Field(min_length=1, max_length=200)
    underlying_key: str = Field(min_length=1, max_length=200)
    date: date
    expiry: date
    quote_timestamp: datetime
    available_at: datetime
    spot_price: float = Field(gt=0)
    futures_price: float = Field(gt=0)
    open_interest: float = Field(ge=0)
    volume: float = Field(ge=0)
    bid: float | None = Field(None, ge=0)
    ask: float | None = Field(None, ge=0)
    risk_free_rate: float = Field(0, ge=-.1, le=1)
    dividend_yield: float = Field(0, ge=-.1, le=1)
    contract_multiplier: float = Field(1, gt=0)
    adjustment_version: str = Field('unadjusted-v1', max_length=80)

    @model_validator(mode='after')
    def consistency(self):
        if self.quote_timestamp.utcoffset() is None or self.available_at.utcoffset() is None:
            raise ValueError('derivatives timestamps must include a timezone')
        if self.available_at < self.quote_timestamp:
            raise ValueError('availability cannot precede quote time')
        if self.expiry < self.date:
            raise ValueError('futures expiry cannot precede quote date')
        if self.bid is not None and self.ask is not None and self.bid > self.ask:
            raise ValueError('bid cannot exceed ask')
        return self


class OptionQuote(Model):
    contract_key: str = Field(min_length=1, max_length=240)
    underlying_key: str = Field(min_length=1, max_length=200)
    date: date
    expiry: date
    strike: float = Field(gt=0)
    option_type: Literal['CALL', 'PUT']
    quote_timestamp: datetime
    available_at: datetime
    spot_price: float = Field(gt=0)
    last_price: float | None = Field(None, ge=0)
    bid: float | None = Field(None, ge=0)
    ask: float | None = Field(None, ge=0)
    volume: float | None = Field(None, ge=0)
    open_interest: float | None = Field(None, ge=0)
    implied_volatility: float | None = Field(None, gt=0, le=10)
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    rho: float | None = None
    risk_free_rate: float = Field(0, ge=-.1, le=1)
    dividend_yield: float = Field(0, ge=-.1, le=1)
    contract_multiplier: float = Field(1, gt=0)
    exercise_style: Literal['EUROPEAN', 'AMERICAN'] = 'EUROPEAN'

    @model_validator(mode='after')
    def consistency(self):
        if self.quote_timestamp.utcoffset() is None or self.available_at.utcoffset() is None:
            raise ValueError('derivatives timestamps must include a timezone')
        if self.available_at < self.quote_timestamp:
            raise ValueError('availability cannot precede quote time')
        if self.expiry < self.date:
            raise ValueError('option expiry cannot precede quote date')
        if self.bid is not None and self.ask is not None and self.bid > self.ask:
            raise ValueError('bid cannot exceed ask')
        if self.last_price is None and (self.bid is None or self.ask is None):
            raise ValueError('last price or a complete bid/ask quote is required')
        return self


class DerivativesRequest(Model):
    snapshot_id: str = Field(min_length=1, max_length=200)
    as_of: datetime
    futures: list[FuturesQuote] = Field(default_factory=list, max_length=100000)
    options: list[OptionQuote] = Field(default_factory=list, max_length=500000)
    realized_volatility: dict[str, float] = Field(default_factory=dict)
    fair_basis_tolerance: float = Field(.001, ge=0, le=.1)
    max_quote_age_seconds: float = Field(900, gt=0, le=86400)
    max_spread_pct: float = Field(.25, gt=0, le=5)
    minimum_option_oi: float = Field(1, ge=0)

    @model_validator(mode='after')
    def point_in_time(self):
        if self.as_of.utcoffset() is None:
            raise ValueError('as_of must include a timezone')
        if not self.futures and not self.options:
            raise ValueError('at least one futures or option quote is required')
        if any(row.available_at > self.as_of for row in [*self.futures, *self.options]):
            raise ValueError('quotes must be known by as_of')
        futures_ids = [(row.instrument_key, row.date, row.expiry) for row in self.futures]
        option_ids = [(row.contract_key, row.date, row.expiry, row.strike, row.option_type) for row in self.options]
        if len(futures_ids) != len(set(futures_ids)) or len(option_ids) != len(set(option_ids)):
            raise ValueError('derivative quote identities must be unique')
        if any(value < 0 or value > 10 for value in self.realized_volatility.values()):
            raise ValueError('realized volatility must be a non-negative decimal')
        return self
