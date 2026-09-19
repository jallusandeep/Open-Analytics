from datetime import datetime, timedelta, timezone

import duckdb
import pytest
from pydantic import ValidationError

from app.engines.news_event.news_event_repository import build_news_events, get_records
from app.engines.news_event.news_event_schema import NewsEventRequest
from app.engines.news_event.news_event_service import calculate_news_events

pytestmark = pytest.mark.unit
UTC = timezone.utc
T0 = datetime(2026, 3, 1, 9, tzinfo=UTC)


def article(article_id='n1', at=T0, **overrides):
    values = dict(
        article_id=article_id, article_version=1, version_timestamp=at,
        source='NSE', source_type='EXCHANGE_ANNOUNCEMENT', published_at=at,
        first_seen_at=at+timedelta(minutes=1), public_available_at=at,
        ingested_at=at+timedelta(minutes=2), headline='Acme wins major supply order',
        body_or_summary='Acme received a major multi-year supply order.',
        source_reference=f'https://example.test/{article_id}', event_type='ORDER_WIN',
        event_subtype='LARGE_ORDER', sentiment_score=.8, materiality_score=80,
        official_confirmation_flag=True, event_cluster_hint='acme-order-1',
        entities=[dict(instrument_key='NSE_EQ|ACME', company_id='ACME', sector='Industrials',
                       relevance_score=100, entity_confidence=95,
                       event_return_1d=.05, benchmark_return_1d=.01, event_rvol=2)],
    )
    values.update(overrides)
    return values


def request(articles=None, evaluations=None, **overrides):
    values = dict(snapshot_id='news-fixture', as_of=T0+timedelta(days=10),
                  evaluation_times=evaluations or [T0+timedelta(hours=12)],
                  articles=articles or [article()])
    values.update(overrides)
    return NewsEventRequest.model_validate(values)


def test_event_mapping_scores_audit_versions_and_market_reaction():
    event = calculate_news_events(request())['events'][0]
    assert event['instrument_key'] == 'NSE_EQ|ACME'
    assert event['event_type'] == 'ORDER_WIN'
    assert event['sentiment_label'] == 'VERY_POSITIVE'
    assert event['source_quality_score'] == 95
    assert event['event_confidence'] > 90
    assert event['event_abnormal_return_1d'] == pytest.approx(.04)
    assert event['event_taxonomy_version'] == '1'
    assert event['source_reference'].endswith('/n1')


def test_duplicates_cluster_and_count_once_but_confirm_independent_sources():
    duplicate = article('n2', T0+timedelta(hours=1), source='Reuters', source_type='NEWS_WIRE',
                        official_confirmation_flag=False,
                        headline='Acme secures major supply order',
                        body_or_summary='Acme secured the same multi-year supply contract.')
    result = calculate_news_events(request([article(), duplicate], [T0+timedelta(hours=2)]))
    assert len({event['event_cluster_id'] for event in result['events']}) == 1
    assert sum(event['duplicate_flag'] for event in result['events']) == 1
    assert all(event['independent_source_count'] == 2 for event in result['events'])
    feature = result['daily_features'][0]
    assert feature['news_count_24h'] == 1
    assert feature['positive_news_count_24h'] == 1


def test_future_confirmation_does_not_leak_into_earlier_daily_snapshot():
    evaluation = T0+timedelta(minutes=30)
    later = article('n2', T0+timedelta(hours=2), source='Reuters', source_type='NEWS_WIRE')
    baseline = calculate_news_events(request([article()], [evaluation]))['daily_features'][0]
    with_future = calculate_news_events(request([article(), later], [evaluation]))['daily_features'][0]
    assert with_future == baseline


def test_article_correction_supersedes_old_sentiment_only_after_version_time():
    original = article()
    corrected_at = T0+timedelta(days=1)
    corrected = article(article_version=2, at=corrected_at, published_at=T0,
                        headline='Acme order cancelled', body_or_summary='The earlier order was cancelled.',
                        sentiment_score=-.9, event_subtype='ORDER_CANCELLED', correction_flag=True,
                        novelty_score=100)
    evaluations = [T0+timedelta(hours=12), corrected_at+timedelta(hours=1)]
    features = calculate_news_events(request([original, corrected], evaluations))['daily_features']
    assert features[0]['news_sentiment_24h'] > 0
    assert features[1]['news_sentiment_24h'] < 0


def test_retraction_removes_signal_after_retraction_without_reactivating_old_version():
    original = article()
    retracted_at = T0+timedelta(hours=2)
    retraction = article(article_version=2, at=retracted_at, published_at=T0,
                         retracted_flag=True, correction_flag=True)
    evaluations = [T0+timedelta(hours=1), retracted_at+timedelta(hours=1)]
    features = calculate_news_events(request([original, retraction], evaluations))['daily_features']
    assert features[0]['news_count_24h'] == 1
    assert features[1]['news_count_24h'] == 0


def test_multi_entity_sentiment_is_specific_to_each_company():
    entities = [
        dict(instrument_key='NSE_EQ|ACME', relevance_score=100, entity_confidence=95, sentiment_score=.8),
        dict(instrument_key='NSE_EQ|RIVAL', relevance_score=80, entity_confidence=90, sentiment_score=-.5),
    ]
    result = calculate_news_events(request([article(entities=entities)]))
    events = {event['instrument_key']: event for event in result['events']}
    assert events['NSE_EQ|ACME']['sentiment_score'] == .8
    assert events['NSE_EQ|RIVAL']['sentiment_score'] == -.5
    features = {row['instrument_key']: row for row in result['daily_features']}
    assert features['NSE_EQ|ACME']['news_factor_score'] > 0
    assert features['NSE_EQ|RIVAL']['news_factor_score'] < 0


def test_quality_flags_rumor_risk_and_manual_review_remain_separate():
    fraud = article(event_type='FRAUD', sentiment_score=-1, materiality_score=95,
                    source='Social post', source_type='SOCIAL_MEDIA', source_quality_score=20,
                    official_confirmation_flag=False, rumor_flag=True)
    result = calculate_news_events(request([fraud]))
    event, feature = result['events'][0], result['daily_features'][0]
    assert event['news_quality_status'] == 'LOW_SOURCE_QUALITY'
    assert 'UNCONFIRMED_RUMOR' in event['exclusion_reasons']
    assert event['manual_review_required']
    assert feature['event_risk_score'] > 0
    assert feature['negative_catalyst_score'] > 0
    assert feature['positive_catalyst_score'] == 0


def test_schema_blocks_naive_timestamps_future_data_and_duplicate_versions():
    payload = request().model_dump()
    payload['articles'][0]['published_at'] = payload['articles'][0]['published_at'].replace(tzinfo=None)
    with pytest.raises(ValidationError, match='timezone'):
        NewsEventRequest.model_validate(payload)
    payload = request().model_dump()
    payload['articles'][0]['public_available_at'] = payload['as_of']+timedelta(days=1)
    payload['articles'][0]['version_timestamp'] = payload['articles'][0]['public_available_at']
    with pytest.raises(ValidationError, match='known by as_of'):
        NewsEventRequest.model_validate(payload)
    payload = request().model_dump()
    payload['articles'].append(payload['articles'][0])
    with pytest.raises(ValidationError, match='unique'):
        NewsEventRequest.model_validate(payload)


def test_storage_is_content_addressed_idempotent_and_queryable():
    conn = duckdb.connect(':memory:')
    try:
        first = build_news_events(conn, request())
        second = build_news_events(conn, request())
        assert second['reused'] and second['run_id'] == first['run_id']
        assert get_records(conn, first['run_id'], 'events')['total'] == 1
        assert get_records(conn, first['run_id'], 'daily_features')['total'] == 1
    finally:
        conn.close()
