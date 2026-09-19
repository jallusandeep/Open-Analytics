from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class FlowEvaluation(Model):
    date: date
    evaluated_at: datetime

    @model_validator(mode='after')
    def timezone(self):
        if self.evaluated_at.utcoffset() is None:
            raise ValueError('evaluation timestamps must include a timezone')
        if self.evaluated_at.date() < self.date:
            raise ValueError('evaluation cannot precede the flow date')
        return self


class MarketFlowObservation(Model):
    source_date: date
    published_at: datetime
    data_available_at: datetime
    ingested_at: datetime
    revision: int = Field(0, ge=0)
    source_name: str = Field(min_length=1, max_length=200)
    source_reference: str = Field(min_length=1, max_length=2000)
    scope: str = Field('INDIA_MARKET', min_length=1, max_length=120)
    market_segment: str = Field('CASH', min_length=1, max_length=80)
    flow_definition: str = Field('GROSS_BUY_MINUS_GROSS_SELL', min_length=1, max_length=160)
    currency: str = Field('INR', min_length=3, max_length=3)
    fii_gross_buy: float | None = Field(None, ge=0)
    fii_gross_sell: float | None = Field(None, ge=0)
    fii_net: float | None = None
    dii_gross_buy: float | None = Field(None, ge=0)
    dii_gross_sell: float | None = Field(None, ge=0)
    dii_net: float | None = None
    market_turnover: float | None = Field(None, gt=0)
    market_return: float | None = None
    market_breadth: float | None = Field(None, ge=-1, le=1)
    india_vix: float | None = Field(None, ge=0)
    fii_index_futures_long: float | None = Field(None, ge=0)
    fii_index_futures_short: float | None = Field(None, ge=0)
    fii_stock_futures_long: float | None = Field(None, ge=0)
    fii_stock_futures_short: float | None = Field(None, ge=0)

    @model_validator(mode='after')
    def validate_source(self):
        stamps = (self.published_at, self.data_available_at, self.ingested_at)
        if any(value.utcoffset() is None for value in stamps):
            raise ValueError('flow timestamps must include a timezone')
        if self.data_available_at < self.published_at:
            raise ValueError('data availability cannot precede publication')
        for prefix in ('fii', 'dii'):
            buy, sell, net = (getattr(self, f'{prefix}_{name}') for name in ('gross_buy', 'gross_sell', 'net'))
            if buy is not None and sell is not None and net is not None:
                tolerance = max(1e-6, abs(net)*1e-8)
                if abs((buy-sell)-net) > tolerance:
                    raise ValueError(f'{prefix}_net conflicts with gross buy and sell')
        return self


class SectorFlowObservation(Model):
    date: date
    data_available_at: datetime
    sector_id: str = Field(min_length=1, max_length=160)
    flow_value: float
    source_name: str = Field(min_length=1, max_length=200)
    direct_observation: bool = True


class StockFlowObservation(Model):
    date: date
    data_available_at: datetime
    instrument_key: str = Field(min_length=1, max_length=200)
    institutional_buy_value: float | None = Field(None, ge=0)
    institutional_sell_value: float | None = Field(None, ge=0)
    bulk_deal_net: float | None = None
    block_deal_net: float | None = None
    fpi_holding_change: float | None = None
    mf_holding_change: float | None = None
    delivery_pct: float | None = Field(None, ge=0, le=100)
    delivery_z: float | None = None
    direct_observation: bool = False
    source_name: str = Field(min_length=1, max_length=200)


class InstitutionalFlowRequest(Model):
    snapshot_id: str = Field(min_length=1, max_length=200)
    as_of: datetime
    evaluations: list[FlowEvaluation] = Field(min_length=1, max_length=5000)
    market_observations: list[MarketFlowObservation] = Field(min_length=1, max_length=20000)
    sector_observations: list[SectorFlowObservation] = Field(default_factory=list, max_length=100000)
    stock_observations: list[StockFlowObservation] = Field(default_factory=list, max_length=100000)
    score_z_clip: float = Field(3, gt=0, le=10)

    @model_validator(mode='after')
    def consistent(self):
        if self.as_of.utcoffset() is None:
            raise ValueError('as_of must include a timezone')
        evaluation_keys = [(item.date, item.evaluated_at) for item in self.evaluations]
        if evaluation_keys != sorted(set(evaluation_keys)):
            raise ValueError('evaluations must be sorted and unique')
        if any(item.evaluated_at > self.as_of for item in self.evaluations):
            raise ValueError('evaluations cannot be after as_of')
        identities = [(item.source_date, item.data_available_at, item.revision) for item in self.market_observations]
        if len(identities) != len(set(identities)):
            raise ValueError('market flow versions must be unique')
        if any(item.data_available_at > self.as_of for item in self.market_observations):
            raise ValueError('market observations must be known by as_of')
        for rows in (self.sector_observations, self.stock_observations):
            if any(item.data_available_at.utcoffset() is None for item in rows):
                raise ValueError('flow timestamps must include a timezone')
            if any(item.data_available_at > self.as_of for item in rows):
                raise ValueError('flow observations must be known by as_of')
        definitions = {(item.source_name, item.scope, item.market_segment, item.flow_definition, item.currency)
                       for item in self.market_observations}
        if len(definitions) != 1:
            raise ValueError('market flow series requires a consistent source definition and currency')
        return self
