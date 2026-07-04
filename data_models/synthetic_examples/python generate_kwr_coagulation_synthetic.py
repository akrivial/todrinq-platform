import json
import random
from datetime import datetime, timezone
from pathlib import Path

# now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
timestamp = now.isoformat().replace("+00:00", "Z")

ftu_raw_water = round(random.uniform(5.0, 25.0), 2)
temperature_raw_water = round(random.uniform(6.0, 20.0), 1)
ph_raw_water = round(random.uniform(7.0, 8.5), 2)
ferric_chloride_dose = round(random.uniform(1.0, 5.0), 2)
lane = random.randint(1, 4)
days_since_dredging = random.randint(1, 250)

effluent_turbidity = round(
    max(0.1, ftu_raw_water * random.uniform(0.05, 0.15)),
    2
)

payload = [
    {
        "id": "urn:ngsi-ld:DrinkingWaterSimulation:CoagulationSoftSensor:Nieuwegein:SoSe8",
        "type": "CoagulationSoftSensor",
        "name": {
            "type": "Property",
            "value": "SoSe #8 - Coagulation Soft Sensor (Nieuwegein)"
        },
        "description": {
            "type": "Property",
            "value": "Synthetic NGSI-LD representation of the KWR coagulation soft sensor used to predict turbidity at the outlet of the coagulation-flocculation process."
        },
        "module": {
            "type": "Property",
            "value": "Treatment"
        },
        "process": {
            "type": "Property",
            "value": "Coagulation-Flocculation"
        },
        "hasInput": {
            "type": "Relationship",
            "object": [
                "urn:ngsi-ld:WaterQualityObserved:LekCanal:SoSe8Input",
                "urn:ngsi-ld:DrinkingWaterTreatment:CoagulationProcess:Nieuwegein:SoSe8Input"
            ]
        },
        "givesPrediction": {
            "type": "Relationship",
            "object": "urn:ngsi-ld:WaterQualityObserved:CoagulationEffluent:Nieuwegein:SoSe8Output"
        },
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        ]
    },
    {
        "id": "urn:ngsi-ld:WaterQualityObserved:LekCanal:SoSe8Input",
        "type": "WaterQualityObserved",
        "name": {
            "type": "Property",
            "value": "Raw Water Quality Observation - Lek Canal"
        },
        "description": {
            "type": "Property",
            "value": "Synthetic raw-water quality observation used as input for the KWR coagulation soft sensor."
        },
        "dateObserved": {
            "type": "Property",
            "value": timestamp
        },
        "year": {
            "type": "Property",
            "value": now.year
        },
        "ftuRawWater": {
            "type": "Property",
            "value": ftu_raw_water,
            "unitCode": "FTU",
            "observedAt": timestamp
        },
        "temperatureRawWater": {
            "type": "Property",
            "value": temperature_raw_water,
            "unitCode": "CEL",
            "observedAt": timestamp
        },
        "pHRawWater": {
            "type": "Property",
            "value": ph_raw_water,
            "unitCode": "Q30",
            "observedAt": timestamp
        },
        "givesInput": {
            "type": "Relationship",
            "object": "urn:ngsi-ld:DrinkingWaterSimulation:CoagulationSoftSensor:Nieuwegein:SoSe8"
        },
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        ]
    },
    {
        "id": "urn:ngsi-ld:DrinkingWaterTreatment:CoagulationProcess:Nieuwegein:SoSe8Input",
        "type": "CoagulationProcess",
        "name": {
            "type": "Property",
            "value": "Coagulation Process - Nieuwegein"
        },
        "description": {
            "type": "Property",
            "value": "Synthetic coagulation-flocculation process variables used as input for the KWR coagulation soft sensor."
        },
        "dateObserved": {
            "type": "Property",
            "value": timestamp
        },
        "ferricChlorideDose": {
            "type": "Property",
            "value": ferric_chloride_dose,
            "unitCode": "P99",
            "substance": {
                "type": "Property",
                "value": "FeCl3"
            },
            "observedAt": timestamp
        },
        "lane": {
            "type": "Property",
            "value": lane,
            "observedAt": timestamp
        },
        "daysSinceDredging": {
            "type": "Property",
            "value": days_since_dredging,
            "unitCode": "DAY",
            "observedAt": timestamp
        },
        "givesInput": {
            "type": "Relationship",
            "object": "urn:ngsi-ld:DrinkingWaterSimulation:CoagulationSoftSensor:Nieuwegein:SoSe8"
        },
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        ]
    },
    {
        "id": "urn:ngsi-ld:WaterQualityObserved:CoagulationEffluent:Nieuwegein:SoSe8Output",
        "type": "WaterQualityObserved",
        "name": {
            "type": "Property",
            "value": "Predicted Coagulation Effluent - Nieuwegein"
        },
        "description": {
            "type": "Property",
            "value": "Synthetic predicted turbidity at the outlet of the coagulation-flocculation process generated by the KWR coagulation soft sensor."
        },
        "dateObserved": {
            "type": "Property",
            "value": timestamp
        },
        "effluentTurbidity": {
            "type": "Property",
            "value": effluent_turbidity,
            "unitCode": "FTU",
            "observedAt": timestamp
        },
        "generatedBy": {
            "type": "Relationship",
            "object": "urn:ngsi-ld:DrinkingWaterSimulation:CoagulationSoftSensor:Nieuwegein:SoSe8"
        },
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        ]
    }
]

output_path = Path(__file__).parent / "kwr_coagulation_synthetic_generated.json"

with open(output_path, "w", encoding="utf-8") as file:
    json.dump(payload, file, indent=2)

print(f"Synthetic KWR SoSe #8 NGSI-LD payload created: {output_path}")