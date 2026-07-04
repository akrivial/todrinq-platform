import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

# now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
lag_1h = now - timedelta(hours=1)

residence_time = round(random.uniform(12, 25), 1)
flow = round(random.uniform(850, 1200), 1)
temperature = round(random.uniform(8, 16), 1)
turbidity = round(random.uniform(0.3, 2.5), 2)
ozone_dosage = round(random.uniform(0.5, 3.5), 2)

ozone_exposure = round(residence_time * ozone_dosage * random.uniform(0.6, 1.0), 2)
bromate = round(random.uniform(1.0, 10.0), 2)
log_coliform_removal = round(random.uniform(1.0, 5.0), 2)

payload = [
    {
        "id": "urn:ngsi-ld:WaterQualityObserved:OzonationInlet:Leiduin:SoSe10Input",
        "type": "WaterQualityObserved",
        "name": {
            "type": "Property",
            "value": "Ozonation Inlet Water Quality - Leiduin"
        },
        "description": {
            "type": "Property",
            "value": "Synthetic influent water quality and operational parameters used as input for the ozonation soft sensor models."
        },
        "dateObserved": {
            "type": "Property",
            "value": now.isoformat().replace("+00:00", "Z")
        },
        "month": {
            "type": "Property",
            "value": now.month
        },
        "residenceTime": {
            "type": "Property",
            "value": residence_time,
            "unitCode": "MIN",
            "observedAt": now.isoformat().replace("+00:00", "Z")
        },
        "flow": {
            "type": "Property",
            "value": flow,
            "unitCode": "Q37",
            "observedAt": now.isoformat().replace("+00:00", "Z")
        },
        "temperature": {
            "type": "Property",
            "value": temperature,
            "unitCode": "CEL",
            "observedAt": now.isoformat().replace("+00:00", "Z")
        },
        "turbidity": {
            "type": "Property",
            "value": turbidity,
            "unitCode": "NTU",
            "observedAt": now.isoformat().replace("+00:00", "Z")
        },
        "turbidityLag1h": {
            "type": "Property",
            "value": round(turbidity + random.uniform(-0.2, 0.2), 2),
            "unitCode": "NTU",
            "observedAt": lag_1h.isoformat().replace("+00:00", "Z")
        },
        "flowLag1h": {
            "type": "Property",
            "value": round(flow + random.uniform(-40, 40), 1),
            "unitCode": "Q37",
            "observedAt": lag_1h.isoformat().replace("+00:00", "Z")
        },
        "temperatureLag1h": {
            "type": "Property",
            "value": round(temperature + random.uniform(-0.3, 0.3), 1),
            "unitCode": "CEL",
            "observedAt": lag_1h.isoformat().replace("+00:00", "Z")
        },
        "ozoneDosageLag1h": {
            "type": "Property",
            "value": round(ozone_dosage + random.uniform(-0.2, 0.2), 2),
            "unitCode": "P99",
            "substance": {
                "type": "Property",
                "value": "O3"
            },
            "observedAt": lag_1h.isoformat().replace("+00:00", "Z")
        },
        "rawInfluent": {
            "type": "Relationship",
            "object": "urn:ngsi-ld:DrinkingWaterTreatment:OzonationProcess:Leiduin"
        },
        "givesInput": {
            "type": "Relationship",
            "object": "urn:ngsi-ld:DrinkingWaterSimulation:OzonationSoftSensor:Leiduin:SoSe10"
        },
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        ]
    },
    {
        "id": "urn:ngsi-ld:DrinkingWaterTreatment:OzonationProcess:Leiduin",
        "type": "OzonationProcess",
        "name": {
            "type": "Property",
            "value": "Ozonation Process - Leiduin"
        },
        "description": {
            "type": "Property",
            "value": "Synthetic ozonation treatment process providing operational input to the ozonation soft sensor suite."
        },
        "dateObserved": {
            "type": "Property",
            "value": now.isoformat().replace("+00:00", "Z")
        },
        "chemicalDosage": {
            "type": "Property",
            "value": ozone_dosage,
            "unitCode": "P99",
            "substance": {
                "type": "Property",
                "value": "O3"
            },
            "observedAt": now.isoformat().replace("+00:00", "Z")
        },
        "laneOperate": {
            "type": "Property",
            "value": [
                {"lane": 1, "compartmentOperate": "1.1 - 1.9"},
                {"lane": 2, "compartmentOperate": "2.1 - 2.9"},
                {"lane": 3, "compartmentOperate": "3.1 - 3.9"},
                {"lane": 4, "compartmentOperate": "4.1 - 4.9"}
            ]
        },
        "givesInput": {
            "type": "Relationship",
            "object": "urn:ngsi-ld:DrinkingWaterSimulation:OzonationSoftSensor:Leiduin:SoSe10"
        },
        "isSimulatedBy": {
            "type": "Relationship",
            "object": "urn:ngsi-ld:DrinkingWaterSimulation:OzonationSoftSensor:Leiduin:SoSe10"
        },
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        ]
    },
    {
        "id": "urn:ngsi-ld:DrinkingWaterSimulation:OzonationSoftSensor:Leiduin:SoSe10",
        "type": "OzonationSoftSensor",
        "name": {
            "type": "Property",
            "value": "SoSe #10 - Ozonation Soft Sensor Suite"
        },
        "description": {
            "type": "Property",
            "value": "Synthetic representation of the ozonation soft sensor suite including CT ozone exposure, bromate formation, and coliform log removal."
        },
        "module": {
            "type": "Property",
            "value": "Treatment"
        },
        "process": {
            "type": "Property",
            "value": "Ozonation"
        },
        "modelComponents": {
            "type": "Property",
            "value": [
                "SoSe #10 - CT ozone exposure model",
                "SoSe #10.1 - Bromate formation model",
                "SoSe #10.2 - Coliform log removal model"
            ]
        },
        "hasInput": {
            "type": "Relationship",
            "object": [
                "urn:ngsi-ld:WaterQualityObserved:OzonationInlet:Leiduin:SoSe10Input",
                "urn:ngsi-ld:DrinkingWaterTreatment:OzonationProcess:Leiduin"
            ]
        },
        "treatedEffluentWater": {
            "type": "Relationship",
            "object": "urn:ngsi-ld:DrinkingWaterSimulation:OzonationEffluent:Leiduin:SoSe10Output"
        },
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        ]
    },
    {
        "id": "urn:ngsi-ld:DrinkingWaterSimulation:OzonationEffluent:Leiduin:SoSe10Output",
        "type": "OzonationEffluent",
        "name": {
            "type": "Property",
            "value": "Ozonation Effluent - Leiduin"
        },
        "description": {
            "type": "Property",
            "value": "Synthetic predicted treated effluent water quality after ozonation."
        },
        "dateObserved": {
            "type": "Property",
            "value": now.isoformat().replace("+00:00", "Z")
        },
        "chemicalConcentration": {
            "type": "Property",
            "value": bromate,
            "unitCode": "P99",
            "substance": {
                "type": "Property",
                "value": "BrO3-"
            },
            "observedAt": now.isoformat().replace("+00:00", "Z")
        },
        "ozoneExposure": {
            "type": "Property",
            "value": ozone_exposure,
            "unitCode": "F34",
            "observedAt": now.isoformat().replace("+00:00", "Z")
        },
        "logColiformRemoval": {
            "type": "Property",
            "value": log_coliform_removal,
            "unitCode": "F35",
            "observedAt": now.isoformat().replace("+00:00", "Z")
        },
        "generatedBy": {
            "type": "Relationship",
            "object": "urn:ngsi-ld:DrinkingWaterSimulation:OzonationSoftSensor:Leiduin:SoSe10"
        },
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        ]
    }
]

output_path = Path(__file__).parent / "sose10_ozonation_synthetic_generated.json"

with open(output_path, "w", encoding="utf-8") as file:
    json.dump(payload, file, indent=2)

print(f"Synthetic SoSe #10 ozonation NGSI-LD payload created: {output_path}")