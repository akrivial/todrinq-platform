import os, datetime as dt
import httpx

ORION = os.getenv("ORION_LD_URL", "http://localhost:1026")
DEFAULT_CONTEXT = [
    "https://smartdatamodels.org/context.jsonld",
    "https://example.org/contexts/water-treatment.jsonld"
]

async def upsert_entity(entity: dict):
    # Ensure @context
    if "@context" not in entity:
        entity["@context"] = DEFAULT_CONTEXT
    url = f"{ORION}/ngsi-ld/v1/entityOperations/upsert?options=update"
    headers = {
        "Content-Type": "application/ld+json",
        "Accept": "application/json"
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, headers=headers, json=[entity])
        r.raise_for_status()
        return r.json() if r.content else None

def softsensor_entity(plant_id: str, turbidity_ntu: float, horizon_iso: str = "PT6H"):
    now = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    return {
        "id": f"urn:ngsi-ld:SoftSensor:TurbidityInlet:{plant_id}",
        "type": "WaterTreatmentSoftSensor",
        "plant": {"type": "Relationship", "object": f"urn:ngsi-ld:Plant:{plant_id}"},
        "prediction": {
            "type": "Property",
            "value": {"turbidityNTU": turbidity_ntu, "horizon": horizon_iso},
            "observedAt": now,
            "unitCode": "NTU"
        },
        "thresholdNTU": {"type": "Property", "value": 6}
    }
