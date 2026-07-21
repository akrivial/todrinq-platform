"""Durable prediction/measurement history with optional Orion-LD publication."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


DB_PATH = Path(os.getenv("TODRINQ_OBSERVATION_DB", Path(__file__).parents[1] / "data" / "observations.sqlite3"))
ORION_URL = os.getenv("ORION_LD_URL", "http://localhost:1026").rstrip("/")
FIWARE_SERVICE = os.getenv("SERVICE", "waternet")
FIWARE_SERVICE_PATH = os.getenv("SERVICE_PATH", "/")
NGSI_CONTEXT = "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            source TEXT NOT NULL,
            model_version TEXT,
            plant_id TEXT NOT NULL,
            metadata_json TEXT NOT NULL
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_observations_sensor_time ON observations(sensor_id, observed_at)"
    )
    return connection


def _utc_iso(value: str | None = None) -> str:
    if not value:
        return datetime.now(timezone.utc).isoformat()
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


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
            headers={
                "Content-Type": "application/ld+json",
                "Accept": "application/json",
                "Fiware-Service": FIWARE_SERVICE,
                "Fiware-ServicePath": FIWARE_SERVICE_PATH,
            },
            json=[entity],
            timeout=3.0,
        ).raise_for_status()
    except Exception:
        # SQLite remains authoritative locally; FIWARE can recover on a later update.
        return


def record_observation(*, sensor_id: str, value: float, unit: str,
                       observed_at: str | None = None, source: str = "manual",
                       model_version: str | None = None, plant_id: str = "Leiduin",
                       kind: str = "prediction", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    timestamp = _utc_iso(observed_at)
    recorded_at = datetime.now(timezone.utc).isoformat()
    payload = metadata or {}
    with _connect() as connection:
        cursor = connection.execute(
            """INSERT INTO observations
               (sensor_id, kind, value, unit, observed_at, recorded_at, source, model_version, plant_id, metadata_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (sensor_id, kind, float(value), unit, timestamp, recorded_at, source,
             model_version, plant_id, json.dumps(payload, default=str)),
        )
        observation_id = cursor.lastrowid
    entity = _entity(sensor_id, float(value), unit, timestamp, source, model_version, plant_id, kind)
    threading.Thread(target=_publish_orion, args=(entity,), daemon=True).start()
    return {"id": observation_id, "observed_at": timestamp, "storage": "sqlite", "orion_publish": "queued"}


def observation_history(sensor_id: str, limit: int = 48, kind: str | None = None) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), 2000))
    query = "SELECT * FROM observations WHERE sensor_id = ?"
    params: list[Any] = [sensor_id]
    if kind:
        query += " AND kind = ?"
        params.append(kind)
    query += " ORDER BY observed_at DESC LIMIT ?"
    params.append(safe_limit)
    with _connect() as connection:
        rows = connection.execute(query, params).fetchall()
    return [
        {**dict(row), "metadata": json.loads(row["metadata_json"])}
        for row in reversed(rows)
    ]

