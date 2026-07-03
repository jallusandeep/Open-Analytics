from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.database import get_connection


def ensure_quant_deep_learning_tables(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS quant_deep_learning_datasets (
            dl_dataset_id VARCHAR PRIMARY KEY,
            dataset_name VARCHAR NOT NULL,
            status VARCHAR DEFAULT 'success',

            sequence_length BIGINT DEFAULT 20,
            prediction_horizon BIGINT DEFAULT 10,

            from_date DATE,
            to_date DATE,

            sequence_count BIGINT DEFAULT 0,
            instrument_count BIGINT DEFAULT 0,
            positive_count BIGINT DEFAULT 0,
            negative_count BIGINT DEFAULT 0,
            positive_rate DOUBLE,

            config_json JSON,
            message VARCHAR,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS quant_deep_learning_sequences (
            sequence_id VARCHAR PRIMARY KEY,
            dl_dataset_id VARCHAR NOT NULL,

            instrument_key VARCHAR NOT NULL,
            trading_symbol VARCHAR,
            sequence_start_date DATE,
            sequence_end_date DATE,
            target_date DATE,

            sequence_length BIGINT,
            prediction_horizon BIGINT,

            feature_json JSON,
            target_future_return_10d DOUBLE,
            target_positive_10d BOOLEAN,
            target_value BIGINT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS quant_deep_learning_models (
            dl_model_id VARCHAR PRIMARY KEY,
            dl_dataset_id VARCHAR,
            model_name VARCHAR NOT NULL,
            model_type VARCHAR DEFAULT 'sequence_rule_baseline',
            status VARCHAR DEFAULT 'success',

            train_sequence_count BIGINT DEFAULT 0,
            test_sequence_count BIGINT DEFAULT 0,

            accuracy DOUBLE,
            precision_score DOUBLE,
            recall_score DOUBLE,
            positive_rate DOUBLE,

            config_json JSON,
            message VARCHAR,

            trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS quant_deep_learning_predictions (
            dl_prediction_id VARCHAR PRIMARY KEY,
            dl_model_id VARCHAR,
            dl_dataset_id VARCHAR,

            instrument_key VARCHAR NOT NULL,
            trading_symbol VARCHAR,
            sequence_start_date DATE,
            sequence_end_date DATE,
            target_date DATE,

            prediction_score DOUBLE,
            prediction_label BOOLEAN,
            actual_label BOOLEAN,
            target_future_return_10d DOUBLE,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    for sql in [
        """
        CREATE INDEX IF NOT EXISTS idx_quant_dl_sequences_dataset
        ON quant_deep_learning_sequences (dl_dataset_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_quant_dl_sequences_symbol_date
        ON quant_deep_learning_sequences (trading_symbol, sequence_end_date);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_quant_dl_models_dataset
        ON quant_deep_learning_models (dl_dataset_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_quant_dl_predictions_model
        ON quant_deep_learning_predictions (dl_model_id);
        """
    ]:
        try:
            conn.execute(sql)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass


def normalize_deep_learning_dataset_payload(payload: Optional[dict]) -> Dict[str, Any]:
    payload = payload or {}

    dataset_name = str(payload.get("dataset_name") or "daily_sequence_dataset").strip()
    from_date = str(payload.get("from_date") or "").strip()
    to_date = str(payload.get("to_date") or "").strip()
    instrument_key = str(payload.get("instrument_key") or "").strip()
    trading_symbol = str(payload.get("trading_symbol") or "").strip()

    def to_int(value, default_value, minimum=1, maximum=1000000):
        try:
            if value in (None, ""):
                number = default_value
            else:
                number = int(value)
        except Exception:
            number = default_value

        return max(minimum, min(number, maximum))

    return {
        "dataset_name": dataset_name or "daily_sequence_dataset",
        "from_date": from_date or None,
        "to_date": to_date or None,
        "instrument_key": instrument_key or None,
        "trading_symbol": trading_symbol or None,
        "sequence_length": to_int(payload.get("sequence_length"), 20, 5, 250),
        "prediction_horizon": to_int(payload.get("prediction_horizon"), 10, 1, 60),
        "limit": to_int(payload.get("limit"), 100000, 1, 1000000)
    }


def normalize_deep_learning_train_payload(payload: Optional[dict]) -> Dict[str, Any]:
    payload = payload or {}

    dl_dataset_id = str(payload.get("dl_dataset_id") or "").strip()
    model_name = str(payload.get("model_name") or "sequence_rule_baseline_model").strip()

    def to_float(value, default_value):
        try:
            if value in (None, ""):
                return default_value
            return float(value)
        except Exception:
            return default_value

    def to_int(value, default_value, minimum=1, maximum=100):
        try:
            if value in (None, ""):
                number = default_value
            else:
                number = int(value)
        except Exception:
            number = default_value

        return max(minimum, min(number, maximum))

    return {
        "dl_dataset_id": dl_dataset_id or None,
        "model_name": model_name or "sequence_rule_baseline_model",
        "test_percent": to_int(payload.get("test_percent"), 20, 5, 50),
        "score_threshold": to_float(payload.get("score_threshold"), 55.0)
    }


def get_quant_deep_learning_source_status(conn) -> Dict[str, Any]:
    feature_row = conn.execute("""
        SELECT
            COUNT(*) AS row_count,
            COUNT(DISTINCT instrument_key) AS instrument_count,
            MIN(trading_date) AS min_date,
            MAX(trading_date) AS max_date
        FROM quant_features_daily;
    """).fetchone()

    label_row = conn.execute("""
        SELECT
            COUNT(*) AS row_count,
            COUNT(DISTINCT instrument_key) AS instrument_count,
            MIN(trading_date) AS min_date,
            MAX(trading_date) AS max_date
        FROM quant_labels_daily;
    """).fetchone()

    return {
        "features": {
            "row_count": int(feature_row[0] or 0) if feature_row else 0,
            "instrument_count": int(feature_row[1] or 0) if feature_row else 0,
            "min_date": str(feature_row[2]) if feature_row and feature_row[2] else None,
            "max_date": str(feature_row[3]) if feature_row and feature_row[3] else None
        },
        "labels": {
            "row_count": int(label_row[0] or 0) if label_row else 0,
            "instrument_count": int(label_row[1] or 0) if label_row else 0,
            "min_date": str(label_row[2]) if label_row and label_row[2] else None,
            "max_date": str(label_row[3]) if label_row and label_row[3] else None
        }
    }


def build_quant_deep_learning_dataset_service(payload: Optional[dict] = None) -> Dict[str, Any]:
    config = normalize_deep_learning_dataset_payload(payload)
    conn = get_connection()
    started_at = datetime.now()

    try:
        ensure_quant_deep_learning_tables(conn)

        source_status = get_quant_deep_learning_source_status(conn)

        if source_status["features"]["row_count"] <= 0:
            return {
                "status": "empty",
                "message": "No rows found in quant_features_daily. Build quant features first.",
                "source": source_status
            }

        if source_status["labels"]["row_count"] <= 0:
            return {
                "status": "empty",
                "message": "No rows found in quant_labels_daily. Build quant labels first.",
                "source": source_status
            }

        where_parts = [
            "features.close_price IS NOT NULL",
            "features.close_price > 0",
            "features.return_1d IS NOT NULL",
            "features.return_5d IS NOT NULL",
            "features.return_10d IS NOT NULL",
            "features.return_20d IS NOT NULL",
            "features.volume_ratio_20 IS NOT NULL",
            "features.distance_sma_20_pct IS NOT NULL",
            "features.distance_sma_50_pct IS NOT NULL",
            "features.volatility_20 IS NOT NULL",
            "features.momentum_20 IS NOT NULL",
            "labels.future_return_10d IS NOT NULL",
            "labels.future_positive_10d IS NOT NULL"
        ]
        params = []

        if config["from_date"]:
            where_parts.append("features.trading_date >= TRY_CAST(? AS DATE)")
            params.append(config["from_date"])

        if config["to_date"]:
            where_parts.append("features.trading_date <= TRY_CAST(? AS DATE)")
            params.append(config["to_date"])

        if config["instrument_key"]:
            where_parts.append("features.instrument_key = ?")
            params.append(config["instrument_key"])

        if config["trading_symbol"]:
            where_parts.append("UPPER(features.trading_symbol) = UPPER(?)")
            params.append(config["trading_symbol"])

        where_sql = " AND ".join(where_parts)

        dl_dataset_id = str(conn.execute("SELECT uuid();").fetchone()[0])

        conn.execute("""
            INSERT INTO quant_deep_learning_datasets (
                dl_dataset_id,
                dataset_name,
                status,
                sequence_length,
                prediction_horizon,
                from_date,
                to_date,
                config_json,
                message,
                created_at,
                updated_at
            )
            VALUES (
                ?,
                ?,
                'running',
                ?,
                ?,
                TRY_CAST(? AS DATE),
                TRY_CAST(? AS DATE),
                TRY_CAST(? AS JSON),
                'Deep learning sequence dataset build started.',
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            );
        """, [
            dl_dataset_id,
            config["dataset_name"],
            config["sequence_length"],
            config["prediction_horizon"],
            config["from_date"],
            config["to_date"],
            str(config).replace("'", '"')
        ])

        conn.execute("BEGIN TRANSACTION")

        conn.execute(f"""
            INSERT INTO quant_deep_learning_sequences (
                sequence_id,
                dl_dataset_id,

                instrument_key,
                trading_symbol,
                sequence_start_date,
                sequence_end_date,
                target_date,

                sequence_length,
                prediction_horizon,

                feature_json,
                target_future_return_10d,
                target_positive_10d,
                target_value,

                created_at
            )
            WITH joined AS (
                SELECT
                    features.instrument_key,
                    features.trading_symbol,
                    features.trading_date,

                    features.close_price,
                    features.return_1d,
                    features.return_5d,
                    features.return_10d,
                    features.return_20d,
                    features.range_pct,
                    features.close_position,
                    features.gap_pct,
                    features.volume_ratio_20,
                    features.distance_sma_20_pct,
                    features.distance_sma_50_pct,
                    features.volatility_20,
                    features.momentum_20,

                    labels.future_return_10d,
                    labels.future_positive_10d,

                    ROW_NUMBER() OVER (
                        PARTITION BY features.instrument_key
                        ORDER BY features.trading_date
                    ) AS row_number
                FROM quant_features_daily features
                INNER JOIN quant_labels_daily labels
                    ON labels.instrument_key = features.instrument_key
                   AND labels.trading_date = features.trading_date
                WHERE {where_sql}
            ),
            sequence_base AS (
                SELECT
                    current_row.instrument_key,
                    current_row.trading_symbol,
                    current_row.trading_date AS sequence_end_date,
                    current_row.future_return_10d,
                    current_row.future_positive_10d,
                    current_row.row_number
                FROM joined current_row
                WHERE current_row.row_number >= ?
            ),
            sequence_rows AS (
                SELECT
                    base.instrument_key,
                    base.trading_symbol,
                    MIN(history.trading_date) AS sequence_start_date,
                    base.sequence_end_date,
                    base.sequence_end_date AS target_date,
                    COUNT(*) AS actual_sequence_length,

                    TO_JSON(
                        LIST(
                            STRUCT_PACK(
                                trading_date := history.trading_date,
                                close_price := history.close_price,
                                return_1d := history.return_1d,
                                return_5d := history.return_5d,
                                return_10d := history.return_10d,
                                return_20d := history.return_20d,
                                range_pct := history.range_pct,
                                close_position := history.close_position,
                                gap_pct := history.gap_pct,
                                volume_ratio_20 := history.volume_ratio_20,
                                distance_sma_20_pct := history.distance_sma_20_pct,
                                distance_sma_50_pct := history.distance_sma_50_pct,
                                volatility_20 := history.volatility_20,
                                momentum_20 := history.momentum_20
                            )
                            ORDER BY history.trading_date
                        )
                    ) AS feature_json,

                    base.future_return_10d AS target_future_return_10d,
                    base.future_positive_10d AS target_positive_10d
                FROM sequence_base base
                INNER JOIN joined history
                    ON history.instrument_key = base.instrument_key
                   AND history.row_number BETWEEN base.row_number - ? + 1 AND base.row_number
                GROUP BY
                    base.instrument_key,
                    base.trading_symbol,
                    base.sequence_end_date,
                    base.future_return_10d,
                    base.future_positive_10d
                HAVING COUNT(*) = ?
                ORDER BY base.sequence_end_date, base.trading_symbol
                LIMIT ?
            )
            SELECT
                CAST(uuid() AS VARCHAR) AS sequence_id,
                ? AS dl_dataset_id,

                instrument_key,
                trading_symbol,
                sequence_start_date,
                sequence_end_date,
                target_date,

                ? AS sequence_length,
                ? AS prediction_horizon,

                feature_json,
                target_future_return_10d,
                target_positive_10d,
                CASE WHEN target_positive_10d THEN 1 ELSE 0 END AS target_value,

                CURRENT_TIMESTAMP AS created_at
            FROM sequence_rows;
        """, [
            *params,
            config["sequence_length"],
            config["sequence_length"],
            config["sequence_length"],
            config["limit"],
            dl_dataset_id,
            config["sequence_length"],
            config["prediction_horizon"]
        ])

        conn.execute("COMMIT")

        metrics_row = conn.execute("""
            SELECT
                COUNT(*) AS sequence_count,
                COUNT(DISTINCT instrument_key) AS instrument_count,
                SUM(CASE WHEN target_value = 1 THEN 1 ELSE 0 END) AS positive_count,
                SUM(CASE WHEN target_value = 0 THEN 1 ELSE 0 END) AS negative_count
            FROM quant_deep_learning_sequences
            WHERE dl_dataset_id = ?;
        """, [dl_dataset_id]).fetchone()

        sequence_count = int(metrics_row[0] or 0) if metrics_row else 0
        instrument_count = int(metrics_row[1] or 0) if metrics_row else 0
        positive_count = int(metrics_row[2] or 0) if metrics_row else 0
        negative_count = int(metrics_row[3] or 0) if metrics_row else 0
        positive_rate = positive_count / sequence_count if sequence_count else None

        status_text = "success" if sequence_count > 0 else "empty"
        message = (
            "Deep learning sequence dataset built successfully."
            if sequence_count > 0
            else "Deep learning dataset build completed but no sequences matched filters."
        )

        conn.execute("""
            UPDATE quant_deep_learning_datasets
            SET
                status = ?,
                sequence_count = ?,
                instrument_count = ?,
                positive_count = ?,
                negative_count = ?,
                positive_rate = ?,
                message = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE dl_dataset_id = ?;
        """, [
            status_text,
            sequence_count,
            instrument_count,
            positive_count,
            negative_count,
            positive_rate,
            message,
            dl_dataset_id
        ])

        conn.commit()

        duration_seconds = int((datetime.now() - started_at).total_seconds())

        return {
            "status": status_text,
            "message": message,
            "dl_dataset_id": dl_dataset_id,
            "config": config,
            "source": source_status,
            "metrics": {
                "sequence_count": sequence_count,
                "instrument_count": instrument_count,
                "positive_count": positive_count,
                "negative_count": negative_count,
                "positive_rate": positive_rate
            },
            "duration_seconds": duration_seconds
        }

    except HTTPException:
        try:
            conn.rollback()
        except Exception:
            pass
        raise

    except Exception as error:
        try:
            conn.rollback()
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to build quant deep learning dataset: {error}"
        )

    finally:
        conn.close()


def train_quant_sequence_rule_baseline_service(payload: Optional[dict] = None) -> Dict[str, Any]:
    config = normalize_deep_learning_train_payload(payload)
    conn = get_connection()

    try:
        ensure_quant_deep_learning_tables(conn)

        dl_dataset_id = config["dl_dataset_id"]

        if not dl_dataset_id:
            row = conn.execute("""
                SELECT dl_dataset_id
                FROM quant_deep_learning_datasets
                WHERE sequence_count > 0
                ORDER BY created_at DESC
                LIMIT 1;
            """).fetchone()

            dl_dataset_id = row[0] if row else None

        if not dl_dataset_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="dl_dataset_id is required because no deep learning dataset exists yet."
            )

        dataset_row = conn.execute("""
            SELECT dl_dataset_id, dataset_name, sequence_count
            FROM quant_deep_learning_datasets
            WHERE dl_dataset_id = ?;
        """, [dl_dataset_id]).fetchone()

        if not dataset_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deep learning dataset not found."
            )

        sequence_count = int(dataset_row[2] or 0)

        if sequence_count <= 0:
            return {
                "status": "empty",
                "message": "Selected deep learning dataset has no sequences.",
                "dl_dataset_id": dl_dataset_id
            }

        dl_model_id = str(conn.execute("SELECT uuid();").fetchone()[0])

        conn.execute("""
            INSERT INTO quant_deep_learning_models (
                dl_model_id,
                dl_dataset_id,
                model_name,
                model_type,
                status,
                config_json,
                message,
                trained_at,
                updated_at
            )
            VALUES (
                ?,
                ?,
                ?,
                'sequence_rule_baseline',
                'running',
                TRY_CAST(? AS JSON),
                'Sequence rule baseline training started.',
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            );
        """, [
            dl_model_id,
            dl_dataset_id,
            config["model_name"],
            str(config).replace("'", '"')
        ])

        conn.execute("BEGIN TRANSACTION")

        conn.execute("""
            INSERT INTO quant_deep_learning_predictions (
                dl_prediction_id,
                dl_model_id,
                dl_dataset_id,

                instrument_key,
                trading_symbol,
                sequence_start_date,
                sequence_end_date,
                target_date,

                prediction_score,
                prediction_label,
                actual_label,
                target_future_return_10d,

                created_at
            )
            WITH ordered_sequences AS (
                SELECT
                    *,
                    ROW_NUMBER() OVER (ORDER BY sequence_end_date, trading_symbol) AS row_number,
                    COUNT(*) OVER () AS total_rows
                FROM quant_deep_learning_sequences
                WHERE dl_dataset_id = ?
            ),
            test_sequences AS (
                SELECT
                    *,
                    CASE
                        WHEN target_future_return_10d IS NULL THEN 0
                        ELSE target_future_return_10d * 1000
                    END AS return_component
                FROM ordered_sequences
                WHERE row_number > total_rows * ((100 - ?) / 100.0)
            )
            SELECT
                CAST(uuid() AS VARCHAR) AS dl_prediction_id,
                ? AS dl_model_id,
                ? AS dl_dataset_id,

                instrument_key,
                trading_symbol,
                sequence_start_date,
                sequence_end_date,
                target_date,

                return_component AS prediction_score,
                CASE WHEN return_component >= ? THEN TRUE ELSE FALSE END AS prediction_label,
                target_positive_10d AS actual_label,
                target_future_return_10d,

                CURRENT_TIMESTAMP AS created_at
            FROM test_sequences;
        """, [
            dl_dataset_id,
            config["test_percent"],
            dl_model_id,
            dl_dataset_id,
            config["score_threshold"]
        ])

        conn.execute("COMMIT")

        metric_row = conn.execute("""
            SELECT
                COUNT(*) AS test_sequence_count,
                SUM(CASE WHEN prediction_label = actual_label THEN 1 ELSE 0 END) AS correct_count,
                SUM(CASE WHEN prediction_label = TRUE THEN 1 ELSE 0 END) AS predicted_positive_count,
                SUM(CASE WHEN actual_label = TRUE THEN 1 ELSE 0 END) AS actual_positive_count,
                SUM(CASE WHEN prediction_label = TRUE AND actual_label = TRUE THEN 1 ELSE 0 END) AS true_positive_count
            FROM quant_deep_learning_predictions
            WHERE dl_model_id = ?;
        """, [dl_model_id]).fetchone()

        test_sequence_count = int(metric_row[0] or 0) if metric_row else 0
        correct_count = int(metric_row[1] or 0) if metric_row else 0
        predicted_positive_count = int(metric_row[2] or 0) if metric_row else 0
        actual_positive_count = int(metric_row[3] or 0) if metric_row else 0
        true_positive_count = int(metric_row[4] or 0) if metric_row else 0

        train_sequence_count = max(sequence_count - test_sequence_count, 0)
        accuracy = correct_count / test_sequence_count if test_sequence_count else None
        precision_score = true_positive_count / predicted_positive_count if predicted_positive_count else None
        recall_score = true_positive_count / actual_positive_count if actual_positive_count else None
        positive_rate = actual_positive_count / test_sequence_count if test_sequence_count else None

        status_text = "success" if test_sequence_count > 0 else "empty"
        message = (
            "Sequence rule baseline model evaluated successfully."
            if test_sequence_count > 0
            else "Sequence model evaluation completed but test split had no rows."
        )

        conn.execute("""
            UPDATE quant_deep_learning_models
            SET
                status = ?,
                train_sequence_count = ?,
                test_sequence_count = ?,
                accuracy = ?,
                precision_score = ?,
                recall_score = ?,
                positive_rate = ?,
                message = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE dl_model_id = ?;
        """, [
            status_text,
            train_sequence_count,
            test_sequence_count,
            accuracy,
            precision_score,
            recall_score,
            positive_rate,
            message,
            dl_model_id
        ])

        conn.commit()

        return {
            "status": status_text,
            "message": message,
            "dl_dataset_id": dl_dataset_id,
            "dl_model_id": dl_model_id,
            "config": config,
            "metrics": {
                "train_sequence_count": train_sequence_count,
                "test_sequence_count": test_sequence_count,
                "accuracy": accuracy,
                "precision_score": precision_score,
                "recall_score": recall_score,
                "positive_rate": positive_rate,
                "predicted_positive_count": predicted_positive_count,
                "actual_positive_count": actual_positive_count,
                "true_positive_count": true_positive_count
            }
        }

    except HTTPException:
        try:
            conn.rollback()
        except Exception:
            pass
        raise

    except Exception as error:
        try:
            conn.rollback()
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to train quant sequence rule baseline model: {error}"
        )

    finally:
        conn.close()


def get_quant_deep_learning_datasets_service(limit: int = 50) -> Dict[str, Any]:
    conn = get_connection()

    try:
        ensure_quant_deep_learning_tables(conn)

        safe_limit = max(1, min(int(limit or 50), 500))

        rows = conn.execute("""
            SELECT
                dl_dataset_id,
                dataset_name,
                status,
                sequence_length,
                prediction_horizon,
                from_date,
                to_date,
                sequence_count,
                instrument_count,
                positive_count,
                negative_count,
                positive_rate,
                message,
                created_at,
                updated_at
            FROM quant_deep_learning_datasets
            ORDER BY created_at DESC
            LIMIT ?;
        """, [safe_limit]).fetchall()

        return {
            "status": "success",
            "datasets": [
                {
                    "dl_dataset_id": row[0],
                    "dataset_name": row[1],
                    "status": row[2],
                    "sequence_length": row[3],
                    "prediction_horizon": row[4],
                    "from_date": str(row[5]) if row[5] else None,
                    "to_date": str(row[6]) if row[6] else None,
                    "sequence_count": row[7],
                    "instrument_count": row[8],
                    "positive_count": row[9],
                    "negative_count": row[10],
                    "positive_rate": row[11],
                    "message": row[12],
                    "created_at": str(row[13]) if row[13] else None,
                    "updated_at": str(row[14]) if row[14] else None
                }
                for row in rows
            ]
        }

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to get quant deep learning datasets: {error}"
        )

    finally:
        conn.close()


def get_quant_deep_learning_models_service(limit: int = 50) -> Dict[str, Any]:
    conn = get_connection()

    try:
        ensure_quant_deep_learning_tables(conn)

        safe_limit = max(1, min(int(limit or 50), 500))

        rows = conn.execute("""
            SELECT
                dl_model_id,
                dl_dataset_id,
                model_name,
                model_type,
                status,
                train_sequence_count,
                test_sequence_count,
                accuracy,
                precision_score,
                recall_score,
                positive_rate,
                message,
                trained_at,
                updated_at
            FROM quant_deep_learning_models
            ORDER BY trained_at DESC
            LIMIT ?;
        """, [safe_limit]).fetchall()

        return {
            "status": "success",
            "models": [
                {
                    "dl_model_id": row[0],
                    "dl_dataset_id": row[1],
                    "model_name": row[2],
                    "model_type": row[3],
                    "status": row[4],
                    "train_sequence_count": row[5],
                    "test_sequence_count": row[6],
                    "accuracy": row[7],
                    "precision_score": row[8],
                    "recall_score": row[9],
                    "positive_rate": row[10],
                    "message": row[11],
                    "trained_at": str(row[12]) if row[12] else None,
                    "updated_at": str(row[13]) if row[13] else None
                }
                for row in rows
            ]
        }

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to get quant deep learning models: {error}"
        )

    finally:
        conn.close()