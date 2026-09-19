from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class RegimeOptions(Model):
    trend_threshold: float = Field(.2, gt=0, lt=1)
    strong_trend_threshold: float = Field(.65, gt=0, le=1)
    return_scale: float = Field(.1, gt=0)
    slope_scale: float = Field(.002, gt=0)
    volatility_floor: float = Field(.08, ge=0)
    volatility_ceiling: float = Field(.4, gt=0)
    high_vol_enter: float = Field(70, gt=40, lt=90)
    high_vol_exit: float = Field(55, ge=0, le=100)
    stress_threshold: float = Field(75, gt=0, le=100)
    drawdown_stress: float = Field(.3, gt=0, le=1)
    minimum_breadth_coverage: float = Field(.8, ge=0, le=1)
    minimum_persistence_sessions: int = Field(1, ge=1, le=60)
    weights: dict[str, float] = Field(default_factory=lambda: {
        'trend': .35, 'breadth': .2, 'volatility': .15,
        'flow': .1, 'liquidity': .1, 'derivatives': .1,
    })
    # Advisory only: neutral until the caller supplies researched multipliers.
    risk_budget_by_regime: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode='after')
    def valid_configuration(self):
        from math import isfinite
        if self.strong_trend_threshold <= self.trend_threshold:
            raise ValueError('strong trend threshold must exceed trend threshold')
        if self.volatility_floor >= self.volatility_ceiling or self.high_vol_exit >= self.high_vol_enter:
            raise ValueError('volatility bounds and hysteresis thresholds must be ordered')
        dimensions = {'trend', 'breadth', 'volatility', 'flow', 'liquidity', 'derivatives'}
        if set(self.weights) != dimensions or any(not isfinite(v) or v < 0 for v in self.weights.values()) or sum(self.weights.values()) <= 0:
            raise ValueError('provide nonnegative weights for all six dimensions with positive total')
        labels = {f'{trend}_{vol}' for trend in ('BULL', 'BEAR', 'SIDEWAYS') for vol in ('LOW_VOL', 'HIGH_VOL')} | {'STRESS', 'RECOVERY'}
        if any(k not in labels or not isfinite(v) or not 0 <= v <= 2 for k, v in self.risk_budget_by_regime.items()):
            raise ValueError('risk budgets require known labels and multipliers between 0 and 2')
        return self


class RegimeObservation(Model):
    date: date
    available_on: date
    market_id: str = Field(min_length=1, max_length=120)
    scope: Literal['INDEX', 'SECTOR', 'GLOBAL'] = 'INDEX'
    source_reference: str = Field(min_length=1, max_length=500)
    # Decimal returns, price/MA - 1, daily decimal regression slope,
    # annualized decimal volatilities, negative decimal drawdown.
    market_return_21d: float | None = Field(None, ge=-1)
    market_return_63d: float | None = Field(None, ge=-1)
    price_vs_sma50: float | None = Field(None, ge=-1)
    price_vs_sma200: float | None = Field(None, ge=-1)
    market_slope_63d: float | None = None
    realized_volatility_21d: float | None = Field(None, ge=0)
    realized_volatility_63d: float | None = Field(None, ge=0)
    current_drawdown: float | None = Field(None, ge=-1, le=0)
    breadth_score: float | None = Field(None, ge=0, le=100)
    pct_above_sma50: float | None = Field(None, ge=0, le=1)
    pct_above_sma200: float | None = Field(None, ge=0, le=1)
    breadth_coverage: float | None = Field(None, ge=0, le=1)
    institutional_flow_score: float | None = Field(None, ge=0, le=100)
    market_liquidity_score: float | None = Field(None, ge=0, le=100)
    atm_iv: float | None = Field(None, ge=0)
    india_vix: float | None = Field(None, ge=0)
    iv_percentile: float | None = Field(None, ge=0, le=100)
    derivatives_risk_score: float | None = Field(None, ge=0, le=100)
    derivatives_sentiment_score: float | None = Field(None, ge=0, le=100)
    correlation: float | None = Field(None, ge=-1, le=1)
    cross_sectional_dispersion: float | None = Field(None, ge=0)

    @model_validator(mode='after')
    def point_in_time(self):
        if self.available_on > self.date:
            raise ValueError('all input components must be available by the classification date')
        return self


class MarketRegimeRequest(Model):
    snapshot_id: str = Field(min_length=1, max_length=200)
    as_of: date
    sessions: list[date] = Field(min_length=1, max_length=10000)
    observations: list[RegimeObservation] = Field(min_length=1, max_length=100000)
    options: RegimeOptions = Field(default_factory=RegimeOptions)

    @model_validator(mode='after')
    def consistent(self):
        if self.sessions != sorted(set(self.sessions)) or self.sessions[-1] > self.as_of:
            raise ValueError('sessions must be sorted, unique and no later than as_of')
        sessions = set(self.sessions)
        keys = [(row.date, row.scope, row.market_id) for row in self.observations]
        if len(keys) != len(set(keys)):
            raise ValueError('one observation per session, scope and market is required')
        if any(row.date not in sessions for row in self.observations):
            raise ValueError('observations require an authoritative session')
        return self
