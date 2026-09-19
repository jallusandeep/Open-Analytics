"""Validated contracts for generic, point-in-time cross-sectional rankings."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


Direction = Literal['HIGHER_IS_BETTER', 'LOWER_IS_BETTER', 'TARGET_RANGE']
Transform = Literal['NONE', 'LOG', 'SIGNED_LOG']
Winsorization = Literal['NONE', 'PERCENTILE']
Normalization = Literal['STANDARD_Z', 'ROBUST_Z', 'RANK']
PeerGroup = Literal['UNIVERSE', 'SECTOR', 'INDUSTRY', 'SUBINDUSTRY', 'SIZE', 'LIQUIDITY']


class MetricDefinition(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    metric_name: str = Field(min_length=1, max_length=120)
    source_engine: str = Field(min_length=1, max_length=80)
    description: str = Field(default='', max_length=500)
    direction: Direction
    transform: Transform = 'NONE'
    target: float | None = None
    winsorization_method: Winsorization = 'PERCENTILE'
    normalization_method: Normalization = 'ROBUST_Z'
    default_peer_group: PeerGroup = 'UNIVERSE'
    winsor_lower: float = Field(default=0.01, ge=0, lt=0.5)
    winsor_upper: float = Field(default=0.99, gt=0.5, le=1)
    minimum_peer_count: int = Field(default=5, ge=2, le=10000)
    allow_sector_neutralization: bool = True
    allow_size_neutralization: bool = True
    active: bool = True
    version: str = Field(default='1', min_length=1, max_length=40)

    @model_validator(mode='after')
    def valid_rules(self):
        if self.winsor_lower >= self.winsor_upper:
            raise ValueError('winsor_lower must be below winsor_upper')
        if self.direction == 'TARGET_RANGE' and self.target is None:
            raise ValueError('TARGET_RANGE metrics require target')
        if self.direction == 'TARGET_RANGE' and self.transform == 'LOG' and self.target <= 0:
            raise ValueError('LOG target metrics require a positive target')
        return self


class MetricObservation(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    instrument_key: str = Field(min_length=1, max_length=200)
    date: date
    available_on: date
    universe_id: str = Field(min_length=1, max_length=120)
    metric_name: str = Field(min_length=1, max_length=120)
    raw_value: float | None = None
    metric_valid: bool = True
    metric_quality_status: str = Field(default='VALID', min_length=1, max_length=80)
    sector: str | None = Field(default=None, max_length=160)
    industry: str | None = Field(default=None, max_length=160)
    sub_industry: str | None = Field(default=None, max_length=160)
    market_cap_bucket: str | None = Field(default=None, max_length=80)
    liquidity_bucket: str | None = Field(default=None, max_length=80)

    @model_validator(mode='after')
    def point_in_time(self):
        if self.available_on < self.date:
            raise ValueError('A metric cannot be available before its observation date')
        return self


class RankingRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    snapshot_id: str = Field(min_length=1, max_length=200)
    as_of: date
    sessions: list[date] = Field(min_length=1, max_length=5000)
    metrics: list[MetricDefinition] = Field(min_length=1, max_length=500)
    observations: list[MetricObservation] = Field(min_length=1, max_length=100000)
    z_clip: float | None = Field(default=3.0, gt=0, le=20)
    outlier_z: float = Field(default=3.0, gt=0, le=20)

    @model_validator(mode='after')
    def consistent_request(self):
        if self.sessions != sorted(set(self.sessions)):
            raise ValueError('sessions must be unique and sorted')
        names = [metric.metric_name for metric in self.metrics]
        if len(names) != len(set(names)):
            raise ValueError('metric definitions must be unique')
        identities = [(row.instrument_key, row.date, row.universe_id, row.metric_name) for row in self.observations]
        if len(identities) != len(set(identities)):
            raise ValueError('observations must be unique by instrument/date/universe/metric')
        known = set(names)
        if any(row.metric_name not in known for row in self.observations):
            raise ValueError('every observation requires metric metadata')
        if any(row.date not in self.sessions for row in self.observations):
            raise ValueError('every observation date must be an authoritative session')
        if any(row.date > self.as_of or row.available_on > self.as_of for row in self.observations):
            raise ValueError('observations must be known by as_of')
        return self
