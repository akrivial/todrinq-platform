from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional

from app.routes.predict import CoagulationInput, run_coagulation_prediction
from app.services.ozonation_predictions import (
    predict_ct,
    predict_bromate,
    predict_coliform,
)

router = APIRouter(tags=["Risk Module"])


# --------------------------------------------------
# INPUT MODELS
# --------------------------------------------------
class SourceRiskInput(BaseModel):
    predicted_turbidity: float
    current_turbidity: Optional[float] = None
    prediction_timestamp: Optional[str] = None
    threshold: float = 15.0
    yopi_sensitive: bool = False
    reset_history: bool = False


class RLRiskInput(BaseModel):
    current_fecl3_dose: float
    recommended_fecl3_dose: float
    output_turbidity: float
    confidence: float


class CTInput(BaseModel):
    Chamber: float
    WaterTemperature: float
    RFTurbidity: float
    FlowRate: float
    Ozonedosage: float


class BromateInput(BaseModel):
    month: float
    Chamber: float
    WaterTemperature: float
    RFTurbidity: float
    FlowRate: float
    Ozonedosage: float
    Residencetime: float
    WaterTemperature_1: float
    RFturbidity_1: float
    FlowRate_1: float
    Ozonedosage_1: float
    CT_All: float


class ColiformInput(BaseModel):
    Chamber: float
    WaterTemperature: float
    RFTurbidity: float
    FlowRate: float
    Ozonedosage: float
    RFturbidity_1: float
    CT_All: float


class OzonationRiskInput(BaseModel):
    ct: CTInput
    bromate: BromateInput
    coliform: ColiformInput
    yopi_sensitive: bool = False


class OzonationOperationalInput(BaseModel):
    bromate_pred: float
    ct_pred: float
    coliform_pred: float


class DistributionRiskInput(BaseModel):
    aeromonas_probability: float
    residual_disinfectant_low: bool = False
    warm_water_condition: bool = False
    stagnation_risk: bool = False
    yopi_sensitive: bool = False


class TreatmentRiskInput(BaseModel):
    coagulation: CoagulationInput
    rl: Optional[RLRiskInput] = None
    ozonation: OzonationRiskInput
    yopi_sensitive: bool = False


class SystemRiskInput(BaseModel):
    source: SourceRiskInput
    treatment: TreatmentRiskInput
    distribution: DistributionRiskInput


# --------------------------------------------------
# CONSTANTS
# --------------------------------------------------
MODULE_RISK = "Risk"
MODULE_SOURCE = "Source / Intake"
MODULE_TREATMENT = "Treatment"
MODULE_DISTRIBUTION = "Distribution"

SOSE_9_NAME = "SoSe #9 - Early prediction of turbidity in DWTP inlet"
SOSE_8_NAME = "SoSe #8 - Estimation of turbidity of the coagulation-flocculation process"
RL_5_NAME = "RL #5 - FeCl3 dosage advisory for coagulation process"
SOSE_10_NAME = "SoSe #10 - Prediction of the ozonation exposure, CT, to improve the ozonation process"
SOSE_101_NAME = "SoSe #10.1 - Bromate formation model"
SOSE_102_NAME = "SoSe #10.2 - Coliform removal model"
SOSE_11_NAME = "SoSe #11 - Aeromonas prediction model"
BACTOSENSE_4_NAME = "BactoSense #4"

# Thresholds currently used in the risk logic
SOURCE_TURBIDITY_THRESHOLD = 5.0
SOSE9_REF_P5 = 7.8
SOSE9_REF_P50 = 15.0
SOSE9_REF_P90 = 23.0
SOSE9_REF_P95 = 28.0
SOSE9_MODERATE_THRESHOLD = SOSE9_REF_P50   # FTU - reference median, not health threshold
SOSE9_HIGH_THRESHOLD     = SOSE9_REF_P95   # FTU - very unusual reference band
SOSE9_HIGH_PERSISTENCE_COUNT = 3  # hourly exceedances required before operational High Risk
COAGULATION_LOW_THRESHOLD    = 6.0   # NTU — Waternet operational boundary
COAGULATION_MEDIUM_THRESHOLD = 9.0   # NTU — Waternet high-risk boundary
COAGULATION_TURBIDITY_THRESHOLD = COAGULATION_LOW_THRESHOLD  # kept for RL classifier compat.
CT_THRESHOLD = 0.7
BROMATE_LOW     = 5.0   # µg/L — EU DWD compliance boundary
BROMATE_HIGH    = 10.0  # µg/L — EU DWD limit
BROMATE_THRESHOLD = BROMATE_HIGH
COLIFORM_LOG_HIGH    = 1.2   # log removal — adequate disinfection
COLIFORM_LOG_MODERATE = 0.85  # log removal — warning zone
COLIFORM_THRESHOLD = COLIFORM_LOG_HIGH
AEROMONAS_THRESHOLD = 0.3


# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def unwrap(x):
    try:
        if hasattr(x, "tolist"):
            x = x.tolist()
        if isinstance(x, list):
            return float(x[0])
        return float(x)
    except Exception:
        return x


def clamp_score(value: int) -> int:
    return max(1, min(5, int(value)))


def score_to_class(score: int) -> str:
    score = clamp_score(score)
    if score <= 2:
        return "Low"
    if score == 3:
        return "Moderate"
    return "High"


def make_band(score: int, extra: dict | None = None) -> dict:
    payload = {
        "class": score_to_class(score),
        "score": clamp_score(score),
    }
    if extra:
        payload.update(extra)
    return payload


def overall_from_scores(*scores: int) -> dict:
    max_score = max(scores) if scores else 1
    return {
        "class": score_to_class(max_score),
        "score": clamp_score(max_score),
    }


def aggregate_risk_classes(classes: list[str]) -> dict:
    normalized = [str(c or "").lower() for c in classes if c]
    if any(c in ("high", "critical") for c in normalized):
        return {"class": "High", "score": 5}
    if any(c in ("moderate", "medium") for c in normalized):
        return {"class": "Moderate", "score": 3}
    return {"class": "Low", "score": 1}


def action_from_class(risk_class: str) -> str:
    if risk_class == "High":
        return "Immediate operator review and mitigation are recommended."
    if risk_class == "Moderate":
        return "Increase monitoring frequency and review operational settings."
    return "Maintain routine monitoring and continue normal operation."


def build_response(
    *,
    submodule: str,
    sensor: str,
    sensor_or_model: str,
    hazard_id: str,
    hazard_description: str,
    prediction,
    threshold,
    likelihood: dict,
    severity: dict,
    consequence: dict,
    overall_risk: dict,
    recommended_action: str,
    yopi_sensitive: bool = False,
    short_term_actions: list[str] | None = None,
    long_term_actions: list[str] | None = None,
    operator_message: str | None = None,
    graph_payload: dict | None = None,
):
    return {
        "module": MODULE_RISK,
        "submodule": submodule,
        "sensor": sensor,
        "sensor_or_model": sensor_or_model,
        "hazard_id": hazard_id,
        "hazard_description": hazard_description,
        "prediction": prediction,
        "threshold": threshold,
        "likelihood": likelihood,
        "severity": severity,
        "consequence": consequence,
        "overall_risk": overall_risk,
        "recommended_action": recommended_action,
        "short_term_actions": short_term_actions or [],
        "long_term_actions": long_term_actions or [],
        "operator_message": operator_message,
        "reviewer_summary": (
            f"{sensor} is translated into a {overall_risk['class'].lower()} risk level "
            f"based on likelihood, severity, and consequence."
        ),
        "vulnerable_groups": {
            "note": (
                "YOPI-sensitive condition considered in the severity assessment."
                if yopi_sensitive
                else ""
            )
        },
        "graph_payload": graph_payload or {},
    }


# --------------------------------------------------
# RISK CLASSIFIERS
# --------------------------------------------------
SOSE9_HOURLY_HISTORY: list[dict] = []
SOSE9_MANUAL_SEQUENCE = 0


def _sose9_hour_key(prediction_timestamp: Optional[str]) -> str:
    global SOSE9_MANUAL_SEQUENCE

    if prediction_timestamp:
        raw = prediction_timestamp.replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0).isoformat()

    SOSE9_MANUAL_SEQUENCE += 1
    return f"manual-{SOSE9_MANUAL_SEQUENCE}"


def _record_sose9_hourly_prediction(
    *,
    predicted_turbidity: float,
    prediction_timestamp: Optional[str] = None,
    reset_history: bool = False,
) -> tuple[int, list[dict]]:
    if reset_history:
        SOSE9_HOURLY_HISTORY.clear()

    hour_key = _sose9_hour_key(prediction_timestamp)
    entry = {
        "hour_key": hour_key,
        "prediction": round(predicted_turbidity, 4),
        "exceeds_high_threshold": predicted_turbidity > SOSE9_REF_P95,
    }

    for idx, existing in enumerate(SOSE9_HOURLY_HISTORY):
        if existing["hour_key"] == hour_key:
            SOSE9_HOURLY_HISTORY[idx] = entry
            break
    else:
        SOSE9_HOURLY_HISTORY.append(entry)

    SOSE9_HOURLY_HISTORY[:] = SOSE9_HOURLY_HISTORY[-24:]

    consecutive = 0
    for item in reversed(SOSE9_HOURLY_HISTORY):
        if not item["exceeds_high_threshold"]:
            break
        consecutive += 1

    return consecutive, list(SOSE9_HOURLY_HISTORY[-SOSE9_HIGH_PERSISTENCE_COUNT:])


def classify_source_risk(
    predicted_turbidity: float,
    threshold: float = SOSE9_MODERATE_THRESHOLD,
    yopi_sensitive: bool = False,
    current_turbidity: Optional[float] = None,
    prediction_timestamp: Optional[str] = None,
    reset_history: bool = False,
):
    consecutive_exceedances, recent_history = _record_sose9_hourly_prediction(
        predicted_turbidity=predicted_turbidity,
        prediction_timestamp=prediction_timestamp,
        reset_history=reset_history,
    )

    if predicted_turbidity < SOSE9_REF_P5:
        risk_class = "Low"
        operational_label = "Low / below P5 reference"
        score = 1
        likelihood_score = 1
        operator_message = "Predicted inlet turbidity is below the P5 reference value for 2022-2024."
        short_term = ["Continue routine monitoring of raw water quality."]
        long_term = [
            "Maintain current intake strategy.",
            "TODO(Akrivi/Greg/Alex): validate that 2026 turbidity percentiles still match the 2022-2024 reference distribution before freezing final operator levels.",
        ]
    elif predicted_turbidity <= SOSE9_REF_P50:
        risk_class = "Low"
        operational_label = "Normal / P5-P50 reference band"
        score = 1
        likelihood_score = 1
        operator_message = "Predicted inlet turbidity is within the low/normal P5-P50 reference band."
        short_term = ["Continue routine monitoring of raw water quality."]
        long_term = [
            "Maintain current intake strategy.",
            "TODO(Akrivi/Greg/Alex): validate that 2026 turbidity percentiles still match the 2022-2024 reference distribution before freezing final operator levels.",
        ]
    elif predicted_turbidity <= SOSE9_REF_P90:
        risk_class = "Moderate"
        operational_label = "Attention / P50-P90 reference band"
        score = 3
        likelihood_score = 2
        operator_message = "Predicted inlet turbidity is above the 2022-2024 median. Be attentive for coagulation."
        short_term = [
            "High inlet turbidity may create operational pressure downstream; check coagulation readiness and source-water conditions.",
        ]
        long_term = [
            "If high values are frequent, check model/input drift, whether the 2022-2024 reference period is still valid for 2026, and investigate possible source causes such as river conditions, upstream/Germany influence, shipping activity, or intake events.",
            "TODO(Akrivi/Greg/Alex): validate that temperature-from-PIMS and turbidity percentile logic remain representative for 2026 operation.",
        ]
    elif predicted_turbidity <= SOSE9_REF_P95:
        risk_class = "Moderate"
        operational_label = "High attention / top 10% of reference values"
        score = 3
        likelihood_score = 3
        operator_message = "Predicted inlet turbidity is in the top 10% of 2022-2024 reference values. Be attentive for coagulation."
        short_term = [
            "High inlet turbidity may create operational pressure downstream; check coagulation readiness and source-water conditions.",
        ]
        long_term = [
            "If high values are frequent, check model/input drift, whether the 2022-2024 reference period is still valid for 2026, and investigate possible source causes such as river conditions, upstream/Germany influence, shipping activity, or intake events.",
            "TODO(Akrivi/Greg/Alex): validate that 2026 turbidity percentiles still match the 2022-2024 reference distribution before freezing final operator levels.",
        ]
    elif consecutive_exceedances < SOSE9_HIGH_PERSISTENCE_COUNT:
        risk_class = "Moderate"
        operational_label = "Very unusual / above P95"
        score = 3
        likelihood_score = 3
        operator_message = (
            "Predicted inlet turbidity is above P95 of the 2022-2024 reference distribution. "
            "Continue monitoring and check whether this becomes a persistent trend."
        )
        short_term = [
            "High inlet turbidity may create operational pressure downstream; check coagulation readiness and source-water conditions.",
        ]
        long_term = [
            "If high values are frequent, check model/input drift, whether the 2022-2024 reference period is still valid for 2026, and investigate possible source causes such as river conditions, upstream/Germany influence, shipping activity, or intake events.",
            "TODO(Akrivi/Greg/Alex): validate P95-based source-attention escalation before operational release.",
        ]
    else:
        risk_class = "High"
        operational_label = "Persistent very unusual trend"
        score = 5
        likelihood_score = 3
        operator_message = (
            "Predicted inlet turbidity has been above P95 for 3 consecutive hourly predictions/observations. "
            "Escalate from attention to trend investigation."
        )
        short_term = [
            "High inlet turbidity may create operational pressure downstream; check coagulation readiness and source-water conditions.",
            "Investigate trend persistence and source-water conditions before changing treatment automatically.",
        ]
        long_term = [
            "If high values are frequent, check model/input drift, whether the 2022-2024 reference period is still valid for 2026, and investigate possible source causes such as river conditions, upstream/Germany influence, shipping activity, or intake events.",
            "TODO(Akrivi/Greg/Alex): validate the persistent-trend escalation rule against historical operations.",
        ]

    # Source turbidity is upstream awareness, not immediate finished-water non-compliance.
    severity_score = 1
    overall = {"class": risk_class, "score": score}
    ratio_to_high = predicted_turbidity / SOSE9_REF_P95

    graph_data: dict = {
        "predicted_turbidity": round(predicted_turbidity, 4),
        "unit": "FTU",
        "reference_percentiles_2022_2024": {
            "P5": SOSE9_REF_P5,
            "P50": SOSE9_REF_P50,
            "P90": SOSE9_REF_P90,
            "P95": SOSE9_REF_P95,
            "attention_reference_line": "20 FTU - be attentive for coagulation",
            "unit": "FTU",
        },
        "prediction_frequency": "hourly",
        "consecutive_high_threshold_exceedances": consecutive_exceedances,
        "required_consecutive_high_threshold_exceedances": SOSE9_HIGH_PERSISTENCE_COUNT,
        "operational_risk": operational_label,
        "recent_hourly_predictions": recent_history,
    }
    if current_turbidity is not None:
        graph_data["current_turbidity"] = round(current_turbidity, 4)

    response = build_response(
        submodule="Source / Intake",
        sensor="Inlet turbidity prediction",
        sensor_or_model=SOSE_9_NAME,
        hazard_id="high_turbidity_source",
        hazard_description=(
            "Predicted inlet turbidity is interpreted as an operational attention/probability band "
            "against the 2022-2024 reference distribution."
        ),
        prediction=predicted_turbidity,
        threshold=None,
        likelihood={
            "class": risk_class,
            "score": likelihood_score,
            "probability_proxy": round(min(max(ratio_to_high, 0.0), 1.0), 3),
        },
        severity={
            "class": "Low",
            "score": severity_score,
            "basis": "Upstream awareness / dune-area and coagulation attention; not immediate finished-water non-compliance.",
        },
        consequence={"class": "Low", "score": severity_score},
        overall_risk=overall,
        recommended_action=action_from_class(overall["class"]),
        yopi_sensitive=yopi_sensitive,
        short_term_actions=short_term,
        long_term_actions=long_term,
        operator_message=operator_message,
        graph_payload=graph_data,
    )
    response.update({
        "risk_categories": ["Low", "Moderate", "High"],
        "traffic_light": {
            "level": risk_class.lower(),
            "color": "green" if risk_class == "Low" else ("amber" if risk_class == "Moderate" else "red"),
            "thresholds": {
                "p5": SOSE9_REF_P5,
                "p50": SOSE9_REF_P50,
                "p90": SOSE9_REF_P90,
                "p95": SOSE9_REF_P95,
                "attention_reference_line": 20.0,
                "unit": "FTU",
            },
        },
        "sose9_persistence": {
            "latest_prediction": round(predicted_turbidity, 4),
            "primary_horizon": "1h ahead is the preferred/most accurate horizon when available; current backend prediction may be 3h depending on route.",
            "unit": "FTU",
            "prediction_frequency": "hourly",
            "high_threshold": SOSE9_REF_P95,
            "high_threshold_label": ">P95 (28 FTU)",
            "consecutive_exceedances": consecutive_exceedances,
            "required_consecutive_exceedances": SOSE9_HIGH_PERSISTENCE_COUNT,
            "display_count": f"{min(consecutive_exceedances, SOSE9_HIGH_PERSISTENCE_COUNT)}/{SOSE9_HIGH_PERSISTENCE_COUNT}",
            "operational_risk": operational_label,
            "recent_hourly_predictions": recent_history,
        },
        "reference_percentiles": {
            "period": "2022-2024",
            "unit": "FTU",
            "P5": SOSE9_REF_P5,
            "P50": SOSE9_REF_P50,
            "P90": SOSE9_REF_P90,
            "P90_label": "top 10% of reference values",
            "P95": SOSE9_REF_P95,
            "attention_reference_line": "20 FTU - be attentive for coagulation",
        },
        "validation_todos": [
            "TODO(Akrivi/Greg/Alex): validate whether 2026 turbidity percentiles still match the 2022-2024 reference distribution before freezing final operator levels.",
            "TODO(Akrivi/Greg/Alex): confirm whether and where a 1h SoSe #9 horizon is available so it can be made primary in the backend response.",
        ],
    })
    return response


def classify_coagulation_risk(prediction: float):
    # ── Traffic-light classification (Waternet expert thresholds) ────────
    if prediction <= COAGULATION_LOW_THRESHOLD:
        risk_level = "low"
        tl_color, tl_icon = "green", "🟢"
        operator_card = "🟢 Low Risk — Continue normal operation and routine monitoring."
        short_term = ["Continue routine monitoring of turbidity and downstream filter performance."]
        long_term  = ["Maintain coagulation model calibration."]
        operator_message = "Coagulation performance is within acceptable operational limits. No action required."
    elif prediction <= COAGULATION_MEDIUM_THRESHOLD:
        risk_level = "medium"
        tl_color, tl_icon = "amber", "🟡"
        operator_card = "🟡 Medium Risk — Review FeCl₃ dosage and increase monitoring frequency."
        short_term = [
            "Increase/check coagulant dosage and consult RL #5 if additional dosing support is needed.",
            "Verify mixing and flocculation conditions.",
            "Increase monitoring frequency of turbidity and downstream filter performance.",
        ]
        long_term  = [
            "Assess whether coagulation model recalibration is needed.",
            "Review raw-water quality trends (pH, temperature, NOM load).",
        ]
        operator_message = (
            "Outlet turbidity is elevated (6–9 NTU). Increase/check coagulant dosage, "
            "consult RL #5 if additional dosing support is needed, and monitor downstream filtration."
        )
    else:
        risk_level = "high"
        tl_color, tl_icon = "red", "🔴"
        operator_card = "🔴 High Risk — Immediate investigation and process adjustment required."
        short_term = [
            "Immediate operator attention required.",
            "Increase/check coagulant dosage immediately and monitor downstream filtration.",
            "Inspect dosing equipment.",
            "Inspect mixing conditions and flocculation performance.",
            "Verify raw-water quality changes (turbidity, NOM, pH, temperature).",
            "Prepare for increased filter loading or additional operational interventions.",
        ]
        long_term  = [
            "If values above 9 NTU occur often, investigate filter backwashing frequency and potential effects on sand filters.",
            "Assess backwash/environmental burden, model/input drift, and process conditions at Waternet.",
            "Review coagulation control strategy and model accuracy.",
        ]
        operator_message = (
            "Outlet turbidity exceeds 9 NTU — immediate investigation required. "
            "Check coagulant dosage, inspect process performance, and assess potential impacts "
            "on downstream filtration."
        )

    # ── Probabilistic likelihood (p = predicted / high threshold) ────────
    p = min(prediction / COAGULATION_MEDIUM_THRESHOLD, 1.0)
    lh_cls, lh_n = ("Low", 1) if p < 0.15 else (("Moderate", 2) if p < 0.40 else ("High", 3))

    # ── Severity (deviation above low threshold, normalised) ─────────────
    dev = max(0.0, (prediction - COAGULATION_LOW_THRESHOLD) / COAGULATION_MEDIUM_THRESHOLD)
    # Outlet turbidity has at least moderate severity because poor coagulation/sedimentation
    # can increase filter loading, backwashing frequency, breakthrough risk, and clogging.
    sv_cls, sv_n = ("Moderate", 2) if dev < 0.40 else ("High", 3)

    risk_score = lh_n * sv_n
    risk_score_cls = "Low" if risk_score <= 2 else ("Moderate" if risk_score <= 4 else "High")

    consequence_score = max(lh_n, sv_n)
    overall = overall_from_scores(lh_n, sv_n, consequence_score)

    response = build_response(
        submodule="Treatment / Coagulation",
        sensor="Outlet turbidity after coagulation/sedimentation",
        sensor_or_model=SOSE_8_NAME,
        hazard_id="high_turbidity_after_coagulation",
        hazard_description=(
            "Predicted outlet turbidity is used as an indicator of coagulation-flocculation performance. "
            "Elevated values indicate insufficient particle removal and potential downstream treatment stress."
        ),
        prediction=prediction,
        threshold=COAGULATION_LOW_THRESHOLD,
        likelihood=make_band(lh_n, {"probability_proxy": round(p, 3)}),
        severity=make_band(sv_n, {"deviation_above_low_threshold": round(dev, 3)}),
        consequence=make_band(consequence_score),
        overall_risk=overall,
        recommended_action=action_from_class(overall["class"]),
        short_term_actions=short_term,
        long_term_actions=long_term,
        operator_message=operator_message,
        graph_payload={
            "predicted_turbidity": prediction,
            "threshold_low": COAGULATION_LOW_THRESHOLD,
            "threshold_medium": COAGULATION_MEDIUM_THRESHOLD,
            "p95_context": "Approx. P95 = 8.7 FTU when percentile context is displayed.",
        },
    )

    # Append the traffic-light card fields to the response
    response["traffic_light"] = {
        "level": risk_level,
        "color": tl_color,
        "icon": tl_icon,
        "operator_card": operator_card,
        "thresholds": {
            "low_boundary": COAGULATION_LOW_THRESHOLD,
            "medium_boundary": COAGULATION_MEDIUM_THRESHOLD,
            "unit": "NTU",
        },
    }
    response["risk_table_row"] = {
        "hazard": "Outlet turbidity after coagulation/flocculation/sedimentation",
        "predicted_value": round(prediction, 3),
        "unit": "NTU",
        "threshold": COAGULATION_LOW_THRESHOLD,
        "threshold_label": "Waternet low-risk limit",
        "likelihood_p": round(p, 3),
        "likelihood_class": lh_cls,
        "likelihood_num": lh_n,
        "severity_dev": round(dev, 3),
        "severity_class": sv_cls,
        "severity_num": sv_n,
        "risk_score": risk_score,
        "risk_class": risk_score_cls,
        "traffic_light": risk_level,
        "mitigation": operator_card,
    }
    return response


def classify_rl_risk(
    current_fecl3_dose: float,
    recommended_fecl3_dose: float,
    output_turbidity: float,
    confidence: float,
):
    dose_deviation = abs(recommended_fecl3_dose - current_fecl3_dose)
    relative_deviation = (
        dose_deviation / current_fecl3_dose
        if current_fecl3_dose > 0
        else dose_deviation
    )

    if dose_deviation <= 0.5:
        likelihood_score = 2
    elif dose_deviation <= 2.0:
        likelihood_score = 3
    else:
        likelihood_score = 5

    if output_turbidity <= 2:
        severity_score = 2
    elif output_turbidity <= COAGULATION_TURBIDITY_THRESHOLD:
        severity_score = 3
    else:
        severity_score = 4

    if confidence < 0.6:
        severity_score += 1

    severity_score = clamp_score(severity_score)
    consequence_score = max(likelihood_score, severity_score)
    overall = overall_from_scores(likelihood_score, severity_score, consequence_score)

    return build_response(
        submodule="Treatment / Coagulation",
        sensor="RL #5",
        sensor_or_model=RL_5_NAME,
        hazard_id="incorrect_rl_dose_application",
        hazard_description="Applying an RL-recommended dose without sufficient confidence or deviation review may destabilize coagulation performance.",
        prediction=recommended_fecl3_dose,
        threshold=current_fecl3_dose,
        likelihood=make_band(
            likelihood_score,
            {"probability_proxy": round(min(relative_deviation, 1.0), 3)},
        ),
        severity=make_band(
            severity_score,
            {"deviation_ratio": round(relative_deviation, 3)},
        ),
        consequence=make_band(consequence_score),
        overall_risk=overall,
        recommended_action=action_from_class(overall["class"]),
        short_term_actions=[
            "Review the RL recommendation before implementation.",
            "Compare current and recommended FeCl3 doses.",
            "Verify predicted output turbidity against plant targets.",
        ],
        long_term_actions=[
            "Validate RL recommendations with historical operator decisions.",
            "Introduce confidence-based acceptance rules.",
        ],
        operator_message="Apply RL output carefully and verify operator acceptance before adjusting dose.",
        graph_payload={
            "current_fecl3_dose": current_fecl3_dose,
            "recommended_fecl3_dose": recommended_fecl3_dose,
            "dose_deviation": round(dose_deviation, 3),
            "confidence": confidence,
        },
    )


def classify_ct_risk(prediction: float):
    if prediction >= CT_THRESHOLD:
        likelihood_score = 2
    elif prediction >= 0.3:
        likelihood_score = 3
    else:
        likelihood_score = 5

    if prediction >= CT_THRESHOLD:
        severity_score = 2
    elif prediction >= 0.3:
        severity_score = 3
    else:
        severity_score = 4

    consequence_score = max(likelihood_score, severity_score)
    overall = overall_from_scores(likelihood_score, severity_score, consequence_score)

    return build_response(
        submodule="Treatment / Ozonation",
        sensor="SoSe #10",
        sensor_or_model=SOSE_10_NAME,
        hazard_id="insufficient_ct",
        hazard_description="Insufficient CT may compromise disinfection performance in the ozonation stage.",
        prediction=prediction,
        threshold=CT_THRESHOLD,
        likelihood=make_band(
            likelihood_score,
            {"probability_proxy": round(max(0.0, CT_THRESHOLD - prediction), 3)},
        ),
        severity=make_band(
            severity_score,
            {"deviation_ratio": round(prediction / CT_THRESHOLD, 3)},
        ),
        consequence=make_band(consequence_score),
        overall_risk=overall,
        recommended_action=action_from_class(overall["class"]),
        short_term_actions=[
            "Review ozone dosage and hydraulic conditions.",
            "Check flow rate and contact time assumptions.",
        ],
        long_term_actions=[
            "Refine CT model calibration.",
            "Improve operational envelopes for ozone control.",
        ],
        operator_message="Low CT values require immediate review of disinfection performance.",
        graph_payload={"ct_value": prediction},
    )


def classify_bromate_risk(prediction: float):
    if prediction < BROMATE_LOW:
        likelihood_score = 2
        severity_score = 2
        traffic_light = "green"
        traffic_label = "Low risk"
    elif prediction < BROMATE_HIGH:
        likelihood_score = 3
        severity_score = 3
        traffic_light = "amber"
        traffic_label = "Moderate risk"
    else:
        likelihood_score = 5
        severity_score = 5
        traffic_light = "red"
        traffic_label = "High risk"

    consequence_score = max(likelihood_score, severity_score)
    overall = overall_from_scores(likelihood_score, severity_score, consequence_score)

    moderate_message = "Check ozone dosage and input conditions."
    high_message = "Act now: review/reduce ozone dose where disinfection requirements allow and check process inputs."

    return build_response(
        submodule="Treatment / Ozonation",
        sensor="Bromate",
        sensor_or_model=SOSE_101_NAME,
        hazard_id="bromate_formation_risk",
        hazard_description="High bromate formation threatens EU DWD compliance (10 µg/L limit) and water-quality objectives.",
        prediction=prediction,
        threshold=BROMATE_HIGH,
        likelihood=make_band(likelihood_score, {"probability_proxy": round(min(prediction / BROMATE_HIGH, 1.0), 3)}),
        severity=make_band(severity_score, {"deviation_ratio": round(prediction / BROMATE_HIGH, 3)}),
        consequence=make_band(consequence_score),
        overall_risk=overall,
        recommended_action=action_from_class(overall["class"]),
        short_term_actions=[
            high_message if prediction >= BROMATE_HIGH else moderate_message if prediction >= BROMATE_LOW else "Maintain routine bromate monitoring.",
            "Check bromide concentration, pH, water temperature, ozone dose, CT/contact time, and ozone residual.",
        ],
        long_term_actions=[
            "Reconsider ozonation strategy/disinfection credits if bromate values remain elevated.",
            "Review input sensor quality.",
            "Verify whether ozone settings remain appropriate.",
        ],
        operator_message=(
            high_message
        ) if prediction >= BROMATE_HIGH else (
            moderate_message
        ) if prediction >= BROMATE_LOW else "✅ Bromate is below 5 µg/L. No immediate action required.",
        graph_payload={
            "bromate_prediction": prediction,
            "traffic_light": traffic_light,
            "traffic_label": traffic_label,
            "threshold_low": BROMATE_LOW,
            "threshold_high": BROMATE_HIGH,
            "unit": "µg/L",
        },
    )


def classify_coliform_risk(prediction: float):
    # Higher log removal = safer; risk increases as log removal decreases
    if prediction > COLIFORM_LOG_HIGH:
        likelihood_score = 2
        severity_score = 2
        traffic_light = "green"
        traffic_label = "Low risk"
    elif prediction >= COLIFORM_LOG_MODERATE:
        likelihood_score = 3
        severity_score = 3
        traffic_light = "amber"
        traffic_label = "Moderate risk"
    else:
        likelihood_score = 5
        severity_score = 5
        traffic_light = "red"
        traffic_label = "High risk"

    consequence_score = max(likelihood_score, severity_score)
    overall = overall_from_scores(likelihood_score, severity_score, consequence_score)

    return build_response(
        submodule="Treatment / Ozonation",
        sensor="Microbial removal",
        sensor_or_model=SOSE_102_NAME,
        hazard_id="insufficient_coliform_removal",
        hazard_description="Low predicted coliform log removal indicates insufficient microbial risk reduction in ozonation.",
        prediction=prediction,
        threshold=COLIFORM_LOG_HIGH,
        likelihood=make_band(likelihood_score, {"probability_proxy": round(max(0.0, COLIFORM_LOG_HIGH - prediction), 3)}),
        severity=make_band(severity_score, {"deviation_ratio": round(prediction / COLIFORM_LOG_HIGH, 3) if COLIFORM_LOG_HIGH > 0 else 0}),
        consequence=make_band(consequence_score),
        overall_risk=overall,
        recommended_action=action_from_class(overall["class"]),
        short_term_actions=[
            "Check ozone residual, CT value, and flow rate.",
            "Review contact time and turbidity conditions.",
            "Inspect ozone-generator performance.",
            "Consider increasing ozone dose to improve disinfection capacity.",
        ],
        long_term_actions=[
            "Refine microbial removal validation against independent measurements.",
            "Link model outputs to microbial safety margins and regulatory targets.",
        ],
        operator_message=(
            "🚨 Coliform log removal is below 0.85 — disinfection capacity is insufficient. "
            "Check ozone residual, CT, flow rate, contact time, turbidity, and ozone-generator performance. "
            "Advise improving disinfection capacity."
        ) if prediction < COLIFORM_LOG_MODERATE else (
            "⚡ Coliform log removal is in the warning zone (0.85–1.2). "
            "Monitor closely and verify ozonation conditions."
        ) if prediction <= COLIFORM_LOG_HIGH else "✅ Coliform log removal > 1.2. Adequate microbial risk reduction.",
        graph_payload={
            "coliform_prediction": prediction,
            "ct_dependency_note": "Connect microbial-removal risk to validated CT/log-removal targets before using EPA/reference tables operationally.",
            "long_term_average_context": "Awaiting annual/long-term average log-removal context.",
            "traffic_light": traffic_light,
            "traffic_label": traffic_label,
            "threshold_moderate": COLIFORM_LOG_MODERATE,
            "threshold_high": COLIFORM_LOG_HIGH,
            "unit": "log removal",
        },
    )


def classify_distribution_risk(
    aeromonas_probability: float,
    residual_disinfectant_low: bool,
    warm_water_condition: bool,
    stagnation_risk: bool,
    yopi_sensitive: bool,
):
    likelihood_score = 2
    if aeromonas_probability > AEROMONAS_THRESHOLD:
        likelihood_score = 3
    if aeromonas_probability > 0.6:
        likelihood_score = 5

    severity_score = 2
    if residual_disinfectant_low:
        severity_score += 1
    if warm_water_condition:
        severity_score += 1
    if stagnation_risk:
        severity_score += 1
    if yopi_sensitive:
        severity_score += 1

    severity_score = clamp_score(severity_score)
    consequence_score = max(likelihood_score, severity_score)
    overall = overall_from_scores(likelihood_score, severity_score, consequence_score)

    return build_response(
        submodule="Distribution",
        sensor="SoSe #11",
        sensor_or_model=SOSE_11_NAME,
        hazard_id="distribution_biological_instability",
        hazard_description="Biological instability in the distribution system may increase Aeromonas occurrence and downstream health risk.",
        prediction=aeromonas_probability,
        threshold=AEROMONAS_THRESHOLD,
        likelihood=make_band(
            likelihood_score,
            {"probability_proxy": round(aeromonas_probability, 3)},
        ),
        severity=make_band(
            severity_score,
            {
                "deviation_ratio": round(
                    aeromonas_probability / AEROMONAS_THRESHOLD, 3
                )
            },
        ),
        consequence=make_band(consequence_score),
        overall_risk=overall,
        recommended_action=action_from_class(overall["class"]),
        yopi_sensitive=yopi_sensitive,
        short_term_actions=[
            "Review residual disinfectant status.",
            "Inspect warm-water and stagnation-prone zones.",
        ],
        long_term_actions=[
            "Improve network flushing and monitoring strategy.",
            "Refine biological instability prediction logic.",
        ],
        operator_message="Distribution conditions suggest increased biological instability risk.",
        graph_payload={
            "aeromonas_probability": aeromonas_probability,
            "residual_disinfectant_low": residual_disinfectant_low,
            "warm_water_condition": warm_water_condition,
            "stagnation_risk": stagnation_risk,
        },
    )


# --------------------------------------------------
# OVERVIEW
# --------------------------------------------------
@router.get("/overview", summary="Risk module overview")
def risk_overview():
    return {
        "module": MODULE_RISK,
        "description": (
            "Transforms hard-sensor and soft-sensor predictions into actionable risk "
            "levels, reasons, and mitigation measures across Source, Treatment, and Distribution."
        ),
        "available_risk_functions": [
            "/risk/source/sose-9/current",
            "/risk/coagulation",
            "/risk/treatment/rl-5/current (advisory validation status only; excluded from aggregation)",
            "/risk/ct",
            "/risk/bromate",
            "/risk/coliform",
            "/risk/ozonation/current",
            "/risk/ozonation/operational",
            "/risk/distribution/sose-11/current",
            "/risk/treatment/current",
            "/risk/system/current",
        ],
        "modules_supported": [
            MODULE_SOURCE,
            MODULE_TREATMENT,
            MODULE_DISTRIBUTION,
        ],
        "sensors_and_models_in_platform": [
            {
                "name": SOSE_9_NAME,
                "type": "Soft sensor",
                "module": "Source / Intake",
                "status": "Implemented",
                "utility": "Waternet #DC1",
            },
            {
                "name": SOSE_8_NAME,
                "type": "Soft sensor",
                "module": "Treatment - Coagulation",
                "status": "Implemented",
                "utility": "Waternet #DC1",
            },
            {
                "name": RL_5_NAME,
                "type": "Reinforcement-learning advisory",
                "module": "Treatment - Coagulation",
                "status": "Under validation; excluded from risk aggregation",
                "utility": "Waternet #DC1",
            },
            {
                "name": SOSE_10_NAME,
                "type": "Soft sensor",
                "module": "Treatment - Ozonation",
                "status": "Implemented",
                "utility": "Waternet #DC1",
            },
            {
                "name": SOSE_101_NAME,
                "type": "Soft sensor",
                "module": "Treatment - Ozonation",
                "status": "Implemented",
                "utility": "Waternet #DC1",
            },
            {
                "name": SOSE_102_NAME,
                "type": "Soft sensor",
                "module": "Treatment - Ozonation",
                "status": "Implemented",
                "utility": "Waternet #DC1",
            },
            {
                "name": SOSE_11_NAME,
                "type": "Soft sensor",
                "module": "Distribution",
                "status": "Under evaluation / subject to change",
                "utility": "Waternet #DC1",
            },
            {
                "name": BACTOSENSE_4_NAME,
                "type": "Hard sensor",
                "module": "Treatment",
                "status": "Connected conceptually / to be aligned in UI",
                "utility": "Waternet #DC1",
            },
        ],
    }


# --------------------------------------------------
# INDIVIDUAL RISK ENDPOINTS
# --------------------------------------------------
@router.post("/source/sose-9/current", summary="Source SoSe #9 risk assessment")
def source_risk(data: SourceRiskInput):
    return classify_source_risk(
        predicted_turbidity=data.predicted_turbidity,
        threshold=data.threshold,
        yopi_sensitive=data.yopi_sensitive,
        current_turbidity=data.current_turbidity,
        prediction_timestamp=data.prediction_timestamp,
        reset_history=data.reset_history,
    )


@router.post("/coagulation", summary="Coagulation risk assessment")
def coagulation_risk(body: CoagulationInput):
    try:
        prediction = unwrap(run_coagulation_prediction(body))
        return classify_coagulation_risk(prediction)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Coagulation risk assessment failed: {str(e)}",
        )


@router.post("/treatment/rl-5/current", summary="RL #5 dosage risk assessment")
def rl5_risk(data: RLRiskInput):
    return {
        "module": MODULE_RISK,
        "submodule": "Treatment / Coagulation",
        "sensor": "Coagulant dosing advisory",
        "sensor_or_model": RL_5_NAME,
        "assessment_type": "advisory_validation_status",
        "included_in_risk_aggregation": False,
        "overall_risk": {"class": "Low", "score": 1},
        "prediction": data.recommended_fecl3_dose,
        "unit": "mg/L",
        "operator_message": (
            "RL #5 supports mitigation/advisory dosing only and is under validation. "
            "Do not interpret this endpoint as a risk-producing output."
        ),
        "validation_status": "under validation",
        "validation_todos": [
            "TODO(Greg): verify ACTION_MAP, dose unit conversion, and model-output interpretation before final release.",
            "TODO(Akrivi/Greg/Alex): confirm whether the confidence/status field should be derived from Q-values or a separate validation layer.",
        ],
    }


@router.post("/ct", summary="CT risk assessment")
def ct_risk(data: CTInput):
    try:
        pred = unwrap(
            predict_ct([[
                data.Chamber,
                data.WaterTemperature,
                data.RFTurbidity,
                data.FlowRate,
                data.Ozonedosage,
            ]])
        )
        return classify_ct_risk(pred)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"CT risk assessment failed: {str(e)}",
        )


@router.post("/bromate", summary="Bromate risk assessment")
def bromate_risk(data: BromateInput):
    try:
        pred = unwrap(
            predict_bromate([[
                data.month,
                data.Chamber,
                data.WaterTemperature,
                data.RFTurbidity,
                data.FlowRate,
                data.Ozonedosage,
                data.Residencetime,
                data.WaterTemperature_1,
                data.RFturbidity_1,
                data.FlowRate_1,
                data.Ozonedosage_1,
                data.CT_All,
            ]])
        )
        return classify_bromate_risk(pred)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Bromate risk assessment failed: {str(e)}",
        )


@router.post("/coliform", summary="Coliform-removal risk assessment")
def coliform_risk(data: ColiformInput):
    try:
        pred = unwrap(
            predict_coliform([[
                data.Chamber,
                data.WaterTemperature,
                data.RFTurbidity,
                data.FlowRate,
                data.Ozonedosage,
                data.RFturbidity_1,
                data.CT_All,
            ]])
        )
        return classify_coliform_risk(pred)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Coliform risk assessment failed: {str(e)}",
        )


# --------------------------------------------------
# COMBINED OZONATION RISK
# --------------------------------------------------
@router.post("/ozonation/current", summary="Combined ozonation risk")
def ozonation_risk(data: OzonationRiskInput):
    try:
        ct_component = ct_risk(data.ct)
        bromate_component = bromate_risk(data.bromate)
        coliform_component = coliform_risk(data.coliform)

        overall = overall_from_scores(
            ct_component["overall_risk"]["score"],
            bromate_component["overall_risk"]["score"],
            coliform_component["overall_risk"]["score"],
        )

        return {
            "module": MODULE_RISK,
            "submodule": "Treatment / Ozonation",
            "overall_risk": overall,
            "recommended_action": action_from_class(overall["class"]),
            "components": {
                "ct": ct_component,
                "bromate": bromate_component,
                "coliform": coliform_component,
            },
            "reviewer_summary": "Combined ozonation risk integrates CT, bromate, and coliform-related model outputs.",
            "vulnerable_groups": {
                "note": (
                    "YOPI-sensitive condition considered in the ozonation risk review."
                    if data.yopi_sensitive
                    else ""
                )
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Combined ozonation risk failed: {str(e)}",
        )


# --------------------------------------------------
# OPERATIONAL OZONATION RISK  (pre-computed predictions → inline card + risk module)
# --------------------------------------------------
@router.post("/ozonation/operational", summary="Operational ozonation risk — traffic light + probabilistic risk table")
def ozonation_operational_risk(data: OzonationOperationalInput):

    # ── Traffic-light classification ──────────────────────────────────────
    def _tl(level): return {"low": ("green","🟢"), "moderate": ("amber","🟡"), "high": ("red","🔴")}[level]

    # Bromate: low <5 µg/L; moderate 5-10; high >=10
    br_level = "high" if data.bromate_pred >= BROMATE_HIGH else ("moderate" if data.bromate_pred >= BROMATE_LOW else "low")
    br_color, br_icon = _tl(br_level)

    # CT: threshold = 0.7 mg/L·min; high <0.3, moderate 0.3-0.7, low ≥0.7
    ct_level = "high" if data.ct_pred < 0.3 else ("moderate" if data.ct_pred < CT_THRESHOLD else "low")
    ct_color, ct_icon = _tl(ct_level)

    # Coliform log removal: threshold = 1.2; high <0.85, moderate 0.85-1.2, low >1.2
    co_level = "high" if data.coliform_pred < COLIFORM_LOG_MODERATE else ("moderate" if data.coliform_pred <= COLIFORM_LOG_HIGH else "low")
    co_color, co_icon = _tl(co_level)

    # ── Probabilistic likelihood (P of exceeding operational threshold) ───
    # Bromate: p = predicted / threshold_max; higher prediction = higher probability of exceedance
    br_p = min(data.bromate_pred / BROMATE_HIGH, 1.0)
    # CT: p = max(0, (threshold - predicted) / threshold); lower CT = higher probability of failure
    ct_p = max(0.0, (CT_THRESHOLD - data.ct_pred) / CT_THRESHOLD)
    # Coliform: p = max(0, (adequate - predicted) / adequate); lower removal = higher failure probability
    co_p = max(0.0, (COLIFORM_LOG_HIGH - data.coliform_pred) / COLIFORM_LOG_HIGH)

    def _likelihood_class(p):
        if p < 0.15:  return "Low",      1
        if p < 0.40:  return "Moderate", 2
        return               "High",     3

    br_lh_cls, br_lh_n = _likelihood_class(br_p)
    ct_lh_cls, ct_lh_n = _likelihood_class(ct_p)
    co_lh_cls, co_lh_n = _likelihood_class(co_p)
    if br_level == "high":
        br_lh_cls, br_lh_n = "High", 3

    # ── Severity (consequence of exceeding threshold) ────────────────────
    # Deviation = how far the prediction has moved beyond (or toward) the threshold
    # Bromate: deviation above max threshold
    br_dev = max(0.0, (data.bromate_pred - BROMATE_HIGH) / BROMATE_HIGH)
    # CT: deviation below adequate threshold
    ct_dev = max(0.0, (CT_THRESHOLD - data.ct_pred) / CT_THRESHOLD)
    # Coliform: deviation below adequate log removal
    co_dev = max(0.0, (COLIFORM_LOG_HIGH - data.coliform_pred) / COLIFORM_LOG_HIGH)

    def _severity_class(dev):
        if dev < 0.10: return "Low",      1
        if dev < 0.40: return "Moderate", 2
        return                "High",     3

    br_sv_cls, br_sv_n = _severity_class(br_dev)
    ct_sv_cls, ct_sv_n = _severity_class(ct_dev)
    co_sv_cls, co_sv_n = _severity_class(co_dev)
    if br_level == "high":
        br_sv_cls, br_sv_n = "High", 3
    if ct_level == "high":
        ct_sv_cls, ct_sv_n = "High", 3
    if co_level == "high":
        co_sv_cls, co_sv_n = "High", 3

    # ── Risk score = likelihood × severity (1–9 scale) ───────────────────
    def _score_class(s):
        if s <= 2:  return "Low"
        if s <= 4:  return "Moderate"
        return             "High"

    br_score = br_lh_n * br_sv_n
    ct_score = ct_lh_n * ct_sv_n
    co_score = co_lh_n * co_sv_n
    overall_score_num = max(br_score, ct_score, co_score)
    overall_label = _score_class(overall_score_num)

    # ── Trade-off & operational message logic ─────────────────────────────
    disinfection_insufficient = ct_level != "low" or co_level != "low"
    trade_off = br_level == "high" and disinfection_insufficient

    if trade_off:
        overall_label = "Critical"
        bromate_message = (
            "⚠️ Bromate is already moderate or high. Do NOT automatically increase ozone dose. "
            "This is an operational trade-off: increasing ozone improves disinfection but "
            "increases bromate formation. Escalate to operator review immediately."
        )
        coliform_message = (
            "🚨 Coliform log removal is insufficient. Disinfection improvement is needed, "
            "but ozone increase is constrained by bromate risk — operator review required."
        )
        combined_message = (
            "🚨 CRITICAL OPERATIONAL TRADE-OFF detected. Coliform log removal is insufficient "
            "AND bromate risk is already moderate/high. Increasing ozone dose may improve "
            "disinfection but will further increase bromate formation. "
            "Do NOT apply an automatic dosage change. Escalate to senior operator and process engineer."
        )
        short_term = [
            "Do not change ozone dose automatically.",
            "Escalate to senior operator and process engineer.",
            "Check bromide concentration, pH, temperature, ozone dose, CT/contact time, and ozone residual.",
            "Evaluate bromate-control strategies (pH adjustment, ammonia/chloramine, H₂O₂) only after expert review.",
            "Assess whether improved CT via contact-time adjustment (not dose increase) is feasible.",
        ]
    elif co_level == "high" and br_level == "low":
        bromate_message = "✅ Bromate is low — ozone dose increase is safe from a bromate perspective."
        coliform_message = (
            "🚨 Coliform log removal is insufficient. Recommend increasing ozone dose or improving CT/contact time. "
            "Bromate risk is low, so this action is operationally safe."
        )
        combined_message = (
            "🚨 Coliform disinfection is insufficient. Bromate risk is low, so increasing ozone dose "
            "or extending contact time is the recommended corrective action."
        )
        short_term = [
            "Increase ozone dose or extend contact time to improve coliform log removal.",
            "Check ozone residual, CT, flow rate, turbidity, and ozone-generator performance.",
            "Monitor bromate during and after ozone dose increase.",
        ]
    elif br_level == "high":
        bromate_message = (
            "🔴 Bromate is at or above 10 µg/L (EU DWD limit). Act now: review/reduce ozone dose "
            "where disinfection requirements allow and check process inputs."
        )
        coliform_message = (
            "✅ Coliform log removal is adequate." if co_level == "low"
            else "⚡ Coliform log removal is in the warning zone — monitor closely."
        )
        combined_message = (
            "⚠️ Bromate risk is HIGH while CT/log-removal appears sufficient. Review decreasing ozone dose "
            "or adjusting ozonation strategy, while maintaining required disinfection credits."
        )
        short_term = [
            "Check bromide concentration, pH, water temperature, ozone dose, CT/contact time, and ozone residual.",
            "Review/reduce ozone dose where disinfection requirements allow.",
            "Evaluate pH adjustment or other bromate-control strategies only after expert review.",
        ]
    elif co_level == "moderate":
        bromate_message = (
            "⚡ Bromate is in the warning zone (5–10 µg/L) — monitor trend." if br_level == "moderate"
            else "✅ Bromate is below 5 µg/L. No bromate intervention required."
        )
        coliform_message = (
            "⚡ Coliform log removal is in the warning zone (0.85–1.2). "
            "Preventive check: ozone residual, CT, flow rate, contact time, turbidity, and ozone-generator performance."
        )
        combined_message = (
            "⚡ Coliform log removal is in the moderate-risk zone. "
            "Perform preventive checks on ozone residual, CT, flow rate, contact time, "
            "turbidity, and ozone-generator performance. Increase monitoring frequency."
        )
        short_term = [
            "Check ozone residual, CT, flow rate, contact time, turbidity, and ozone-generator performance.",
            "Increase monitoring frequency for coliform removal.",
            "Monitor bromate trend." if br_level == "moderate" else "Maintain routine bromate monitoring.",
        ]
    elif br_level == "moderate":
        bromate_message = (
            "⚡ Bromate is in the warning zone (5–10 µg/L). "
            "Track trend and review ozone dose, pH, and contact conditions."
        )
        coliform_message = "✅ Coliform log removal is adequate. No immediate action required."
        combined_message = (
            "⚡ Bromate is in the warning zone. Track trend and review ozone dose, pH, and contact conditions. "
            "Coliform removal is adequate."
        )
        short_term = [
            "Track bromate trend and review ozone dose, pH, and contact time.",
            "Verify bromide concentration and upstream conditions.",
        ]
    else:
        bromate_message = "✅ Bromate is below 5 µg/L. No intervention required."
        coliform_message = "✅ Coliform log removal > 1.2. Adequate microbial risk reduction."
        combined_message = "✅ Normal operation. All ozonation parameters are within safe operational limits. No immediate intervention required."
        short_term = ["Maintain routine monitoring of ozone residual, bromate, and coliform removal."]

    # ── Prioritized risk table ────────────────────────────────────────────
    risk_table = [
        {
            "hazard": "Bromate formation",
            "predicted_value": round(data.bromate_pred, 3),
            "unit": "µg/L",
            "threshold": BROMATE_HIGH,
            "threshold_label": "EU DWD limit",
            "likelihood_p": round(br_p, 3),
            "likelihood_class": br_lh_cls,
            "likelihood_num": br_lh_n,
            "severity_dev": round(br_dev, 3),
            "severity_class": br_sv_cls,
            "severity_num": br_sv_n,
            "risk_score": br_score,
            "risk_class": _score_class(br_score),
            "traffic_light": br_level,
            "mitigation": (
                "Optimise ozone dose; check bromide, pH, temperature, CT/contact time; "
                "evaluate pH adjustment and bromate-control strategies after expert review."
            ),
        },
        {
            "hazard": "CT / ozone exposure",
            "predicted_value": round(data.ct_pred, 3),
            "unit": "mg/L·min",
            "threshold": CT_THRESHOLD,
            "threshold_label": "Adequate CT",
            "likelihood_p": round(ct_p, 3),
            "likelihood_class": ct_lh_cls,
            "likelihood_num": ct_lh_n,
            "severity_dev": round(ct_dev, 3),
            "severity_class": ct_sv_cls,
            "severity_num": ct_sv_n,
            "risk_score": ct_score,
            "risk_class": _score_class(ct_score),
            "traffic_light": ct_level,
            "mitigation": "Review ozone dosage, contact time, and hydraulic conditions.",
        },
        {
            "hazard": "Microbial/log removal",
            "predicted_value": round(data.coliform_pred, 3),
            "unit": "log removal",
            "threshold": COLIFORM_LOG_HIGH,
            "threshold_label": "Adequate log removal",
            "likelihood_p": round(co_p, 3),
            "likelihood_class": co_lh_cls,
            "likelihood_num": co_lh_n,
            "severity_dev": round(co_dev, 3),
            "severity_class": co_sv_cls,
            "severity_num": co_sv_n,
            "risk_score": co_score,
            "risk_class": _score_class(co_score),
            "traffic_light": co_level,
            "mitigation": (
                "Check ozone residual, CT, flow rate, contact time, turbidity, and ozone-generator performance. "
                "Increase ozone dose only if bromate risk is low and disinfection review supports it."
            ),
        },
    ]
    # Sort by descending risk score (highest priority first)
    risk_table.sort(key=lambda x: -x["risk_score"])

    return {
        "module": MODULE_RISK,
        "submodule": "Treatment / Ozonation",
        "assessment_type": "operational",
        "overall_risk": {"class": overall_label, "score": overall_score_num},
        "trade_off_detected": trade_off,
        "trade_off_warning": trade_off,
        "combined_message": combined_message,
        "short_term_actions": short_term,
        "bromate_indicator": {
            "label": "Bromate Risk",
            "value": round(data.bromate_pred, 3),
            "unit": "µg/L",
            "level": br_level,
            "color": br_color,
            "icon": br_icon,
            "thresholds": {"low_boundary": BROMATE_LOW, "high_boundary": BROMATE_HIGH},
            "guideline": "EU DWD: 10 µg/L",
            "message": bromate_message,
        },
        "coliform_indicator": {
            "label": "Coliform Risk",
            "value": round(data.coliform_pred, 3),
            "unit": "log removal",
            "level": co_level,
            "color": co_color,
            "icon": co_icon,
            "thresholds": {"moderate_boundary": COLIFORM_LOG_MODERATE, "low_boundary": COLIFORM_LOG_HIGH},
            "message": coliform_message,
        },
        "ct_indicator": {
            "label": "CT Exposure",
            "value": round(data.ct_pred, 3),
            "unit": "mg/L·min",
            "level": ct_level,
            "color": ct_color,
            "icon": ct_icon,
        },
        "risk_table": risk_table,
        "severity_likelihood_matrix": {
            "bromate":  {"likelihood": br_lh_n, "severity": br_sv_n, "score": br_score, "label": "Bromate"},
            "ct":       {"likelihood": ct_lh_n, "severity": ct_sv_n, "score": ct_score, "label": "CT"},
            "coliform": {"likelihood": co_lh_n, "severity": co_sv_n, "score": co_score, "label": "Coliform"},
            "scale_likelihood": "P(exceeds threshold): Low <0.15 | Moderate 0.15–0.40 | High ≥0.40",
            "scale_severity": "Deviation from threshold: Low <10% | Moderate 10–40% | High >40%",
            "score_formula": "Risk score = Likelihood × Severity (1–9)",
        },
    }


# --------------------------------------------------
# DISTRIBUTION RISK
# --------------------------------------------------
@router.post("/distribution/sose-11/current", summary="Distribution SoSe #11 risk assessment")
def distribution_risk(data: DistributionRiskInput):
    try:
        return classify_distribution_risk(
            aeromonas_probability=data.aeromonas_probability,
            residual_disinfectant_low=data.residual_disinfectant_low,
            warm_water_condition=data.warm_water_condition,
            stagnation_risk=data.stagnation_risk,
            yopi_sensitive=data.yopi_sensitive,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Distribution risk assessment failed: {str(e)}",
        )


# --------------------------------------------------
# TREATMENT CURRENT RISK
# Combines coagulation + RL + ozonation
# --------------------------------------------------
@router.post("/treatment/current", summary="Current treatment risk")
def treatment_current_risk(data: TreatmentRiskInput):
    try:
        coag_component = coagulation_risk(data.coagulation)
        ozonation_component = ozonation_risk(data.ozonation)

        overall = aggregate_risk_classes([
            coag_component["overall_risk"]["class"],
            ozonation_component["overall_risk"]["class"],
        ])

        return {
            "module": MODULE_RISK,
            "submodule": "Treatment",
            "overall_risk": overall,
            "recommended_action": action_from_class(overall["class"]),
            "components": {
                "coagulation": coag_component,
                "ozonation": ozonation_component,
            },
            "excluded_components": {
                "rl5": "RL #5 is advisory/mitigation support and is excluded from treatment risk aggregation.",
            },
            "reviewer_summary": "Treatment risk combines active risk-producing coagulation and ozonation outputs. RL #5 is excluded.",
            "vulnerable_groups": {
                "note": (
                    "YOPI-sensitive condition considered in the treatment risk review."
                    if data.yopi_sensitive
                    else ""
                )
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Treatment current risk failed: {str(e)}",
        )


# --------------------------------------------------
# SYSTEM CURRENT RISK - POST
# --------------------------------------------------
@router.post("/system/current", summary="Current system-wide risk")
def system_current_risk_post(data: SystemRiskInput):
    try:
        source_component = source_risk(data.source)
        treatment_component = treatment_current_risk(data.treatment)
        distribution_component = distribution_risk(data.distribution)

        overall = aggregate_risk_classes([
            source_component["overall_risk"]["class"],
            treatment_component["overall_risk"]["class"],
            distribution_component["overall_risk"]["class"],
        ])

        dominant = max(
            [
                ("Source / Intake", source_component["overall_risk"]["score"]),
                ("Treatment", treatment_component["overall_risk"]["score"]),
                ("Distribution", distribution_component["overall_risk"]["score"]),
            ],
            key=lambda x: x[1],
        )[0]

        return {
            "module": MODULE_RISK,
            "submodule": "System",
            "overall_risk": overall,
            "system_status": "connected",
            "dominant_module": dominant,
            "recommended_action": action_from_class(overall["class"]),
            "components": {
                "source": source_component,
                "treatment": treatment_component,
                "distribution": distribution_component,
            },
            "reviewer_summary": "System risk aggregates Source, Treatment, and Distribution risk responses into one source-to-tap view.",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"System current risk failed: {str(e)}",
        )


# --------------------------------------------------
# SYSTEM CURRENT RISK - GET PLACEHOLDER
# --------------------------------------------------
@router.get("/system/current", summary="Current system-wide risk placeholder")
def system_current_risk_get():
    return {
        "module": MODULE_RISK,
        "submodule": "System",
        "note": (
            "This GET endpoint is a lightweight placeholder. "
            "Use POST /risk/system/current for the full connected source-to-tap risk calculation."
        ),
        "overall_risk": {"class": "Moderate", "score": 3},
        "system_status": "partially_connected",
        "dominant_module": MODULE_TREATMENT,
        "recommended_action": (
            "Review treatment risk outputs first; connect Source / Intake "
            f"({SOSE_9_NAME}) and Distribution ({SOSE_11_NAME}) to enable full system aggregation."
        ),
    }
