import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path


def round_list(values, digits=2):
    return [round(v, digits) for v in values]


# now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
now = datetime.now(timezone.utc).replace(second=0, microsecond=0)

turbidity_lag = round_list([random.uniform(0.8, 2.5) for _ in range(24)])
temperature_lag = round_list([random.uniform(8.0, 16.0) for _ in range(24)])
discharge_lag = round_list([random.uniform(850, 1200) for _ in range(24)], 1)

current_turbidity = turbidity_lag[-1]
current_temperature = temperature_lag[-1]
current_flow = discharge_lag[-1]

turbidity_plus_1h = round(current_turbidity + random.uniform(0.0, 0.5), 2)
turbidity_plus_2h = round(turbidity_plus_1h + random.uniform(0.0, 0.5), 2)
turbidity_plus_3h = round(turbidity_plus_2h + random.uniform(0.0, 0.5), 2)

payload = [
    {
        "id": "urn:ngsi-ld:WaterQualityObserved:CoagulationInfluent:Leiduin:SoSe9Input",
        "type": "WaterQualityObserved",
        "dateObserved": {
            "type": "Property",
            "value": now.isoformat().replace("+00:00", "Z")
        },
        "month": {
            "type": "Property",
            "value": now.month
        },
        "turbidity": {
            "type": "Property",
            "value": current_turbidity,
            "unitCode": "FTU",
            "observedAt": now.isoformat().replace("+00:00", "Z")
        },
        "temperature": {
            "type": "Property",
            "value": current_temperature,
            "unitCode": "CEL",
            "observedAt": now.isoformat().replace("+00:00", "Z")
        },
        "turbidityLag24h": {
            "type": "Property",
            "value": turbidity_lag,
            "unitCode": "FTU"
        },
        "temperatureLag24h": {
            "type": "Property",
            "value": temperature_lag,
            "unitCode": "CEL"
        },
        "givesInput": {
            "type": "Relationship",
            "object": "urn:ngsi-ld:DrinkingWaterSimulation:TurbidityInletSoftSensor:Leiduin:SoSe9"
        },
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        ]
    },
    {
        "id": "urn:ngsi-ld:WaterQuantityObserved:Hagesteinboven:SoSe9Input",
        "type": "WaterQuantityObserved",
        "dateObserved": {
            "type": "Property",
            "value": now.isoformat().replace("+00:00", "Z")
        },
        "flow": {
            "type": "Property",
            "value": current_flow,
            "unitCode": "Q37",
            "observedAt": now.isoformat().replace("+00:00", "Z")
        },
        "dischargeLag24h": {
            "type": "Property",
            "value": discharge_lag,
            "unitCode": "Q37"
        },
        "givesInput": {
            "type": "Relationship",
            "object": "urn:ngsi-ld:DrinkingWaterSimulation:TurbidityInletSoftSensor:Leiduin:SoSe9"
        },
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        ]
    },
    {
        "id": "urn:ngsi-ld:DrinkingWaterSimulation:TurbidityInletSoftSensor:Leiduin:SoSe9",
        "type": "TurbidityInletSoftSensor",
        "name": {
            "type": "Property",
            "value": "SoSe #9 - Turbidity Inlet Soft Sensor"
        },
        "module": {
            "type": "Property",
            "value": "Source / Intake"
        },
        "forecastHorizon": {
            "type": "Property",
            "value": 3,
            "unitCode": "HUR"
        },
        "forecastResolution": {
            "type": "Property",
            "value": 1,
            "unitCode": "HUR"
        },
        "numberOfInputFeatures": {
            "type": "Property",
            "value": 73
        },
        "hasInput": {
            "type": "Relationship",
            "object": [
                "urn:ngsi-ld:WaterQualityObserved:CoagulationInfluent:Leiduin:SoSe9Input",
                "urn:ngsi-ld:WaterQuantityObserved:Hagesteinboven:SoSe9Input"
            ]
        },
        "givesPrediction": {
            "type": "Relationship",
            "object": "urn:ngsi-ld:WaterQualityObserved:CoagulationInfluent:Leiduin:SoSe9Output"
        },
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        ]
    },
    {
        "id": "urn:ngsi-ld:WaterQualityObserved:CoagulationInfluent:Leiduin:SoSe9Output",
        "type": "WaterQualityObserved",
        "dateObserved": {
            "type": "Property",
            "value": now.isoformat().replace("+00:00", "Z")
        },
        "turbidityPlus1h": {
            "type": "Property",
            "value": turbidity_plus_1h,
            "unitCode": "FTU",
            "observedAt": (now + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
        },
        "turbidityPlus2h": {
            "type": "Property",
            "value": turbidity_plus_2h,
            "unitCode": "FTU",
            "observedAt": (now + timedelta(hours=2)).isoformat().replace("+00:00", "Z")
        },
        "turbidityPlus3h": {
            "type": "Property",
            "value": turbidity_plus_3h,
            "unitCode": "FTU",
            "observedAt": (now + timedelta(hours=3)).isoformat().replace("+00:00", "Z")
        },
        "generatedBy": {
            "type": "Relationship",
            "object": "urn:ngsi-ld:DrinkingWaterSimulation:TurbidityInletSoftSensor:Leiduin:SoSe9"
        },
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        ]
    }
]

output_path = Path(__file__).parent / "sose9_synthetic_generated.json"

with open(output_path, "w", encoding="utf-8") as file:
    json.dump(payload, file, indent=2)

print(f"Synthetic SoSe #9 NGSI-LD payload created: {output_path}")