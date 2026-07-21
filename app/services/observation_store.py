"""Durable observations with PostgreSQL production and SQLite local support."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx


DB_PATH = Path(os.getenv("TODRINQ_OBSERVATION_DB", Path(__file__).parents[1] / "data" / "observations.sqlite3"))
DATABASE_URL = os.getenv("TODRINQ_DATABASE_URL") or os.getenv("DATABASE_URL")
DYNAMODB_TABLE = os.getenv("TODRINQ_DYNAMODB_TABLE")
DATABASE_BACKEND = "dynamodb" if DYNAMODB_TABLE else "postgresql" if DATABASE_URL else "sqlite"
ORION_URL = os.getenv("ORION_LD_URL", "http://localhost:1026").rstrip("/")
FIWARE_SERVICE = os.getenv("SERVICE", "waternet")
FIWARE_SERVICE_PATH = os.getenv("SERVICE_PATH", "/")
NGSI_CONTEXT = "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"


SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_id TEXT NOT NULL, kind TEXT NOT NULL, value REAL NOT NULL,
    unit TEXT NOT NULL, observed_at TEXT NOT NULL, recorded_at TEXT NOT NULL,
    source TEXT NOT NULL, model_version TEXT, plant_id TEXT NOT NULL,
    metadata_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_observations_sensor_time
    ON observations(sensor_id, observed_at);
CREATE TABLE IF NOT EXISTS scheduler_runs (
    job_name TEXT NOT NULL, scheduled_for TEXT NOT NULL, started_at TEXT NOT NULL,
    finished_at TEXT, status TEXT NOT NULL, details_json TEXT NOT NULL,
    PRIMARY KEY(job_name, scheduled_for)
);
CREATE TABLE IF NOT EXISTS risk_signals (
    sensor_key TEXT NOT NULL, prediction_timestamp TEXT NOT NULL,
    value REAL NOT NULL, raw_class TEXT NOT NULL, recorded_at TEXT NOT NULL,
    PRIMARY KEY(sensor_key, prediction_timestamp)
);
"""

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    id BIGSERIAL PRIMARY KEY,
    sensor_id TEXT NOT NULL, kind TEXT NOT NULL, value DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL, observed_at TIMESTAMPTZ NOT NULL, recorded_at TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL, model_version TEXT, plant_id TEXT NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_observations_sensor_time
    ON observations(sensor_id, observed_at);
CREATE TABLE IF NOT EXISTS scheduler_runs (
    job_name TEXT NOT NULL, scheduled_for TIMESTAMPTZ NOT NULL, started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ, status TEXT NOT NULL, details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY(job_name, scheduled_for)
);
CREATE TABLE IF NOT EXISTS risk_signals (
    sensor_key TEXT NOT NULL, prediction_timestamp TIMESTAMPTZ NOT NULL,
    value DOUBLE PRECISION NOT NULL, raw_class TEXT NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY(sensor_key, prediction_timestamp)
);
"""


def _postgres_connect():
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError("PostgreSQL requires psycopg[binary]; install project requirements.") from exc
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=10)


def _dynamo_table():
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("DynamoDB requires boto3; install project requirements.") from exc
    return boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "eu-central-1")).Table(DYNAMODB_TABLE)


def _sqlite_connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.executescript(SQLITE_SCHEMA)
    return connection


def initialize_database() -> None:
    if DATABASE_BACKEND == "dynamodb":
        _dynamo_table().load()
    elif DATABASE_BACKEND == "postgresql":
        with _postgres_connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(POSTGRES_SCHEMA)
    else:
        with _sqlite_connect():
            pass


def _utc_datetime(value: str | datetime | None = None) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif value:
        normalized = value.strip().replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    else:
        parsed = datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _utc_iso(value: str | datetime | None = None) -> str:
    return _utc_datetime(value).isoformat()


def _entity(sensor_id: str, value: float, unit: str, observed_at: str, source: str,
            model_version: str | None, plant_id: str, kind: str) -> dict[str, Any]:
    safe_sensor = sensor_id.replace("_", "-")
    return {
        "@context": [NGSI_CONTEXT],
        "id": f"urn:ngsi-ld:ToDrinQObservation:{plant_id}:{safe_sensor}",
        "type": "WaterQualityObserved" if kind == "measurement" else "WaterTreatmentPrediction",
        "plant": {"type": "Relationship", "object": f"urn:ngsi-ld:Plant:{plant_id}"},
        "sensorId": {"type": "Property", "value": sensor_id},
        "result": {"type": "Property", "value": value, "observedAt": observed_at, "unitText": unit},
        "dataSource": {"type": "Property", "value": source},
        "modelVersion": {"type": "Property", "value": model_version or "not-specified"},
    }


def _publish_orion(entity: dict[str, Any]) -> None:
    try:
        httpx.post(
            f"{ORION_URL}/ngsi-ld/v1/entityOperations/upsert?options=update",
            headers={"Content-Type": "application/ld+json", "Accept": "application/json",
                     "Fiware-Service": FIWARE_SERVICE, "Fiware-ServicePath": FIWARE_SERVICE_PATH},
            json=[entity], timeout=3.0,
        ).raise_for_status()
    except Exception:
        return


def record_observation(*, sensor_id: str, value: float, unit: str,
                       observed_at: str | None = None, source: str = "manual",
                       model_version: str | None = None, plant_id: str = "Leiduin",
                       kind: str = "prediction", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    observed = _utc_datetime(observed_at)
    recorded = datetime.now(timezone.utc)
    payload = metadata or {}
    initialize_database()
    if DATABASE_BACKEND == "dynamodb":
        observation_id = str(uuid.uuid4())
        _dynamo_table().put_item(Item={
            "pk": f"OBS#{sensor_id}", "sk": f"{observed.isoformat()}#{observation_id}",
            "id": observation_id, "sensor_id": sensor_id, "kind": kind,
            "value": Decimal(str(float(value))), "unit": unit,
            "observed_at": observed.isoformat(), "recorded_at": recorded.isoformat(),
            "source": source, "model_version": model_version or "", "plant_id": plant_id,
            "metadata_json": json.dumps(payload, default=str),
        })
    elif DATABASE_BACKEND == "postgresql":
        with _postgres_connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO observations
                    (sensor_id,kind,value,unit,observed_at,recorded_at,source,model_version,plant_id,metadata_json)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb) RETURNING id""",
                    (sensor_id, kind, float(value), unit, observed, recorded, source,
                     model_version, plant_id, json.dumps(payload, default=str)),
                )
                observation_id = cursor.fetchone()["id"]
    else:
        with _sqlite_connect() as connection:
            cursor = connection.execute(
                """INSERT INTO observations
                (sensor_id,kind,value,unit,observed_at,recorded_at,source,model_version,plant_id,metadata_json)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (sensor_id, kind, float(value), unit, observed.isoformat(), recorded.isoformat(), source,
                 model_version, plant_id, json.dumps(payload, default=str)),
            )
            observation_id = cursor.lastrowid
    timestamp = observed.isoformat()
    threading.Thread(target=_publish_orion, args=(
        _entity(sensor_id, float(value), unit, timestamp, source, model_version, plant_id, kind),
    ), daemon=True).start()
    return {"id": observation_id, "observed_at": timestamp, "storage": DATABASE_BACKEND, "orion_publish": "queued"}


def observation_history(sensor_id: str, limit: int = 48, kind: str | None = None) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), 2000))
    initialize_database()
    if DATABASE_BACKEND == "dynamodb":
        from boto3.dynamodb.conditions import Key
        response = _dynamo_table().query(
            KeyConditionExpression=Key("pk").eq(f"OBS#{sensor_id}"),
            ScanIndexForward=False, Limit=safe_limit,
        )
        rows = response.get("Items", [])
        if kind:
            rows = [row for row in rows if row.get("kind") == kind]
        items = []
        for row in reversed(rows):
            item = {k: v for k, v in row.items() if k not in {"pk", "sk", "metadata_json"}}
            item["value"] = float(item["value"])
            item["metadata"] = json.loads(row.get("metadata_json", "{}"))
            items.append(item)
        return items
    if DATABASE_BACKEND == "postgresql":
        query = "SELECT * FROM observations WHERE sensor_id = %s"
        params: list[Any] = [sensor_id]
        if kind:
            query += " AND kind = %s"
            params.append(kind)
        query += " ORDER BY observed_at DESC LIMIT %s"
        params.append(safe_limit)
        with _postgres_connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
        items = []
        for row in reversed(rows):
            item = dict(row)
            item["observed_at"] = _utc_iso(item["observed_at"])
            item["recorded_at"] = _utc_iso(item["recorded_at"])
            metadata = item.pop("metadata_json", {})
            item["metadata"] = metadata if isinstance(metadata, dict) else json.loads(metadata)
            items.append(item)
        return items
    query = "SELECT * FROM observations WHERE sensor_id = ?"
    params = [sensor_id]
    if kind:
        query += " AND kind = ?"
        params.append(kind)
    query += " ORDER BY observed_at DESC LIMIT ?"
    params.append(safe_limit)
    with _sqlite_connect() as connection:
        rows = connection.execute(query, params).fetchall()
    return [{**dict(row), "metadata": json.loads(row["metadata_json"])} for row in reversed(rows)]


def claim_scheduler_slot(job_name: str, scheduled_for: datetime) -> bool:
    initialize_database()
    now = datetime.now(timezone.utc)
    if DATABASE_BACKEND == "dynamodb":
        try:
            _dynamo_table().put_item(
                Item={"pk": f"JOB#{job_name}", "sk": scheduled_for.isoformat(),
                      "started_at": now.isoformat(), "status": "running", "details_json": "{}"},
                ConditionExpression="attribute_not_exists(pk) AND attribute_not_exists(sk)",
            )
            return True
        except Exception as exc:
            error_code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            if error_code == "ConditionalCheckFailedException":
                return False
            raise
    if DATABASE_BACKEND == "postgresql":
        with _postgres_connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO scheduler_runs(job_name,scheduled_for,started_at,status,details_json)
                    VALUES (%s,%s,%s,'running','{}'::jsonb) ON CONFLICT DO NOTHING RETURNING job_name""",
                    (job_name, scheduled_for, now),
                )
                return cursor.fetchone() is not None
    with _sqlite_connect() as connection:
        cursor = connection.execute(
            """INSERT OR IGNORE INTO scheduler_runs
            (job_name,scheduled_for,started_at,status,details_json) VALUES (?,?,?,?,?)""",
            (job_name, scheduled_for.isoformat(), now.isoformat(), "running", "{}"),
        )
        return cursor.rowcount == 1


def finish_scheduler_slot(job_name: str, scheduled_for: datetime, status: str, details: dict[str, Any]) -> None:
    finished = datetime.now(timezone.utc)
    if DATABASE_BACKEND == "dynamodb":
        _dynamo_table().update_item(
            Key={"pk": f"JOB#{job_name}", "sk": scheduled_for.isoformat()},
            UpdateExpression="SET finished_at=:finished, #status=:status, details_json=:details",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":finished": finished.isoformat(), ":status": status,
                                       ":details": json.dumps(details, default=str)},
        )
    elif DATABASE_BACKEND == "postgresql":
        with _postgres_connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """UPDATE scheduler_runs SET finished_at=%s,status=%s,details_json=%s::jsonb
                    WHERE job_name=%s AND scheduled_for=%s""",
                    (finished, status, json.dumps(details, default=str), job_name, scheduled_for),
                )
    else:
        with _sqlite_connect() as connection:
            connection.execute(
                """UPDATE scheduler_runs SET finished_at=?,status=?,details_json=?
                WHERE job_name=? AND scheduled_for=?""",
                (finished.isoformat(), status, json.dumps(details, default=str), job_name, scheduled_for.isoformat()),
            )


def clear_risk_signal_history(sensor_key: str) -> None:
    initialize_database()
    if DATABASE_BACKEND == "dynamodb":
        from boto3.dynamodb.conditions import Key
        table = _dynamo_table()
        rows = table.query(KeyConditionExpression=Key("pk").eq(f"RISK#{sensor_key}"),
                           ProjectionExpression="pk,sk").get("Items", [])
        with table.batch_writer() as batch:
            for row in rows:
                batch.delete_item(Key={"pk": row["pk"], "sk": row["sk"]})
    elif DATABASE_BACKEND == "postgresql":
        with _postgres_connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM risk_signals WHERE sensor_key=%s", (sensor_key,))
    else:
        with _sqlite_connect() as connection:
            connection.execute("DELETE FROM risk_signals WHERE sensor_key=?", (sensor_key,))


def record_risk_signal(sensor_key: str, prediction_timestamp: datetime, value: float,
                       raw_class: str, limit: int = 24) -> list[dict[str, Any]]:
    """Upsert one distinct prediction signal and return chronological history."""
    initialize_database()
    now = datetime.now(timezone.utc)
    if DATABASE_BACKEND == "dynamodb":
        from boto3.dynamodb.conditions import Key
        table = _dynamo_table()
        table.put_item(Item={
            "pk": f"RISK#{sensor_key}", "sk": prediction_timestamp.isoformat(),
            "value": Decimal(str(float(value))), "raw_class": raw_class,
            "recorded_at": now.isoformat(),
        })
        rows = table.query(KeyConditionExpression=Key("pk").eq(f"RISK#{sensor_key}"),
                           ScanIndexForward=False, Limit=limit).get("Items", [])
        return [{"timestamp": row["sk"], "value": float(row["value"]),
                 "raw_class": row["raw_class"]} for row in reversed(rows)]
    if DATABASE_BACKEND == "postgresql":
        with _postgres_connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO risk_signals(sensor_key,prediction_timestamp,value,raw_class,recorded_at)
                    VALUES (%s,%s,%s,%s,%s)
                    ON CONFLICT(sensor_key,prediction_timestamp) DO UPDATE
                    SET value=EXCLUDED.value,raw_class=EXCLUDED.raw_class,recorded_at=EXCLUDED.recorded_at""",
                    (sensor_key, prediction_timestamp, float(value), raw_class, now),
                )
                cursor.execute(
                    """SELECT prediction_timestamp,value,raw_class FROM risk_signals
                    WHERE sensor_key=%s ORDER BY prediction_timestamp DESC LIMIT %s""",
                    (sensor_key, limit),
                )
                rows = list(reversed(cursor.fetchall()))
        return [{"timestamp": _utc_iso(row["prediction_timestamp"]), "value": float(row["value"]),
                 "raw_class": row["raw_class"]} for row in rows]
    with _sqlite_connect() as connection:
        connection.execute(
            """INSERT INTO risk_signals(sensor_key,prediction_timestamp,value,raw_class,recorded_at)
            VALUES (?,?,?,?,?) ON CONFLICT(sensor_key,prediction_timestamp) DO UPDATE SET
            value=excluded.value,raw_class=excluded.raw_class,recorded_at=excluded.recorded_at""",
            (sensor_key, prediction_timestamp.isoformat(), float(value), raw_class, now.isoformat()),
        )
        rows = connection.execute(
            """SELECT prediction_timestamp,value,raw_class FROM risk_signals
            WHERE sensor_key=? ORDER BY prediction_timestamp DESC LIMIT ?""",
            (sensor_key, limit),
        ).fetchall()
    return [{"timestamp": row["prediction_timestamp"], "value": float(row["value"]),
             "raw_class": row["raw_class"]} for row in reversed(rows)]


def database_status() -> dict[str, Any]:
    try:
        initialize_database()
        if DATABASE_BACKEND == "dynamodb":
            table = _dynamo_table()
            table.load()
            count = table.item_count
            location = DYNAMODB_TABLE
        elif DATABASE_BACKEND == "postgresql":
            with _postgres_connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) AS count FROM observations")
                    count = cursor.fetchone()["count"]
            location = "configured PostgreSQL service"
        else:
            with _sqlite_connect() as connection:
                count = connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
            location = str(DB_PATH)
        return {"ok": True, "backend": DATABASE_BACKEND, "location": location, "observation_count": count}
    except Exception as exc:
        return {"ok": False, "backend": DATABASE_BACKEND, "error": str(exc)}
