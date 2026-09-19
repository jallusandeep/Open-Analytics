"""Auditable event clustering and point-in-time daily news features."""
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from math import exp, log, sqrt
from statistics import fmean, pstdev
import re

from app.engines.news_event.news_event_schema import NewsEventRequest

VERSION = '1'
SOURCE_QUALITY = {
    'EXCHANGE_ANNOUNCEMENT': 95, 'REGULATORY_FILING': 95, 'COMPANY_PRESS_RELEASE': 85,
    'NEWS_WIRE': 80, 'FINANCIAL_MEDIA': 70, 'GENERAL_MEDIA': 55,
    'BROKER_RESEARCH': 65, 'TRANSCRIPT': 75, 'SOCIAL_MEDIA': 25, 'OTHER': 40,
}
RISK_TYPES = {'REGULATORY', 'LEGAL', 'FRAUD', 'GOVERNANCE', 'CREDIT_RATING', 'DEFAULT',
              'MANAGEMENT_CHANGE', 'PLANT_SHUTDOWN', 'CYBERSECURITY', 'ACCIDENT'}
MANUAL_REVIEW_TYPES = {'FRAUD', 'DEFAULT', 'M_AND_A', 'REGULATORY'}


def _tokens(text):
    return set(re.findall(r'[a-z0-9]+', text.lower()))


def _similarity(left, right):
    union = left | right
    return len(left & right)/len(union) if union else 1


def _label(sentiment):
    return ('VERY_POSITIVE' if sentiment >= .6 else 'POSITIVE' if sentiment >= .15 else
            'VERY_NEGATIVE' if sentiment <= -.6 else 'NEGATIVE' if sentiment <= -.15 else 'NEUTRAL')


def _quality(source_quality, entity_confidence, novelty, official, rumor):
    score = .4*source_quality + .3*entity_confidence + .2*novelty + (10 if official else 0)
    if rumor:
        score *= .65
    return max(0, min(100, score))


def _cluster_articles(articles, threshold):
    clusters, assignments = [], {}
    for article in sorted(articles, key=lambda item: (item.public_available_at, item.article_id, item.article_version)):
        article_tokens = _tokens(article.headline+' '+article.body_or_summary[:1000])
        entity_keys = {entity.instrument_key for entity in article.entities}
        match = None
        for cluster in clusters:
            if article.event_cluster_hint and article.event_cluster_hint == cluster['hint']:
                match = cluster; break
            if (article.event_type == cluster['event_type'] and entity_keys & cluster['entities'] and
                    _similarity(article_tokens, cluster['tokens']) >= threshold):
                match = cluster; break
        if match is None:
            cluster_id = sha256(f'{article.article_id}|{article.article_version}|{article.public_available_at.isoformat()}'.encode()).hexdigest()[:24]
            match = dict(id=cluster_id, hint=article.event_cluster_hint, event_type=article.event_type,
                         entities=entity_keys, tokens=article_tokens, articles=[])
            clusters.append(match)
        match['articles'].append(article)
        match['entities'].update(entity_keys)
        match['tokens'].update(article_tokens)
        assignments[(article.article_id, article.article_version)] = match['id']
    return clusters, assignments


def _event_records(request, clusters, assignments):
    cluster_lookup = {cluster['id']: cluster for cluster in clusters}
    records = []
    for article in sorted(request.articles, key=lambda item: (item.public_available_at, item.article_id, item.article_version)):
        cluster = cluster_lookup[assignments[(article.article_id, article.article_version)]]
        canonical = cluster['articles'][0]
        source_quality = (article.source_quality_score if article.source_quality_score is not None
                          else SOURCE_QUALITY[article.source_type])
        novelty = article.novelty_score if article.novelty_score is not None else (100 if article is canonical else 10)
        sources = {item.source for item in cluster['articles'] if item.public_available_at <= request.as_of}
        official = article.official_confirmation_flag
        for entity in article.entities:
            sentiment = entity.sentiment_score if entity.sentiment_score is not None else article.sentiment_score
            confidence = _quality(source_quality, entity.entity_confidence, novelty, official, article.rumor_flag)
            event_id = sha256(f'{article.article_id}|{article.article_version}|{entity.instrument_key}'.encode()).hexdigest()
            abnormal_1d = (entity.event_return_1d-entity.benchmark_return_1d
                           if entity.event_return_1d is not None and entity.benchmark_return_1d is not None else None)
            abnormal_5d = (entity.event_return_5d-entity.benchmark_return_5d
                           if entity.event_return_5d is not None and entity.benchmark_return_5d is not None else None)
            reasons = []
            if article is not canonical: reasons.append('DUPLICATE')
            if source_quality < request.minimum_source_quality: reasons.append('LOW_SOURCE_QUALITY')
            if entity.entity_confidence < request.minimum_entity_confidence: reasons.append('LOW_ENTITY_CONFIDENCE')
            if novelty < 20: reasons.append('LOW_NOVELTY')
            if article.rumor_flag and not official: reasons.append('UNCONFIRMED_RUMOR')
            if article.retracted_flag: reasons.append('RETRACTED')
            records.append(dict(
                event_id=event_id, event_cluster_id=cluster['id'], article_id=article.article_id,
                article_version=article.article_version, version_timestamp=article.version_timestamp.astimezone(timezone.utc).isoformat(),
                published_at=article.published_at.astimezone(timezone.utc).isoformat(),
                public_available_at=article.public_available_at.astimezone(timezone.utc).isoformat(),
                first_publication_timestamp=canonical.public_available_at.astimezone(timezone.utc).isoformat(),
                first_source=canonical.source, source=article.source, source_type=article.source_type,
                source_quality_score=source_quality, source_reference=article.source_reference,
                event_type=article.event_type, event_subtype=article.event_subtype,
                sentiment_score=sentiment, sentiment_label=_label(sentiment),
                headline_sentiment=article.headline_sentiment, body_sentiment=article.body_sentiment,
                relevance_score=entity.relevance_score, materiality_score=article.materiality_score,
                novelty_score=novelty, entity_confidence=entity.entity_confidence,
                event_confidence=confidence, surprise_score=article.surprise_score,
                instrument_key=entity.instrument_key, company_id=entity.company_id,
                sector=entity.sector, industry=entity.industry,
                duplicate_flag=article is not canonical, independent_source_count=len(sources),
                official_confirmation_flag=official, rumor_flag=article.rumor_flag,
                retracted_flag=article.retracted_flag, correction_flag=article.correction_flag,
                manual_review_required=article.event_type in MANUAL_REVIEW_TYPES and article.materiality_score >= 70,
                pre_event_return_1d=entity.pre_event_return_1d, pre_event_return_5d=entity.pre_event_return_5d,
                event_return_1d=entity.event_return_1d, event_return_5d=entity.event_return_5d,
                event_return_21d=entity.event_return_21d, event_abnormal_return_1d=abnormal_1d,
                event_abnormal_return_5d=abnormal_5d, event_rvol=entity.event_rvol,
                event_volatility_change=entity.event_volatility_change,
                news_quality_status=reasons[0] if reasons else 'VALID',
                exclusion_reasons=reasons, event_taxonomy_version=request.taxonomy_version,
                classifier_version=request.classifier_version,
                sentiment_model_version=request.sentiment_model_version,
                entity_model_version=request.entity_model_version,
            ))
    return records


def _event_signal(event, evaluation, half_lives, confirmation_count, official):
    age_days = max(0, (evaluation-event['_available']).total_seconds()/86400)
    half_life = half_lives.get(event['event_type'], half_lives.get('OTHER', 7))
    decay = exp(-log(2)*age_days/half_life)
    confidence = event['event_confidence']
    if official: confidence = min(100, confidence+10)
    confidence = min(100, confidence+5*max(0, confirmation_count-1))
    weight = (event['relevance_score']/100 * event['materiality_score']/100 *
              event['novelty_score']/100 * event['source_quality_score']/100 * confidence/100 * decay)
    return event['sentiment_score']*weight, weight, decay, confidence


def _daily_features(request, events):
    for event in events:
        event['_available'] = datetime.fromisoformat(event['public_available_at'])
        event['_version_at'] = datetime.fromisoformat(event['version_timestamp'])
    instruments = sorted(set(event['instrument_key'] for event in events))
    features = []
    for evaluation in request.evaluation_times:
        evaluation = evaluation.astimezone(timezone.utc)
        for instrument in instruments:
            eligible = [event for event in events if event['instrument_key'] == instrument and
                        event['_available'] <= evaluation]
            latest_versions = {}
            for event in eligible:
                key = (event['article_id'], event['instrument_key'])
                if key not in latest_versions or (event['_version_at'], event['article_version']) > (
                        latest_versions[key]['_version_at'], latest_versions[key]['article_version']):
                    latest_versions[key] = event
            eligible = [event for event in latest_versions.values() if not event['retracted_flag']]
            clusters = defaultdict(list)
            for event in eligible:
                clusters[event['event_cluster_id']].append(event)
            representatives = []
            for cluster_events in clusters.values():
                available_sources = {event['source'] for event in cluster_events}
                official = any(event['official_confirmation_flag'] for event in cluster_events)
                representative = max(cluster_events, key=lambda item: (item['event_confidence'], -item['_available'].timestamp()))
                signal, intensity, decay, confidence = _event_signal(
                    representative, evaluation, request.half_life_days, len(available_sources), official)
                representatives.append((representative, signal, intensity, decay, confidence))
            def window(hours):
                return [item for item in representatives if 0 <= (evaluation-item[0]['_available']).total_seconds() <= hours*3600]
            day, week = window(24), window(24*7)
            def weighted_sentiment(items):
                denominator = sum(item[2] for item in items)
                return sum(item[1] for item in items)/denominator if denominator else None
            prior_week = [item for item in representatives if 24*3600 < (evaluation-item[0]['_available']).total_seconds() <= 8*24*3600]
            sentiment_24h, sentiment_7d = weighted_sentiment(day), weighted_sentiment(week)
            prior_sentiment = weighted_sentiment(prior_week)
            risk = sum(abs(signal)*100 for event, signal, _, _, _ in week if event['event_type'] in RISK_TYPES and signal < 0)
            positive = sum(max(0, signal)*100 for _, signal, _, _, _ in week)
            negative = sum(max(0, -signal)*100 for _, signal, _, _, _ in week)
            current_count = len(week)
            historical_counts = []
            for offset in range(1, 5):
                lower = offset*7*24*3600
                upper = (offset+1)*7*24*3600
                historical_counts.append(sum(lower < (evaluation-item[0]['_available']).total_seconds() <= upper for item in representatives))
            baseline_mean = fmean(historical_counts) if historical_counts else 0
            baseline_std = pstdev(historical_counts) if len(historical_counts) > 1 else 0
            feature = dict(instrument_key=instrument, date=evaluation.date().isoformat(), evaluation_time=evaluation.isoformat(),
                news_count_24h=len(day), news_count_7d=current_count,
                positive_news_count_24h=sum(item[0]['sentiment_score'] > .15 for item in day),
                negative_news_count_24h=sum(item[0]['sentiment_score'] < -.15 for item in day),
                positive_news_count_7d=sum(item[0]['sentiment_score'] > .15 for item in week),
                negative_news_count_7d=sum(item[0]['sentiment_score'] < -.15 for item in week),
                news_sentiment_24h=sentiment_24h, news_sentiment_7d=sentiment_7d,
                news_momentum_score=(sentiment_24h-prior_sentiment if sentiment_24h is not None and prior_sentiment is not None else None),
                news_volume_z=((current_count-baseline_mean)/baseline_std if baseline_std else None),
                event_intensity_score=sum(item[2]*100 for item in week),
                positive_catalyst_score=positive, negative_catalyst_score=negative,
                event_risk_score=risk, news_factor_score=sum(item[1]*100 for item in week),
                news_reversal_flag=(sentiment_7d is not None and sentiment_24h is not None and sentiment_7d*sentiment_24h < 0),
                latest_event_confidence=(max((item[4] for item in day), default=None)),
                news_quality_status='VALID' if week else 'NO_RECENT_EVENTS')
            features.append(feature)
    for event in events:
        event.pop('_available', None)
        event.pop('_version_at', None)
    return features


def calculate_news_events(request: NewsEventRequest):
    clusters, assignments = _cluster_articles(request.articles, request.duplicate_similarity_threshold)
    events = _event_records(request, clusters, assignments)
    features = _daily_features(request, events)
    return dict(version=VERSION, snapshot_id=request.snapshot_id,
                as_of=request.as_of.astimezone(timezone.utc).isoformat(),
                events=events, daily_features=features)
