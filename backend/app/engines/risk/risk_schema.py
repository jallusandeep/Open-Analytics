from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.engines.returns.returns_schema import ReturnsRequest


COMPONENTS = {'volatility', 'downside', 'beta', 'drawdown', 'var', 'cvar', 'idiosyncratic'}


class RiskOptions(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    annualization_sessions: int = Field(252, ge=1, le=366)
    minimum_coverage: float = Field(1.0, ge=0.8, le=1)
    minimum_beta_observations: int = Field(20, ge=3, le=1260)
    minimum_tail_observations: int = Field(100, ge=60, le=1260)
    minimum_rank_count: int = Field(3, ge=2, le=500)
    historical_rank_window: int = Field(252, ge=21, le=1260)
    minimum_historical_observations: int = Field(21, ge=2, le=1260)
    ewma_lambda: float = Field(0.94, gt=0, lt=1)
    downside_target_type: Literal['ZERO', 'MINIMUM_ACCEPTABLE', 'RISK_FREE', 'BENCHMARK'] = 'ZERO'
    minimum_acceptable_return: float | None = Field(None, gt=-1, le=1)
    large_gap_threshold: float = Field(0.03, gt=0, le=1)
    stale_sessions: int = Field(5, ge=2, le=63)
    ranking_window: Literal[21, 63, 126, 252] = 63
    winsor_lower: float = Field(0.01, ge=0, lt=0.5)
    winsor_upper: float = Field(0.99, gt=0.5, le=1)
    composite_weights: dict[str, float] = Field(default_factory=dict)
    flag_percentile: float = Field(90, ge=50, le=100)
    deep_drawdown_threshold: float = Field(0.2, gt=0, le=1)

    @model_validator(mode='after')
    def explicit_configuration(self):
        import math
        if self.downside_target_type == 'MINIMUM_ACCEPTABLE' and self.minimum_acceptable_return is None:
            raise ValueError('MINIMUM_ACCEPTABLE requires a daily minimum_acceptable_return')
        if any(k not in COMPONENTS or not math.isfinite(v) or v <= 0 for k, v in self.composite_weights.items()):
            raise ValueError('Composite weights must be positive finite values for supported components')
        return self


class TradingCheck(BaseModel):
    model_config = ConfigDict(extra='forbid')
    instrument_key: str
    date: date
    available_on: date
    stale_price_flag: bool = False
    liquidity_status: Literal['LIQUID', 'ILLIQUID', 'UNKNOWN'] = 'UNKNOWN'
    trading_status: Literal['ACTIVE', 'SUSPENDED', 'DELISTED'] = 'ACTIVE'


class RiskRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    returns: ReturnsRequest
    options: RiskOptions = Field(default_factory=RiskOptions)
    trading_checks: list[TradingCheck] = Field(default_factory=list, max_length=20000)

    @model_validator(mode='after')
    def validated_basis(self):
        if self.returns.price_basis == 'raw':
            raise ValueError('Risk requires adjusted or total_return inputs; raw returns are unsupported')
        identities = [(r.instrument_key, r.date) for r in self.trading_checks]
        if len(identities) != len(set(identities)):
            raise ValueError('Duplicate trading check for instrument/date')
        return self


class RiskBuildRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    returns_run_id: str = Field(min_length=1, max_length=64)
    options: RiskOptions = Field(default_factory=RiskOptions)
    trading_checks: list[TradingCheck] = Field(default_factory=list, max_length=20000)


class CovarianceRequest(RiskBuildRequest):
    instrument_keys: list[str] = Field(min_length=2, max_length=50)
    as_of: date
    window: int = Field(63, ge=3, le=1260)

    @model_validator(mode='after')
    def unique_keys(self):
        if len(self.instrument_keys) != len(set(self.instrument_keys)):
            raise ValueError('Covariance instruments must be unique')
        return self
