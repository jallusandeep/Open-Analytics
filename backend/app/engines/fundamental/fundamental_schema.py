from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class FundamentalStatement(Model):
    instrument_key: str = Field(min_length=1, max_length=200)
    company_id: str | None = Field(None, max_length=200)
    sector: str | None = Field(None, max_length=160)
    industry: str | None = Field(None, max_length=160)
    period_end_date: date
    period_type: Literal['QUARTERLY', 'ANNUAL']
    reporting_date: date | None = None
    announcement_date: date | None = None
    filing_date: date | None = None
    data_available_date: date
    revision: int = Field(0, ge=0)
    currency: str = Field('INR', min_length=3, max_length=3)
    revenue: float | None = None
    gross_profit: float | None = None
    operating_expenses: float | None = None
    ebitda: float | None = None
    ebit: float | None = None
    profit_before_tax: float | None = None
    tax_expense: float | None = None
    net_income: float | None = None
    eps: float | None = None
    cash: float | None = None
    total_assets: float | None = None
    current_assets: float | None = None
    current_liabilities: float | None = None
    inventory: float | None = None
    receivables: float | None = None
    total_debt: float | None = None
    short_term_debt: float | None = None
    long_term_debt: float | None = None
    shareholders_equity: float | None = None
    operating_cash_flow: float | None = None
    capital_expenditure: float | None = None
    investing_cash_flow: float | None = None
    financing_cash_flow: float | None = None
    free_cash_flow: float | None = None
    interest_expense: float | None = None
    depreciation_amortization: float | None = None
    shares_outstanding: float | None = None
    working_capital: float | None = None

    @model_validator(mode='after')
    def dates_and_identity(self):
        public_dates = [value for value in (self.reporting_date, self.announcement_date, self.filing_date) if value]
        if public_dates and self.data_available_date < max(public_dates):
            raise ValueError('data_available_date cannot precede a supplied public filing date')
        if self.data_available_date < self.period_end_date:
            raise ValueError('fundamentals cannot be available before period end')
        return self


class ScoreWeights(Model):
    profitability: float = Field(.35, ge=0)
    cash_quality: float = Field(.25, ge=0)
    balance_sheet: float = Field(.20, ge=0)
    stability: float = Field(.20, ge=0)


class FundamentalRequest(Model):
    snapshot_id: str = Field(min_length=1, max_length=200)
    as_of: date
    statements: list[FundamentalStatement] = Field(min_length=1, max_length=100000)
    stale_after_days: int = Field(550, ge=90, le=2000)
    trend_tolerance: float = Field(.01, ge=0, le=1)
    score_weights: ScoreWeights = Field(default_factory=ScoreWeights)

    @model_validator(mode='after')
    def consistent(self):
        identities = [(r.instrument_key, r.period_end_date, r.period_type,
                       r.data_available_date, r.revision) for r in self.statements]
        if len(identities) != len(set(identities)):
            raise ValueError('statement versions must be unique')
        if any(r.data_available_date > self.as_of for r in self.statements):
            raise ValueError('all supplied statement versions must be known by as_of')
        currencies = {}
        for row in self.statements:
            currencies.setdefault(row.instrument_key, set()).add(row.currency)
        if any(len(values) > 1 for values in currencies.values()):
            raise ValueError('currency normalization is required before calculation')
        if sum(self.score_weights.model_dump().values()) <= 0:
            raise ValueError('score weights must have a positive sum')
        return self
