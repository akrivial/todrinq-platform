# app/services/risk.py

def classify_turbidity_6h(v: float):
    if v > 6:
        return {
            "risk_level": "high",
            "risk_score": 3,
            "reason": "Turbidity > 6 NTU (alarm threshold).",
            "mitigation": "Adjust FeCl3 dosing, check pH and flocculation, consider backwash.",
        }
    if v >= 4:
        return {
            "risk_level": "moderate",
            "risk_score": 2,
            "reason": "Turbidity in 4–6 NTU range.",
            "mitigation": "Increase monitoring and optimise coagulation.",
        }
    return {
        "risk_level": "low",
        "risk_score": 1,
        "reason": "Turbidity < 4 NTU.",
        "mitigation": "Normal operation.",
    }


def classify_ct(v: float):
    if v < 0.6:
        return {
            "risk_level": "high",
            "risk_score": 3,
            "reason": "Low CT indicates potentially insufficient disinfection.",
            "mitigation": "Increase ozone dose or contact time.",
        }
    if v < 1.0:
        return {
            "risk_level": "moderate",
            "risk_score": 2,
            "reason": "CT is in a warning range.",
            "mitigation": "Monitor closely and verify ozonation settings.",
        }
    return {
        "risk_level": "low",
        "risk_score": 1,
        "reason": "CT is acceptable.",
        "mitigation": "Continue normal operation.",
    }


def classify_bromate(v: float):
    if v > 10:
        return {
            "risk_level": "high",
            "risk_score": 3,
            "reason": "Bromate exceeds 10 µg/L.",
            "mitigation": "Reduce ozone dose and review precursor conditions.",
        }
    if v >= 5:
        return {
            "risk_level": "moderate",
            "risk_score": 2,
            "reason": "Bromate is elevated (5–10 µg/L).",
            "mitigation": "Track trend and optimise process.",
        }
    return {
        "risk_level": "low",
        "risk_score": 1,
        "reason": "Bromate is below 5 µg/L.",
        "mitigation": "No immediate action required.",
    }


def classify_coliform(v: float):
    if v < 2:
        return {
            "risk_level": "high",
            "risk_score": 3,
            "reason": "Low coliform log removal.",
            "mitigation": "Check disinfection performance.",
        }
    if v < 3:
        return {
            "risk_level": "moderate",
            "risk_score": 2,
            "reason": "Moderate coliform removal.",
            "mitigation": "Increase monitoring.",
        }
    return {
        "risk_level": "low",
        "risk_score": 1,
        "reason": "Adequate coliform removal.",
        "mitigation": "Normal operation.",
    }


def overall_risk(*scores):
    max_score = max(scores)

    if max_score == 3:
        return "high", "Immediate action required."
    if max_score == 2:
        return "moderate", "Preventive action recommended."
    return "low", "System stable."