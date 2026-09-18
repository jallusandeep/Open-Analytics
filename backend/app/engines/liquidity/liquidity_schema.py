from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class DepthLevel(Model):
    price: float = Field(gt=0, le=1e12)
    size: float = Field(ge=0, le=1e18)


class Observation(Model):
    instrument_key: str = Field(min_length=1, max_length=200)
    date: date
    available_on: date
    open: float = Field(gt=0, le=1e12)
    high: float = Field(gt=0, le=1e12)
    low: float = Field(gt=0, le=1e12)
    close: float = Field(gt=0, le=1e12)
    volume: float = Field(ge=0, le=1e18)
    adjusted_close: float | None = Field(None, gt=0, le=1e12)
    adjustment_valid: bool = False
    traded_value: float | None = Field(None, ge=0, le=1e30)
    market_cap: float | None = Field(None, gt=0, le=1e30)
    free_float_market_cap: float | None = Field(None, gt=0, le=1e30)
    trade_count: int | None = Field(None, ge=0)
    quality_valid: bool = False
    trading_status: Literal['ACTIVE', 'SUSPENDED', 'DELISTED', 'UNKNOWN'] = 'UNKNOWN'
    quote_timestamp: datetime | None = None
    observation_timestamp: datetime | None = None
    bid_price: float | None = Field(None, gt=0, le=1e12)
    ask_price: float | None = Field(None, gt=0, le=1e12)
    bid_size: float | None = Field(None, ge=0, le=1e18)
    ask_size: float | None = Field(None, ge=0, le=1e18)
    bids: list[DepthLevel] = Field(default_factory=list, max_length=50)
    asks: list[DepthLevel] = Field(default_factory=list, max_length=50)
    trade_price: float | None = Field(None, gt=0, le=1e12)
    execution_price: float | None = Field(None, gt=0, le=1e12)
    reference_price: float | None = Field(None, gt=0, le=1e12)
    side: Literal['BUY', 'SELL'] = 'BUY'
    order_value: float | None = Field(None, ge=0, le=1e30)
    position_value: float | None = Field(None, ge=0, le=1e30)
    lot_size: int | None = Field(None, gt=0)
    tick_size: float | None = Field(None, gt=0)
    order_price: float | None = Field(None, gt=0, le=1e12)
    order_shares: int | None = Field(None, gt=0)
    upper_circuit_price: float | None = Field(None, gt=0)
    lower_circuit_price: float | None = Field(None, gt=0)
    auction_flag: bool = False
    settlement_issue_flag: bool = False
    special_series_flag: bool = False
    trade_to_trade_flag: bool = False
    corporate_event_restriction: bool = False
    short_sale_available: bool | None = None
    derivatives_available: bool | None = None
    order_book_stable: bool | None = None
    delivery_quantity: float | None = Field(None, ge=0)
    delivery_percentage: float | None = Field(None, ge=0, le=100)
    block_deal_value: float | None = Field(None, ge=0)
    bulk_deal_value: float | None = Field(None, ge=0)

    @model_validator(mode='after')
    def temporal_and_price_consistency(self):
        if self.available_on < self.date:
            raise ValueError('Daily observations cannot be available before their session')
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close):
            raise ValueError('OHLC bounds are inconsistent')
        for stamp in (self.quote_timestamp, self.observation_timestamp):
            if stamp is not None and stamp.utcoffset() is None:
                raise ValueError('Quote timestamps must include a timezone')
        if self.observation_timestamp and self.observation_timestamp.date() != self.date:
            raise ValueError('Observation timestamp must belong to its session')
        if self.order_shares is not None and self.order_value is not None:
            from math import isclose
            if not isclose(self.order_value, self.order_shares*(self.order_price or self.close), rel_tol=1e-8):
                raise ValueError('order_value must match order_shares times order_price (or close)')
        if self.upper_circuit_price and self.lower_circuit_price and self.lower_circuit_price >= self.upper_circuit_price:
            raise ValueError('Circuit price bounds must be ordered')
        return self


class Membership(Model):
    instrument_key: str
    date: date
    available_on: date
    universe_id: str = Field(min_length=1)
    research_eligible: bool = True
    sector_id: str | None = None
    size_bucket: str | None = None


class LiquidityOptions(Model):
    min_adv: float = Field(1e7, gt=0, le=1e30)
    max_spread_pct: float = Field(.01, gt=0, le=1)
    min_trading_frequency: float = Field(.95, ge=0, le=1)
    max_days_to_liquidate: float = Field(5, gt=0)
    max_participation_rate: float = Field(.05, gt=0, le=1)
    min_depth_value: float = Field(0, ge=0)
    min_price: float = Field(1, gt=0)
    max_quote_age_seconds: float = Field(300, gt=0, le=86400)
    minimum_rank_count: int = Field(3, ge=2, le=500)
    require_depth: bool = True
    require_short_sale: bool = False
    require_derivatives: bool = False
    require_stable_order_book: bool = False
    max_expected_slippage_bps: float | None = Field(None, ge=0)
    max_price_impact: float | None = Field(None, ge=0)
    max_volume_cv: float | None = Field(None, ge=0)
    microcap_threshold: float = Field(5e9, gt=0)
    circuit_proximity: float = Field(.01, ge=0, le=.1)
    shock_ratio: float = Field(.5, gt=0, lt=1)
    trend_threshold: float = Field(.1, gt=0, lt=1)
    impact_coefficient: float | None = Field(None, gt=0, le=100)
    composite_weights: dict[str, float] = Field(default_factory=lambda: {'adv': .4, 'frequency': .3, 'amihud': .3})

    @model_validator(mode='after')
    def weights(self):
        import math
        if len(self.composite_weights) < 2 or any(k not in {'adv', 'frequency', 'spread', 'depth', 'amihud', 'impact'} or not math.isfinite(v) or v <= 0 for k, v in self.composite_weights.items()):
            raise ValueError('Configure at least two supported components with positive finite weights')
        if not math.isfinite(sum(self.composite_weights.values())):
            raise ValueError('Composite weight sum must be finite')
        return self


class LiquidityRequest(Model):
    snapshot_id: str = Field(min_length=1, max_length=200)
    calendar_version: str = Field(min_length=1, max_length=200)
    as_of: date
    sessions: list[date] = Field(min_length=1, max_length=10000)
    instrument_keys: list[str] = Field(min_length=1, max_length=500)
    observations: list[Observation] = Field(max_length=20000)
    memberships: list[Membership] = Field(default_factory=list, max_length=20000)
    options: LiquidityOptions = Field(default_factory=LiquidityOptions)

    @model_validator(mode='after')
    def grid(self):
        if self.sessions != sorted(set(self.sessions)) or len(self.instrument_keys) != len(set(self.instrument_keys)):
            raise ValueError('Sessions must be sorted and unique; instruments must be unique')
        if self.as_of not in self.sessions or len(self.sessions)*len(self.instrument_keys) > 20000:
            raise ValueError('as_of must be a session and the grid must not exceed 20000 rows')
        for records in (self.observations, self.memberships):
            identities = [(r.instrument_key, r.date) for r in records]
            if len(identities) != len(set(identities)):
                raise ValueError('Duplicate instrument/date input')
            if any(r.date not in self.sessions for r in records):
                raise ValueError('Input dates must be calendar sessions')
        if any(r.instrument_key not in self.instrument_keys for r in self.observations):
            raise ValueError('Observation instrument is outside the requested grid')
        return self
