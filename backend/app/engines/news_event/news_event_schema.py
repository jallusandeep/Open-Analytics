from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SOURCE_TYPES = Literal['EXCHANGE_ANNOUNCEMENT', 'REGULATORY_FILING', 'COMPANY_PRESS_RELEASE',
                       'NEWS_WIRE', 'FINANCIAL_MEDIA', 'GENERAL_MEDIA', 'BROKER_RESEARCH',
                       'TRANSCRIPT', 'SOCIAL_MEDIA', 'OTHER']
EVENT_TYPES = Literal['EARNINGS', 'GUIDANCE', 'ORDER_WIN', 'ORDER_LOSS', 'CONTRACT', 'M_AND_A',
                      'STAKE_SALE', 'FUND_RAISE', 'BUYBACK', 'DIVIDEND', 'SPLIT', 'BONUS',
                      'RIGHTS_ISSUE', 'MANAGEMENT_CHANGE', 'BOARD_CHANGE', 'REGULATORY', 'LEGAL',
                      'FRAUD', 'GOVERNANCE', 'CREDIT_RATING', 'DEBT', 'DEFAULT', 'PRODUCT_LAUNCH',
                      'CAPACITY_EXPANSION', 'CAPEX', 'PLANT_SHUTDOWN', 'LABOUR', 'CYBERSECURITY',
                      'ACCIDENT', 'ESG', 'MACRO', 'SECTOR', 'ANALYST_ACTION', 'INSIDER_ACTIVITY', 'OTHER']


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class EntityLink(Model):
    instrument_key: str = Field(min_length=1, max_length=200)
    company_id: str | None = Field(None, max_length=200)
    sector: str | None = Field(None, max_length=160)
    industry: str | None = Field(None, max_length=160)
    relevance_score: float = Field(ge=0, le=100)
    entity_confidence: float = Field(ge=0, le=100)
    sentiment_score: float | None = Field(None, ge=-1, le=1)
    pre_event_return_1d: float | None = None
    pre_event_return_5d: float | None = None
    event_return_1d: float | None = None
    event_return_5d: float | None = None
    event_return_21d: float | None = None
    benchmark_return_1d: float | None = None
    benchmark_return_5d: float | None = None
    event_rvol: float | None = Field(None, ge=0)
    event_volatility_change: float | None = None


class NewsArticle(Model):
    article_id: str = Field(min_length=1, max_length=300)
    article_version: int = Field(1, ge=1)
    version_timestamp: datetime
    source: str = Field(min_length=1, max_length=300)
    source_type: SOURCE_TYPES
    published_at: datetime
    first_seen_at: datetime
    public_available_at: datetime
    ingested_at: datetime
    headline: str = Field(min_length=1, max_length=2000)
    body_or_summary: str = Field('', max_length=50000)
    source_reference: str = Field(min_length=1, max_length=4000)
    language: str = Field('en', min_length=2, max_length=20)
    event_type: EVENT_TYPES
    event_subtype: str | None = Field(None, max_length=120)
    sentiment_score: float = Field(ge=-1, le=1)
    headline_sentiment: float | None = Field(None, ge=-1, le=1)
    body_sentiment: float | None = Field(None, ge=-1, le=1)
    materiality_score: float = Field(ge=0, le=100)
    novelty_score: float | None = Field(None, ge=0, le=100)
    source_quality_score: float | None = Field(None, ge=0, le=100)
    event_cluster_hint: str | None = Field(None, max_length=300)
    rumor_flag: bool = False
    official_confirmation_flag: bool = False
    retracted_flag: bool = False
    correction_flag: bool = False
    surprise_score: float | None = None
    entities: list[EntityLink] = Field(min_length=1, max_length=100)

    @model_validator(mode='after')
    def timestamps(self):
        timestamps = (self.version_timestamp, self.published_at, self.first_seen_at,
                      self.public_available_at, self.ingested_at)
        if any(value.utcoffset() is None for value in timestamps):
            raise ValueError('news timestamps must include a timezone')
        if self.public_available_at < self.published_at:
            raise ValueError('public availability cannot precede publication')
        if self.version_timestamp < self.published_at:
            raise ValueError('article version cannot precede publication')
        if self.public_available_at < self.version_timestamp:
            raise ValueError('article version cannot be public before its version timestamp')
        keys = [entity.instrument_key for entity in self.entities]
        if len(keys) != len(set(keys)):
            raise ValueError('entity links must be unique per article version')
        return self


class NewsEventRequest(Model):
    snapshot_id: str = Field(min_length=1, max_length=200)
    as_of: datetime
    evaluation_times: list[datetime] = Field(min_length=1, max_length=5000)
    articles: list[NewsArticle] = Field(min_length=1, max_length=100000)
    taxonomy_version: str = Field('1', min_length=1, max_length=40)
    classifier_version: str = Field('structured-input-v1', min_length=1, max_length=100)
    sentiment_model_version: str = Field('provided-v1', min_length=1, max_length=100)
    entity_model_version: str = Field('provided-v1', min_length=1, max_length=100)
    duplicate_similarity_threshold: float = Field(.75, ge=.5, le=1)
    minimum_entity_confidence: float = Field(50, ge=0, le=100)
    minimum_source_quality: float = Field(30, ge=0, le=100)
    half_life_days: dict[str, float] = Field(default_factory=lambda: {
        'ANALYST_ACTION': 3, 'EARNINGS': 10, 'GUIDANCE': 10,
        'REGULATORY': 20, 'LEGAL': 20, 'FRAUD': 30, 'GOVERNANCE': 30,
        'DEFAULT': 30, 'OTHER': 7,
    })

    @model_validator(mode='after')
    def point_in_time(self):
        if self.as_of.utcoffset() is None or any(value.utcoffset() is None for value in self.evaluation_times):
            raise ValueError('as_of and evaluation times must include a timezone')
        if self.evaluation_times != sorted(set(self.evaluation_times)):
            raise ValueError('evaluation_times must be sorted and unique')
        if any(value > self.as_of for value in self.evaluation_times):
            raise ValueError('evaluation times cannot be after as_of')
        identities = [(item.article_id, item.article_version) for item in self.articles]
        if len(identities) != len(set(identities)):
            raise ValueError('article versions must be unique')
        if any(item.version_timestamp > self.as_of or item.public_available_at > self.as_of for item in self.articles):
            raise ValueError('article versions must be known by as_of')
        if any(value <= 0 for value in self.half_life_days.values()):
            raise ValueError('event half-lives must be positive')
        return self
