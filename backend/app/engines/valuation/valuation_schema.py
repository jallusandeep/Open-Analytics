from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class ValuationObservation(Model):
    instrument_key: str = Field(min_length=1, max_length=200)
    date: date
    price_available_date: date
    fundamental_available_date: date
    shares_available_date: date
    price: float = Field(gt=0, le=1e12)
    shares_outstanding: float | None = Field(None, gt=0, le=1e18)
    market_cap: float | None = Field(None, gt=0, le=1e30)
    free_float_market_cap: float | None = Field(None, gt=0, le=1e30)
    sector: str | None = Field(None, max_length=160)
    industry: str | None = Field(None, max_length=160)
    size_bucket: str | None = Field(None, max_length=80)
    revenue_ttm: float | None = None
    ebitda_ttm: float | None = None
    ebit_ttm: float | None = None
    net_income_ttm: float | None = None
    eps_ttm: float | None = None
    shareholders_equity: float | None = None
    operating_cash_flow_ttm: float | None = None
    free_cash_flow_ttm: float | None = None
    total_debt: float | None = Field(None, ge=0)
    cash: float | None = Field(None, ge=0)
    preferred_equity: float | None = Field(None, ge=0)
    minority_interest: float | None = Field(None, ge=0)
    dividends_per_share_ttm: float | None = Field(None, ge=0)
    forward_eps_fy1: float | None = None
    estimate_available_date: date | None = None
    revenue_growth_yoy: float | None = None
    eps_growth_yoy: float | None = None
    fundamental_quality_score: float | None = Field(None, ge=0, le=100)
    financial_strength_score: float | None = Field(None, ge=0, le=100)
    fundamental_quality_status: str = Field('VALID', max_length=80)

    @model_validator(mode='after')
    def point_in_time(self):
        if self.price_available_date > self.date:
            raise ValueError('price must be known on the valuation date')
        if self.fundamental_available_date > self.date:
            raise ValueError('fundamentals must be known on the valuation date')
        if self.shares_available_date > self.date:
            raise ValueError('share count must be known on the valuation date')
        if self.forward_eps_fy1 is not None and (self.estimate_available_date is None or self.estimate_available_date > self.date):
            raise ValueError('forward estimates require a point-in-time availability date')
        if self.market_cap is None and self.shares_outstanding is None:
            raise ValueError('market_cap or historical shares_outstanding is required')
        if self.market_cap is not None and self.shares_outstanding is not None:
            derived = self.price*self.shares_outstanding
            if abs(self.market_cap-derived)/self.market_cap > .01:
                raise ValueError('market_cap conflicts with price and historical shares_outstanding')
        return self


class ValueWeights(Model):
    earnings_yield: float = Field(1, ge=0)
    book_to_price: float = Field(1, ge=0)
    ebit_to_ev: float = Field(1, ge=0)
    fcf_yield: float = Field(1, ge=0)
    sales_yield: float = Field(0, ge=0)


class ValuationRequest(Model):
    snapshot_id: str = Field(min_length=1, max_length=200)
    as_of: date
    observations: list[ValuationObservation] = Field(min_length=1, max_length=100000)
    stale_after_days: int = Field(550, ge=90, le=2000)
    minimum_history: int = Field(20, ge=2, le=1250)
    minimum_peer_count: int = Field(5, ge=2, le=10000)
    value_weights: ValueWeights = Field(default_factory=ValueWeights)

    @model_validator(mode='after')
    def consistent(self):
        identities = [(row.instrument_key, row.date) for row in self.observations]
        if len(identities) != len(set(identities)):
            raise ValueError('observations must be unique by instrument and date')
        if any(row.date > self.as_of for row in self.observations):
            raise ValueError('valuation observations cannot be after as_of')
        if sum(self.value_weights.model_dump().values()) <= 0:
            raise ValueError('value weights must have a positive sum')
        return self
