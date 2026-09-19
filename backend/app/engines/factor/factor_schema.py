from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class ComponentDefinition(Model):
    metric_name: str = Field(min_length=1, max_length=120)
    source_engine: str = Field(min_length=1, max_length=80)
    weight: float = Field(1, gt=0, le=100)
    direction: Literal['HIGHER_IS_BETTER', 'LOWER_IS_BETTER'] = 'HIGHER_IS_BETTER'
    transform: Literal['NONE', 'LOG', 'SIGNED_LOG'] = 'NONE'
    normalization: Literal['ROBUST_Z', 'STANDARD_Z', 'RANK'] = 'ROBUST_Z'
    peer_group: Literal['UNIVERSE', 'SECTOR', 'INDUSTRY'] = 'UNIVERSE'
    winsor_lower: float = Field(.01, ge=0, lt=.5)
    winsor_upper: float = Field(.99, gt=.5, le=1)

    @model_validator(mode='after')
    def bounds(self):
        if self.winsor_lower >= self.winsor_upper:
            raise ValueError('winsorization bounds must be ordered')
        return self


class FactorDefinition(Model):
    factor_name: str = Field(min_length=1, max_length=120)
    factor_version: str = Field(min_length=1, max_length=40)
    description: str = Field('', max_length=500)
    components: list[ComponentDefinition] = Field(min_length=1, max_length=50)
    minimum_component_count: int = Field(1, ge=1, le=50)
    missing_value_rule: Literal['REQUIRE_ALL', 'REQUIRE_MINIMUM_COUNT', 'RENORMALIZE_AVAILABLE_WEIGHTS'] = 'RENORMALIZE_AVAILABLE_WEIGHTS'
    neutralization: list[Literal['SECTOR', 'INDUSTRY', 'SIZE']] = Field(default_factory=list, max_length=3)
    rebalance_frequency: str = Field('DAILY', max_length=40)
    holding_horizon: int = Field(21, ge=1, le=1260)
    active: bool = True

    @model_validator(mode='after')
    def components_are_valid(self):
        names = [item.metric_name for item in self.components]
        if len(names) != len(set(names)):
            raise ValueError('factor components must be unique')
        if self.minimum_component_count > len(self.components):
            raise ValueError('minimum_component_count exceeds component count')
        if len(self.neutralization) != len(set(self.neutralization)):
            raise ValueError('neutralization steps must be unique')
        return self


class MetricObservation(Model):
    instrument_key: str = Field(min_length=1, max_length=200)
    date: date
    available_on: date
    universe_id: str = Field(min_length=1, max_length=120)
    metric_name: str = Field(min_length=1, max_length=120)
    value: float | None = None
    metric_valid: bool = True
    quality_status: str = Field('VALID', max_length=80)
    sector: str | None = Field(None, max_length=160)
    industry: str | None = Field(None, max_length=160)
    size_bucket: str | None = Field(None, max_length=80)

    @model_validator(mode='after')
    def availability(self):
        if self.available_on > self.date:
            raise ValueError('factor inputs must be available on the factor date')
        return self


class ForwardReturn(Model):
    instrument_key: str = Field(min_length=1, max_length=200)
    factor_date: date
    horizon: int = Field(ge=1, le=1260)
    return_value: float
    available_on: date

    @model_validator(mode='after')
    def realized_later(self):
        if self.available_on <= self.factor_date:
            raise ValueError('forward return must be realized after the factor date')
        return self


class FactorRequest(Model):
    snapshot_id: str = Field(min_length=1, max_length=200)
    as_of: date
    definitions: list[FactorDefinition] = Field(min_length=1, max_length=100)
    observations: list[MetricObservation] = Field(min_length=1, max_length=200000)
    forward_returns: list[ForwardReturn] = Field(default_factory=list, max_length=100000)
    minimum_peer_count: int = Field(5, ge=2, le=10000)
    composite_weights: dict[str, float] = Field(default_factory=dict)
    transaction_cost_bps: float = Field(0, ge=0, le=10000)

    @model_validator(mode='after')
    def consistent(self):
        factor_ids = [(item.factor_name, item.factor_version) for item in self.definitions]
        if len(factor_ids) != len(set(factor_ids)):
            raise ValueError('factor name/version definitions must be unique')
        metrics = {component.metric_name for factor in self.definitions for component in factor.components}
        configurations = {}
        for factor in self.definitions:
            for component in factor.components:
                signature = (component.source_engine, component.direction, component.transform,
                             component.normalization, component.peer_group,
                             component.winsor_lower, component.winsor_upper)
                previous = configurations.setdefault(component.metric_name, signature)
                if previous != signature:
                    raise ValueError('shared component metrics require consistent normalization metadata')
        if any(row.metric_name not in metrics for row in self.observations):
            raise ValueError('every observation requires a registered component')
        identities = [(row.instrument_key, row.date, row.universe_id, row.metric_name) for row in self.observations]
        if len(identities) != len(set(identities)):
            raise ValueError('metric observations must be unique')
        returns = [(row.instrument_key, row.factor_date, row.horizon) for row in self.forward_returns]
        if len(returns) != len(set(returns)):
            raise ValueError('forward returns must be unique')
        if any(row.date > self.as_of for row in self.observations) or any(row.available_on > self.as_of for row in self.forward_returns):
            raise ValueError('inputs must be known by as_of')
        active_names = {item.factor_name for item in self.definitions if item.active}
        if any(name not in active_names or weight < 0 for name, weight in self.composite_weights.items()):
            raise ValueError('composite weights require active factors and non-negative values')
        return self
