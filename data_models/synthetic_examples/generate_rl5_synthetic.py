import json
import random
from datetime import datetime, timezone
from pathlib import Path

# now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
timestamp = now.isoformat().replace("+00:00", "Z")

turbidity = round(random.uniform(0.8, 8.0), 2)
temperature = round(random.uniform(8.0, 18.0), 1)
ph = round(random.uniform(7.0, 8.2), 2)
flow = round(random.uniform(850.0, 1200.0), 1)
current_dose = round(random.uniform(15.0, 35.0), 1)

recommended_dose = round(current_dose + random.uniform(-5.0, 3.0), 1)
recommended_dose = max(5.0, min(recommended_dose, 40.0))

dose_adjustment = round(recommended_dose - current_dose, 1)

if dose_adjustment < -0.5:
    recommendation_type = "Decrease dose"
elif dose_adjustment > 0.5:
    recommendation_type = "Increase dose"
else:
    recommendation_type = "Maintain current dose"

payload = [
    {
        "id": "urn:ngsi-ld:WaterQualityObserved:CoagulationInfluent:Leiduin:RL5Input",
        "type": "WaterQualityObserved",
        "name": {
            "type": "Property",
            "value": "Coagulation Influent Water Quality - Leiduin"
        },
        "description": {
            "type": "Property",
            "value": "Synthetic influent water quality and operational parameters used as input for RL #5 FeCl3 dosage recommendation."
        },
        "dateObserved": {
            "type": "Property",
            "value": timestamp
        },
        "month": {
            "type": "Property",
            "value": now.month
        },
        "turbidity": {
            "type": "Property",
            "value": turbidity,
            "unitCode": "NTU",
            "observedAt": timestamp
        },
        "temperature": {
            "type": "Property",
            "value": temperature,
            "unitCode": "CEL",
            "observedAt": timestamp
        },
        "pH": {
            "type": "Property",
            "value": ph,
            "unitCode": "Q30",
            "observedAt": timestamp
        },
        "flow": {
            "type": "Property",
            "value": flow,
            "unitCode": "Q37",
            "observedAt": timestamp
        },
        "currentFerricChlorideDose": {
            "type": "Property",
            "value": current_dose,
            "unitCode": "M1",
            "substance": {
                "type": "Property",
                "value": "FeCl3"
            },
            "observedAt": timestamp
        },
        "lane": {
            "type": "Property",
            "value": random.randint(1, 4)
        },
        "daysSinceDredging": {
            "type": "Property",
            "value": random.randint(1, 90),
            "unitCode": "DAY"
        },
        "givesInput": {
            "type": "Relationship",
            "object": "urn:ngsi-ld:DrinkingWaterSimulation:CoagulationDoseRecommendation:Leiduin:RL5"
        },
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        ]
    },
    {
        "id": "urn:ngsi-ld:DrinkingWaterTreatment:CoagulationProcess:Leiduin",
        "type": "CoagulationProcess",
        "name": {
            "type": "Property",
            "value": "Coagulation Process - Leiduin"
        },
        "description": {
            "type": "Property",
            "value": "Synthetic coagulation process entity connected to the RL #5 dosage recommendation model."
        },
        "dateObserved": {
            "type": "Property",
            "value": timestamp
        },
        "chemicalDosage": {
            "type": "Property",
            "value": current_dose,
            "unitCode": "M1",
            "substance": {
                "type": "Property",
                "value": "FeCl3"
            },
            "observedAt": timestamp
        },
        "processObjective": {
            "type": "Property",
            "value": "Optimise FeCl3 dosing while maintaining acceptable coagulation performance."
        },
        "isOptimisedBy": {
            "type": "Relationship",
            "object": "urn:ngsi-ld:DrinkingWaterSimulation:CoagulationDoseRecommendation:Leiduin:RL5"
        },
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        ]
    },
    {
        "id": "urn:ngsi-ld:DrinkingWaterSimulation:CoagulationDoseRecommendation:Leiduin:RL5",
        "type": "CoagulationDoseRecommendation",
        "name": {
            "type": "Property",
            "value": "RL #5 - Optimal FeCl3 Dosage Recommendation"
        },
        "description": {
            "type": "Property",
            "value": "Synthetic NGSI-LD representation of the reinforcement-learning-based model for recommending FeCl3 dosage during coagulation."
        },
        "module": {
            "type": "Property",
            "value": "Treatment"
        },
        "process": {
            "type": "Property",
            "value": "Coagulation"
        },
        "modelType": {
            "type": "Property",
            "value": "Reinforcement Learning"
        },
        "controlledParameter": {
            "type": "Property",
            "value": "FeCl3 dosage"
        },
        "hasInput": {
            "type": "Relationship",
            "object": [
                "urn:ngsi-ld:WaterQualityObserved:CoagulationInfluent:Leiduin:RL5Input",
                "urn:ngsi-ld:DrinkingWaterTreatment:CoagulationProcess:Leiduin"
            ]
        },
        "givesRecommendation": {
            "type": "Relationship",
            "object": "urn:ngsi-ld:DrinkingWaterTreatment:CoagulationDoseRecommendationOutput:Leiduin:RL5Output"
        },
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        ]
    },
    {
        "id": "urn:ngsi-ld:DrinkingWaterTreatment:CoagulationDoseRecommendationOutput:Leiduin:RL5Output",
        "type": "CoagulationDoseRecommendationOutput",
        "name": {
            "type": "Property",
            "value": "Recommended FeCl3 Dosage - Leiduin"
        },
        "description": {
            "type": "Property",
            "value": "Synthetic output generated by RL #5 for FeCl3 dosage recommendation."
        },
        "dateObserved": {
            "type": "Property",
            "value": timestamp
        },
        "recommendedFerricChlorideDose": {
            "type": "Property",
            "value": recommended_dose,
            "unitCode": "M1",
            "substance": {
                "type": "Property",
                "value": "FeCl3"
            },
            "observedAt": timestamp
        },
        "currentFerricChlorideDose": {
            "type": "Property",
            "value": current_dose,
            "unitCode": "M1",
            "substance": {
                "type": "Property",
                "value": "FeCl3"
            },
            "observedAt": timestamp
        },
        "doseAdjustment": {
            "type": "Property",
            "value": dose_adjustment,
            "unitCode": "M1"
        },
        "recommendationType": {
            "type": "Property",
            "value": recommendation_type
        },
        "expectedOperationalEffect": {
            "type": "Property",
            "value": "Potential chemical saving while maintaining coagulation performance."
        },
        "generatedBy": {
            "type": "Relationship",
            "object": "urn:ngsi-ld:DrinkingWaterSimulation:CoagulationDoseRecommendation:Leiduin:RL5"
        },
        "@context": [
            "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
        ]
    }
]

output_path = Path(__file__).parent / "rl5_synthetic_generated.json"

with open(output_path, "w", encoding="utf-8") as file:
    json.dump(payload, file, indent=2)

print(f"Synthetic RL #5 NGSI-LD payload created: {output_path}")