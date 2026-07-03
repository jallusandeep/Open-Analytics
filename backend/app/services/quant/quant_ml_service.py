from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.database import get_connection


def ensure_quant_ml_tables(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS quant_ml_datasets (
            dataset_id VARCHAR PRIMARY KEY,
            dataset_name VARCHAR NOT NULL,
            status VARCHAR DEFAULT 'success',

            from_date DATE,
            to_date DATE,
            target_column VARCHAR DEFAULT 'future_positive_10d',

            row_count BIGINT DEFAULT 0,
            feature_count BIGINT DEFAULT 0,
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
        CREATE TABLE IF NOT EXISTS quant_ml_dataset_rows (
            row_id VARCHAR PRIMARY KEY,
            dataset_id VARCHAR NOT NULL,

            instrument_key VARCHAR NOT NULL,
            trading_symbol VARCHAR,
            trading_date DATE NOT NULL,

            close_price DOUBLE,

            return_1d DOUBLE,
            return_5d DOUBLE,
            return_10d DOUBLE,
            return_20d DOUBLE,

            range_pct DOUBLE,
            close_position DOUBLE,
            gap_pct DOUBLE,

            volume_ratio_20 DOUBLE,
            distance_sma_20_pct DOUBLE,
            distance_sma_50_pct DOUBLE,
            volatility_20 DOUBLE,
            momentum_20 DOUBLE,

            future_return_10d DOUBLE,
            future_positive_10d BOOLEAN,
            target_value BIGINT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS quant_ml_models (
            model_id VARCHAR PRIMARY KEY,
            dataset_id VARCHAR,
            model_name VARCHAR NOT NULL,
            model_type VARCHAR DEFAULT 'rule_baseline',
            status VARCHAR DEFAULT 'success',

            train_row_count BIGINT DEFAULT 0,
            test_row_count BIGINT DEFAULT 0,

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
        CREATE TABLE IF NOT EXISTS quant_ml_predictions (
            prediction_id VARCHAR PRIMARY KEY,
            model_id VARCHAR,
            dataset_id VARCHAR,

            instrument_key VARCHAR NOT NULL,
            trading_symbol VARCHAR,
            trading_date DATE NOT NULL,

            close_price DOUBLE,
            prediction_score DOUBLE,
            prediction_label BOOLEAN,
            actual_label BOOLEAN,
            future_return_10d DOUBLE,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    for sql in [
        """
        CREATE INDEX IF NOT EXISTS idx_quant_ml_dataset_rows_dataset
        ON quant_ml_dataset_rows (dataset_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_quant_ml_dataset_rows_symbol_date
        ON quant_ml_dataset_rows (trading_symbol, trading_date);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_quant_ml_models_dataset
        ON quant_ml_models (dataset_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_quant_ml_predictions_model
        ON quant_ml_predictions (model_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_quant_ml_predictions_symbol_date
        ON quant_ml_predictions (trading_symbol, trading_date);
        """
    ]:
        try:
            conn.execute(sql)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass


def normalize_ml_dataset_payload(payload: Optional[dict]) -> Dict[str, Any]:
    payload = payload or {}

    dataset_name = str(payload.get("dataset_name") or "daily_quant_ml_dataset").strip()
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
        "dataset_name": dataset_name or "daily_quant_ml_dataset",
        "from_date": from_date or None,
        "to_date": to_date or None,
        "instrument_key": instrument_key or None,
        "trading_symbol": trading_symbol or None,
        "target_column": "future_positive_10d",
        "limit": to_int(payload.get("limit"), 200000, 1, 1000000)
    }


def normalize_ml_train_payload(payload: Optional[dict]) -> Dict[str, Any]:
    payload = payload or {}

    dataset_id = str(payload.get("dataset_id") or "").strip()
    model_name = str(payload.get("model_name") or "rule_baseline_model").strip()

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
        "dataset_id": dataset_id or None,
        "model_name": model_name or "rule_baseline_model",
        "test_percent": to_int(payload.get("test_percent"), 20, 5, 50),
        "score_threshold": to_float(payload.get("score_threshold"), 60.0)
    }


def get_quant_ml_source_status(conn) -> Dict[str, Any]:
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


def build_quant_ml_dataset_service(payload: Optional[dict] = None) -> Dict[str, Any]:
    config = normalize_ml_dataset_payload(payload)
    conn = get_connection()
    started_at = datetime.now()

    try:
        ensure_quant_ml_tables(conn)

        source_status = get_quant_ml_source_status(conn)

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

        dataset_id = str(conn.execute("SELECT uuid();").fetchone()[0])

        conn.execute("""
            INSERT INTO quant_ml_datasets (
                dataset_id,
                dataset_name,
                status,
                from_date,
                to_date,
                target_column,
                config_json,
                message,
                created_at,
                updated_at
            )
            VALUES (
                ?,
                ?,
                'running',
                TRY_CAST(? AS DATE),
                TRY_CAST(? AS DATE),
                ?,
                TRY_CAST(? AS JSON),
                'ML dataset build started.',
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            );
        """, [
            dataset_id,
            config["dataset_name"],
            config["from_date"],
            config["to_date"],
            config["target_column"],
            str(config).replace("'", '"')
        ])

        conn.execute("BEGIN TRANSACTION")

        conn.execute(f"""
            INSERT INTO quant_ml_dataset_rows (
                row_id,
                dataset_id,

                instrument_key,
                trading_symbol,
                trading_date,

                close_price,

                return_1d,
                return_5d,
                return_10d,
                return_20d,

                range_pct,
                close_position,
                gap_pct,

                volume_ratio_20,
                distance_sma_20_pct,
                distance_sma_50_pct,
                volatility_20,
                momentum_20,

                future_return_10d,
                future_positive_10d,
                target_value,

                created_at
            )
            SELECT
                CAST(uuid() AS VARCHAR) AS row_id,
                ? AS dataset_id,

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
                CASE WHEN labels.future_positive_10d THEN 1 ELSE 0 END AS target_value,

                CURRENT_TIMESTAMP AS created_at
            FROM quant_features_daily features
            INNER JOIN quant_labels_daily labels
                ON labels.instrument_key = features.instrument_key
               AND labels.trading_date = features.trading_date
            WHERE {where_sql}
            ORDER BY features.trading_date, features.trading_symbol
            LIMIT ?;
        """, [
            dataset_id,
            *params,
            config["limit"]
        ])

        conn.execute("COMMIT")

        metrics_row = conn.execute("""
            SELECT
                COUNT(*) AS row_count,
                SUM(CASE WHEN target_value = 1 THEN 1 ELSE 0 END) AS positive_count,
                SUM(CASE WHEN target_value = 0 THEN 1 ELSE 0 END) AS negative_count
            FROM quant_ml_dataset_rows
            WHERE dataset_id = ?;
        """, [dataset_id]).fetchone()

        row_count = int(metrics_row[0] or 0) if metrics_row else 0
        positive_count = int(metrics_row[1] or 0) if metrics_row else 0
        negative_count = int(metrics_row[2] or 0) if metrics_row else 0
        positive_rate = positive_count / row_count if row_count else None

        status_text = "success" if row_count > 0 else "empty"
        message = (
            "ML dataset built successfully."
            if row_count > 0
            else "ML dataset build completed but no rows matched filters."
        )

        conn.execute("""
            UPDATE quant_ml_datasets
            SET
                status = ?,
                row_count = ?,
                feature_count = 13,
                positive_count = ?,
                negative_count = ?,
                positive_rate = ?,
                message = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE dataset_id = ?;
        """, [
            status_text,
            row_count,
            positive_count,
            negative_count,
            positive_rate,
            message,
            dataset_id
        ])

        conn.commit()

        duration_seconds = int((datetime.now() - started_at).total_seconds())

        return {
            "status": status_text,
            "message": message,
            "dataset_id": dataset_id,
            "config": config,
            "source": source_status,
            "metrics": {
                "row_count": row_count,
                "feature_count": 13,
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
            detail=f"Unable to build quant ML dataset: {error}"
        )

    finally:
        conn.close()


def train_quant_rule_baseline_model_service(payload: Optional[dict] = None) -> Dict[str, Any]:
    config = normalize_ml_train_payload(payload)
    conn = get_connection()

    try:
        ensure_quant_ml_tables(conn)

        dataset_id = config["dataset_id"]

        if not dataset_id:
            row = conn.execute("""
                SELECT dataset_id
                FROM quant_ml_datasets
                WHERE row_count > 0
                ORDER BY created_at DESC
                LIMIT 1;
            """).fetchone()

            dataset_id = row[0] if row else None

        if not dataset_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="dataset_id is required because no dataset exists yet."
            )

        dataset_row = conn.execute("""
            SELECT dataset_id, dataset_name, row_count
            FROM quant_ml_datasets
            WHERE dataset_id = ?;
        """, [dataset_id]).fetchone()

        if not dataset_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ML dataset not found."
            )

        row_count = int(dataset_row[2] or 0)

        if row_count <= 0:
            return {
                "status": "empty",
                "message": "Selected dataset has no rows.",
                "dataset_id": dataset_id
            }

        model_id = str(conn.execute("SELECT uuid();").fetchone()[0])

        conn.execute("""
            INSERT INTO quant_ml_models (
                model_id,
                dataset_id,
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
                'rule_baseline',
                'running',
                TRY_CAST(? AS JSON),
                'Rule baseline training started.',
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            );
        """, [
            model_id,
            dataset_id,
            config["model_name"],
            str(config).replace("'", '"')
        ])

        conn.execute("BEGIN TRANSACTION")

        conn.execute("""
            INSERT INTO quant_ml_predictions (
                prediction_id,
                model_id,
                dataset_id,

                instrument_key,
                trading_symbol,
                trading_date,

                close_price,
                prediction_score,
                prediction_label,
                actual_label,
                future_return_10d,

                created_at
            )
            WITH ordered_rows AS (
                SELECT
                    *,
                    ROW_NUMBER() OVER (ORDER BY trading_date, trading_symbol) AS row_number,
                    COUNT(*) OVER () AS total_rows
                FROM quant_ml_dataset_rows
                WHERE dataset_id = ?
            ),
            test_rows AS (
                SELECT
                    *,
                    (
                        COALESCE(return_20d, 0) * 120
                        + COALESCE(volume_ratio_20, 0) * 12
                        + COALESCE(distance_sma_20_pct, 0) * 80
                        + COALESCE(distance_sma_50_pct, 0) * 40
                        - COALESCE(volatility_20, 0) * 100
                        + COALESCE(momentum_20, 0) * 80
                    ) AS raw_score
                FROM ordered_rows
                WHERE row_number > total_rows * ((100 - ?) / 100.0)
            )
            SELECT
                CAST(uuid() AS VARCHAR) AS prediction_id,
                ? AS model_id,
                ? AS dataset_id,

                instrument_key,
                trading_symbol,
                trading_date,

                close_price,

                raw_score AS prediction_score,
                CASE WHEN raw_score >= ? THEN TRUE ELSE FALSE END AS prediction_label,
                future_positive_10d AS actual_label,
                future_return_10d,

                CURRENT_TIMESTAMP AS created_at
            FROM test_rows;
        """, [
            dataset_id,
            config["test_percent"],
            model_id,
            dataset_id,
            config["score_threshold"]
        ])

        conn.execute("COMMIT")

        metric_row = conn.execute("""
            SELECT
                COUNT(*) AS test_row_count,
                SUM(CASE WHEN prediction_label = actual_label THEN 1 ELSE 0 END) AS correct_count,
                SUM(CASE WHEN prediction_label = TRUE THEN 1 ELSE 0 END) AS predicted_positive_count,
                SUM(CASE WHEN actual_label = TRUE THEN 1 ELSE 0 END) AS actual_positive_count,
                SUM(CASE WHEN prediction_label = TRUE AND actual_label = TRUE THEN 1 ELSE 0 END) AS true_positive_count
            FROM quant_ml_predictions
            WHERE model_id = ?;
        """, [model_id]).fetchone()

        test_row_count = int(metric_row[0] or 0) if metric_row else 0
        correct_count = int(metric_row[1] or 0) if metric_row else 0
        predicted_positive_count = int(metric_row[2] or 0) if metric_row else 0
        actual_positive_count = int(metric_row[3] or 0) if metric_row else 0
        true_positive_count = int(metric_row[4] or 0) if metric_row else 0

        train_row_count = max(row_count - test_row_count, 0)
        accuracy = correct_count / test_row_count if test_row_count else None
        precision_score = true_positive_count / predicted_positive_count if predicted_positive_count else None
        recall_score = true_positive_count / actual_positive_count if actual_positive_count else None
        positive_rate = actual_positive_count / test_row_count if test_row_count else None

        status_text = "success" if test_row_count > 0 else "empty"
        message = (
            "Rule baseline model evaluated successfully."
            if test_row_count > 0
            else "Model evaluation completed but test split had no rows."
        )

        conn.execute("""
            UPDATE quant_ml_models
            SET
                status = ?,
                train_row_count = ?,
                test_row_count = ?,
                accuracy = ?,
                precision_score = ?,
                recall_score = ?,
                positive_rate = ?,
                message = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE model_id = ?;
        """, [
            status_text,
            train_row_count,
            test_row_count,
            accuracy,
            precision_score,
            recall_score,
            positive_rate,
            message,
            model_id
        ])

        conn.commit()

        return {
            "status": status_text,
            "message": message,
            "dataset_id": dataset_id,
            "model_id": model_id,
            "config": config,
            "metrics": {
                "train_row_count": train_row_count,
                "test_row_count": test_row_count,
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
            detail=f"Unable to train quant rule baseline model: {error}"
        )

    finally:
        conn.close()


def get_quant_ml_datasets_service(limit: int = 50) -> Dict[str, Any]:
    conn = get_connection()

    try:
        ensure_quant_ml_tables(conn)

        safe_limit = max(1, min(int(limit or 50), 500))

        rows = conn.execute("""
            SELECT
                dataset_id,
                dataset_name,
                status,
                from_date,
                to_date,
                target_column,
                row_count,
                feature_count,
                positive_count,
                negative_count,
                positive_rate,
                message,
                created_at,
                updated_at
            FROM quant_ml_datasets
            ORDER BY created_at DESC
            LIMIT ?;
        """, [safe_limit]).fetchall()

        return {
            "status": "success",
            "datasets": [
                {
                    "dataset_id": row[0],
                    "dataset_name": row[1],
                    "status": row[2],
                    "from_date": str(row[3]) if row[3] else None,
                    "to_date": str(row[4]) if row[4] else None,
                    "target_column": row[5],
                    "row_count": row[6],
                    "feature_count": row[7],
                    "positive_count": row[8],
                    "negative_count": row[9],
                    "positive_rate": row[10],
                    "message": row[11],
                    "created_at": str(row[12]) if row[12] else None,
                    "updated_at": str(row[13]) if row[13] else None
                }
                for row in rows
            ]
        }

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to get quant ML datasets: {error}"
        )

    finally:
        conn.close()


def get_quant_ml_models_service(limit: int = 50) -> Dict[str, Any]:
    conn = get_connection()

    try:
        ensure_quant_ml_tables(conn)

        safe_limit = max(1, min(int(limit or 50), 500))

        rows = conn.execute("""
            SELECT
                model_id,
                dataset_id,
                model_name,
                model_type,
                status,
                train_row_count,
                test_row_count,
                accuracy,
                precision_score,
                recall_score,
                positive_rate,
                message,
                trained_at,
                updated_at
            FROM quant_ml_models
            ORDER BY trained_at DESC
            LIMIT ?;
        """, [safe_limit]).fetchall()

        return {
            "status": "success",
            "models": [
                {
                    "model_id": row[0],
                    "dataset_id": row[1],
                    "model_name": row[2],
                    "model_type": row[3],
                    "status": row[4],
                    "train_row_count": row[5],
                    "test_row_count": row[6],
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
            detail=f"Unable to get quant ML models: {error}"
        )

    finally:
        conn.close()