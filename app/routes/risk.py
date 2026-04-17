from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.routes.predict import CoagulationInput, run_coagulation_prediction
from app.services.ozonation_predictions import (
    predict_ct,
    predict_bromate,
    predict_coliform,
)

router = APIRouter(tags=["Risk Module"])


# =========================================================
# INPUT MODELS
# =========================================================
class SourceRiskInput(BaseModel):
    predicted_turbidity: float = Field(..., description="Predicted raw water turbidity at DWTP inlet")
    threshold: float = Field(5.0, description="Operational turbidity threshold")
    yopi_sensitive: bool = Field(True, description="Whether to emphasize vulnerable consumer groups")


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


class RLDosageRiskInput(BaseModel):
    current_fecl3_dose: float = Field(..., description="Current FeCl3 dose")
    recommended_fecl3_dose: float = Field(..., description="Recommended FeCl3 dose from RL model")
    output_turbidity: Optional[float] = Field(None, description="Observed or predicted output turbidity")
    confidence: float = Field(0.75, description="Confidence/proxy of RL recommendation in [0,1]")


class DistributionRiskInput(BaseModel):
    aeromonas_probability: float = Field(..., description="Predicted probability proxy of Aeromonas occurrence [0,1]")
    residual_disinfectant_low: bool = False
    warm_water_condition: bool = False
    stagnation_risk: bool = False
    yopi_sensitive: bool = True


class OzonationRiskInput(BaseModel):
    ct: CTInput
    bromate: BromateInput
    coliform: ColiformInput
    yopi_sensitive: bool = True


class TreatmentRiskInput(BaseModel):
    coagulation: CoagulationInput
    ozonation: OzonationRiskInput
    rl: Optional[RLDosageRiskInput] = None
    yopi_sensitive: bool = True


class SystemRiskInput(BaseModel):
    source: SourceRiskInput
    treatment: TreatmentRiskInput
    distribution: DistributionRiskInput


# =========================================================
# CONSTANT NAMES
# =========================================================
MODULE_RISK = "Risk"
MODULE_SOURCE = "Source / Intake"
MODULE_TREATMENT = "Treatment"
MODULE_DISTRIBUTION = "Distribution"
MODULE_SYSTEM = "Source-to-tap"

SOSE_9_NAME = "SoSe #9 - Early prediction of turbidity in DWTP inlet"
SOSE_8_NAME = "SoSe #8 - Estimation of turbidity of the coagulation-flocculation process"
RL_4_NAME = "RL #4 - RL Optimal FeCl3 dosage for coagulation process"
SOSE_10_NAME = "SoSe #10 - Prediction of the ozonation exposure, CT, to improve the ozonation process"
SOSE_101_NAME = "SoSe #10.1 - Bromate formation model"
SOSE_102_NAME = "SoSe #10.2 - Coliform removal model"
SOSE_11_NAME = "SoSe #11 - Aeromonas prediction model"
BACTOSENSE_4_NAME = "BactoSense #4"


# =========================================================
# GENERIC HELPERS
# =========================================================
def to_float(value: Any) -> float:
    if isinstance(value, list):
        if not value:
            return 0.0
        return to_float(value[0])
    try:
        return float(value)
    except Exception:
        return 0.0


def level_from_score(score: int) -> str:
    if score <= 2:
        return "Low"
    if score == 3:
        return "Moderate"
    return "High"


def traffic_light(level: str) -> str:
    if level == "Low":
        return "green"
    if level == "Moderate":
        return "amber"
    return "red"


def probability_proxy_from_class(level: str) -> float:
    mapping = {
        "Low": 0.10,
        "Moderate": 0.25,
        "High": 0.60,
    }
    return mapping.get(level, 0.25)


def likelihood_block(level: str, score: int, note: str) -> Dict[str, Any]:
    return {
        "class": level,
        "score": score,
        "probability_proxy": probability_proxy_from_class(level),
        "operational_meaning": note,
    }


def severity_block(level: str, score: int, deviation_ratio: float, note: str) -> Dict[str, Any]:
    return {
        "class": level,
        "score": score,
        "deviation_ratio": round(deviation_ratio, 3),
        "operational_meaning": note,
    }


def consequence_block(level: str, score: int, base_class: Optional[str] = None) -> Dict[str, Any]:
    return {
        "class": level,
        "score": score,
        "base_class": base_class or level,
    }


def overall_risk_block(likelihood_score: int, severity_score: int, consequence_score: int) -> Dict[str, Any]:
    # weighted but still easy to explain
    combined_score = round((0.35 * likelihood_score) + (0.35 * severity_score) + (0.30 * consequence_score), 2)

    if combined_score < 2.0:
        level = "Low"
    elif combined_score < 3.25:
        level = "Moderate"
    else:
        level = "High"

    return {
        "class": level,
        "score": combined_score,
        "traffic_light": traffic_light(level),
    }


def make_graph_payload(
    module_name: str,
    sensor_name: str,
    hazard_id: str,
    risk_obj: Dict[str, Any],
    short_term_actions: List[str],
    long_term_actions: List[str],
) -> Dict[str, Any]:
    return {
        "nodes": [
            {"id": "sensor", "label": sensor_name, "group": "sensor"},
            {"id": "hazard", "label": hazard_id, "group": "hazard"},
            {"id": "risk", "label": risk_obj["overall_risk"]["class"], "group": "risk"},
            {"id": "short", "label": "Short-term actions", "group": "action"},
            {"id": "long", "label": "Long-term actions", "group": "action"},
        ],
        "edges": [
            {"source": "sensor", "target": "hazard"},
            {"source": "hazard", "target": "risk"},
            {"source": "risk", "target": "short"},
            {"source": "risk", "target": "long"},
        ],
        "decision_tree": {
            "root_question": f"Is the current {module_name} condition acceptable?",
            "if_no": {
                "hazard": hazard_id,
                "risk_class": risk_obj["overall_risk"]["class"],
                "short_term_actions": short_term_actions,
                "long_term_actions": long_term_actions,
            },
            "if_yes": {
                "message": "Continue routine monitoring and trend analysis."
            },
        },
    }


def build_risk_response(
    *,
    hazard_id: str,
    hazard_description: str,
    module: str,
    sensor: str,
    parameter: str,
    prediction: Any,
    threshold: Any,
    monitoring_sensors: List[str],
    likelihood: Dict[str, Any],
    severity: Dict[str, Any],
    consequence: Dict[str, Any],
    short_term_actions: List[str],
    long_term_actions: List[str],
    operator_message: str,
    reviewer_summary: str,
    yopi_sensitive: bool = False,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    overall = overall_risk_block(
        likelihood["score"],
        severity["score"],
        consequence["score"],
    )

    response = {
        "hazard_id": hazard_id,
        "hazard_description": hazard_description,
        "module": module,
        "sensor": sensor,
        "parameter": parameter,
        "prediction": prediction,
        "threshold": threshold,
        "monitoring_sensors": monitoring_sensors,
        "likelihood": likelihood,
        "severity": severity,
        "consequence": consequence,
        "overall_risk": overall,
        "short_term_actions": short_term_actions,
        "long_term_actions": long_term_actions,
        "operator_message": operator_message,
        "reviewer_summary": reviewer_summary,
        "vulnerable_groups": {
            "yopi_sensitive": yopi_sensitive,
            "note": (
                "Vulnerable consumers should be prioritized when microbiological protection "
                "or by-product formation may be compromised."
                if yopi_sensitive
                else "No additional YOPI emphasis applied in this assessment."
            ),
        },
    }

    response["graph_payload"] = make_graph_payload(
        module_name=module,
        sensor_name=sensor,
        hazard_id=hazard_id,
        risk_obj=response,
        short_term_actions=short_term_actions,
        long_term_actions=long_term_actions,
    )

    if extra:
        response.update(extra)

    return response


# =========================================================
# HAZARD-SPECIFIC BUILDERS
# =========================================================
def build_source_turbidity_risk(predicted_turbidity: float, threshold: float, yopi_sensitive: bool) -> Dict[str, Any]:
    deviation_ratio = 0.0 if threshold == 0 else max((predicted_turbidity - threshold) / threshold, 0.0)

    if predicted_turbidity <= threshold:
        l_score, s_score, c_score = 2, 2, 2
        l_class, s_class, c_class = "Moderate", "Moderate", "Low"
        operator_message = "Early change signal detected in source water; continue preventive monitoring."
    elif predicted_turbidity <= threshold * 1.4:
        l_score, s_score, c_score = 3, 3, 2
        l_class, s_class, c_class = "Moderate", "Moderate", "Low"
        operator_message = "Elevated inlet turbidity may propagate downstream; review coagulation readiness."
    else:
        l_score, s_score, c_score = 4, 4, 3
        l_class, s_class, c_class = "High", "High", "Moderate"
        operator_message = "High source turbidity may challenge barrier performance from intake through treatment."

    return build_risk_response(
        hazard_id="high_turbidity_source",
        hazard_description=(
            "High concentrations of turbidity, particulate matter, suspended solids, or algae at intake."
        ),
        module=MODULE_SOURCE,
        sensor=SOSE_9_NAME,
        parameter="turbidity",
        prediction=predicted_turbidity,
        threshold=threshold,
        monitoring_sensors=["Turbidity", "Chlorophyll A", "Raw water intake quality"],
        likelihood=likelihood_block(
            l_class,
            l_score,
            "Likelihood reflects the probability that changing source-water conditions will stress downstream treatment barriers.",
        ),
        severity=severity_block(
            s_class,
            s_score,
            deviation_ratio,
            "Severity reflects how far the expected inlet condition deviates from the operational threshold.",
        ),
        consequence=consequence_block(
            c_class,
            c_score,
            base_class="Low",
        ),
        short_term_actions=[
            "Increase intake and raw-water quality monitoring frequency.",
            "Alert treatment operators to possible increased coagulant demand.",
            "Check whether downstream coagulation settings remain appropriate.",
        ],
        long_term_actions=[
            "Strengthen source-water event forecasting and intake early-warning integration.",
            "Link source risk automatically to treatment setpoint review logic.",
            "Refine source-to-treatment intervention pathways for seasonal or weather-driven events.",
        ],
        operator_message=operator_message,
        reviewer_summary=(
            "This source risk view translates SoSe #9 into an upstream early-warning signal "
            "that can cascade into treatment and distribution planning."
        ),
        yopi_sensitive=yopi_sensitive,
    )


def build_coagulation_risk(prediction: float, yopi_sensitive: bool) -> Dict[str, Any]:
    # threshold logic aligned with your earlier UI / risk discussion
    threshold = 6.0
    deviation_ratio = max((prediction - threshold) / threshold, 0.0)

    if prediction <= 4.0:
        hazard_id = "stable_coagulation"
        hazard_description = "Coagulation output remains within acceptable operational range."
        l_class, l_score = "Low", 1
        s_class, s_score = "Low", 1
        c_class, c_score = "Low", 1
        operator_message = "Coagulation appears stable; maintain monitoring and dosage verification."
    elif prediction <= 6.0:
        hazard_id = "borderline_coagulation_performance"
        hazard_description = "Borderline removal of particulate material and organic matter after coagulation."
        l_class, l_score = "Moderate", 3
        s_class, s_score = "Moderate", 3
        c_class, c_score = "Moderate", 3
        operator_message = "Coagulation is approaching the limit; review FeCl3 dosage and flocculation conditions."
    else:
        hazard_id = "insufficient_coagulation"
        hazard_description = "Insufficient removal of contaminants such as particulate material and organic matter."
        l_class, l_score = "High", 4
        s_class, s_score = "Moderate", 3
        c_class, c_score = "Moderate", 3
        operator_message = "Risk of insufficient coagulation performance; intervene before breakthrough propagates downstream."

    return build_risk_response(
        hazard_id=hazard_id,
        hazard_description=hazard_description,
        module="Treatment - Coagulation",
        sensor=SOSE_8_NAME,
        parameter="predicted_turbidity_after_coagulation",
        prediction=prediction,
        threshold=threshold,
        monitoring_sensors=[
            "Output turbidity after coagulation/flocculation",
            "FeCl3 dosage",
            "pH",
            "Raw water turbidity",
        ],
        likelihood=likelihood_block(
            l_class,
            l_score,
            "Likelihood reflects the expected probability of poor particulate removal under the current coagulation state.",
        ),
        severity=severity_block(
            s_class,
            s_score,
            deviation_ratio,
            "Severity reflects how far the expected coagulation outcome deviates from the operational turbidity target.",
        ),
        consequence=consequence_block(
            c_class,
            c_score,
            base_class="Moderate",
        ),
        short_term_actions=[
            "Verify current FeCl3 dosage and compare with recent raw-water conditions.",
            "Check pH and mixing/flocculation conditions.",
            "Increase operator attention on downstream rapid sand filtration performance.",
        ],
        long_term_actions=[
            "Connect SoSe #8 outputs to automated coagulant decision support.",
            "Validate soft-sensor alarms with plant data and operator feedback.",
            "Integrate coagulation risk with source-event forecasting.",
        ],
        operator_message=operator_message,
        reviewer_summary=(
            "This endpoint translates SoSe #8 into a treatment risk statement linked to barrier performance and corrective action."
        ),
        yopi_sensitive=yopi_sensitive,
    )


def build_rl_dosage_risk(data: RLDosageRiskInput, yopi_sensitive: bool) -> Dict[str, Any]:
    current_dose = data.current_fecl3_dose
    recommended_dose = data.recommended_fecl3_dose
    confidence = data.confidence
    dose_gap = abs(recommended_dose - current_dose)
    dose_gap_ratio = 0.0 if current_dose == 0 else dose_gap / current_dose

    if confidence < 0.5:
        l_class, l_score = "Moderate", 3
        s_class, s_score = "Moderate", 3
        c_class, c_score = "Low", 2
        msg = "RL recommendation requires careful operator validation due to limited confidence."
    elif dose_gap_ratio < 0.10:
        l_class, l_score = "Low", 1
        s_class, s_score = "Low", 1
        c_class, c_score = "Low", 1
        msg = "RL recommendation is close to current practice; low operational disruption expected."
    elif dose_gap_ratio < 0.25:
        l_class, l_score = "Moderate", 3
        s_class, s_score = "Moderate", 3
        c_class, c_score = "Moderate", 3
        msg = "RL recommendation suggests a meaningful dosing adjustment; operator review is recommended."
    else:
        l_class, l_score = "High", 4
        s_class, s_score = "Moderate", 3
        c_class, c_score = "Moderate", 3
        msg = "RL recommendation deviates strongly from current dosage; confirm plant conditions before implementation."

    return build_risk_response(
        hazard_id="dosage_mismatch_or_unverified_optimization",
        hazard_description=(
            "Potential mismatch between current FeCl3 dosage and the dosage recommended by the RL optimization layer."
        ),
        module="Treatment - Coagulation",
        sensor=RL_4_NAME,
        parameter="recommended_fecl3_dose",
        prediction=recommended_dose,
        threshold=current_dose,
        monitoring_sensors=[
            "Current FeCl3 dose",
            "Recommended FeCl3 dose",
            "Output turbidity",
            "Model confidence / applicability domain",
        ],
        likelihood=likelihood_block(
            l_class,
            l_score,
            "Likelihood reflects the probability that acting on the recommendation without review may create operational instability.",
        ),
        severity=severity_block(
            s_class,
            s_score,
            dose_gap_ratio,
            "Severity reflects the relative deviation between current and recommended coagulant dosage.",
        ),
        consequence=consequence_block(
            c_class,
            c_score,
            base_class="Low",
        ),
        short_term_actions=[
            "Compare recommended dosage with current raw-water conditions.",
            "Review operator acceptance before large dose changes are applied.",
            "Validate the recommendation against turbidity and downstream filter behaviour.",
        ],
        long_term_actions=[
            "Define confidence thresholds for automatic vs operator-reviewed RL suggestions.",
            "Link RL recommendations to historical plant performance benchmarking.",
            "Add explainability features for dosing recommendations in the UI.",
        ],
        operator_message=msg,
        reviewer_summary=(
            "RL #4 is treated as a decision-support layer whose risk depends on recommendation confidence and dosage deviation."
        ),
        yopi_sensitive=yopi_sensitive,
        extra={
            "current_fecl3_dose": current_dose,
            "dose_gap": round(dose_gap, 3),
            "dose_gap_ratio": round(dose_gap_ratio, 3),
            "confidence": confidence,
        },
    )


def build_ct_risk(prediction: float, yopi_sensitive: bool) -> Dict[str, Any]:
    threshold = 0.70
    deviation_ratio = 0.0 if threshold == 0 else max((threshold - prediction) / threshold, 0.0)

    if prediction >= 0.70:
        l_class, l_score = "Low", 1
        s_class, s_score = "Low", 1
        c_class, c_score = "Low", 1
        hazard_id = "sufficient_ozonation_exposure"
        hazard_description = "CT indicates sufficient ozonation exposure for disinfection support."
        msg = "CT appears acceptable; continue monitoring the balance between disinfection and DBP control."
    elif prediction >= 0.30:
        l_class, l_score = "Moderate", 3
        s_class, s_score = "Moderate", 3
        c_class, c_score = "Moderate", 3
        hazard_id = "borderline_ozonation_exposure"
        hazard_description = "CT is borderline and may weaken disinfection robustness."
        msg = "CT is approaching an insufficient zone; review contact time and dosage conditions."
    else:
        l_class, l_score = "High", 4
        s_class, s_score = "High", 4
        c_class, c_score = "Major", 4
        hazard_id = "insufficient_ozonation"
        hazard_description = "Insufficient ozonation may compromise disinfection of source water."
        msg = "CT is too low; prioritize disinfection security and investigate process constraints."

    return build_risk_response(
        hazard_id=hazard_id,
        hazard_description=hazard_description,
        module="Treatment - Ozonation",
        sensor=SOSE_10_NAME,
        parameter="CT",
        prediction=prediction,
        threshold=threshold,
        monitoring_sensors=["CT", "Ozone dosage", "Flow rate", "Water temperature"],
        likelihood=likelihood_block(
            l_class,
            l_score,
            "Likelihood reflects the expected probability that current CT conditions are insufficient for robust disinfection support.",
        ),
        severity=severity_block(
            "High" if s_score >= 4 else s_class,
            s_score,
            deviation_ratio,
            "Severity reflects how far the predicted CT falls below the desired disinfection-support threshold.",
        ),
        consequence=consequence_block(
            "High" if c_score >= 4 else c_class,
            c_score,
            base_class="Moderate",
        ),
        short_term_actions=[
            "Review ozone dosage, hydraulic residence time, and chamber conditions.",
            "Check whether changes in flow or turbidity reduced effective contact time.",
            "Cross-check the CT signal with bromate and coliform-related outputs.",
        ],
        long_term_actions=[
            "Improve joint optimization of CT, bromate, and microbial risk.",
            "Calibrate CT alarm thresholds with plant and validation data.",
            "Integrate CT risk directly into source-to-tap intervention pathways.",
        ],
        operator_message=msg,
        reviewer_summary=(
            "SoSe #10 is translated into a disinfection-reliability risk signal rather than just a raw prediction."
        ),
        yopi_sensitive=yopi_sensitive,
    )


def build_bromate_risk(prediction: float, yopi_sensitive: bool) -> Dict[str, Any]:
    threshold = 8.0
    deviation_ratio = 0.0 if threshold == 0 else max((prediction - threshold) / threshold, 0.0)

    if prediction <= 3.0:
        l_class, l_score = "Low", 1
        s_class, s_score = "Low", 1
        c_class, c_score = "Low", 1
        hazard_id = "controlled_bromate_formation"
        hazard_description = "Bromate formation is within a comfortable operating zone."
        msg = "Bromate appears controlled; continue balancing disinfection and DBP minimization."
    elif prediction <= 8.0:
        l_class, l_score = "Moderate", 3
        s_class, s_score = "Moderate", 3
        c_class, c_score = "Moderate", 3
        hazard_id = "elevated_bromate_formation"
        hazard_description = "Bromate formation is elevated and approaching the risk threshold."
        msg = "Bromate risk is increasing; review ozone dose, contact time, and upstream organic load."
    else:
        l_class, l_score = "High", 4
        s_class, s_score = "Moderate", 3
        c_class, c_score = "Moderate", 3
        hazard_id = "excessive_ozonation"
        hazard_description = "Excessive ozonation may promote bromate formation and unnecessary cost."
        msg = "Bromate risk is too high; reduce DBP pressure while maintaining disinfection coverage."

    return build_risk_response(
        hazard_id=hazard_id,
        hazard_description=hazard_description,
        module="Treatment - Ozonation",
        sensor=SOSE_101_NAME,
        parameter="bromate",
        prediction=prediction,
        threshold=threshold,
        monitoring_sensors=["Bromate", "Ozone dosage", "CT", "Raw water quality"],
        likelihood=likelihood_block(
            l_class,
            l_score,
            "Likelihood reflects the probability that current ozonation conditions promote problematic bromate formation.",
        ),
        severity=severity_block(
            s_class,
            s_score,
            deviation_ratio,
            "Severity reflects how far the predicted bromate outcome approaches or exceeds the target threshold.",
        ),
        consequence=consequence_block(
            c_class,
            c_score,
            base_class="Moderate",
        ),
        short_term_actions=[
            "Review ozone dosage and chamber operating conditions.",
            "Check whether CT targets are being achieved with unnecessary DBP stress.",
            "Increase bromate attention when raw-water quality changes suddenly.",
        ],
        long_term_actions=[
            "Strengthen integrated CT–bromate operating envelopes.",
            "Use bromate risk outputs in multi-objective control design.",
            "Refine decision-support logic for disinfection vs by-product trade-offs.",
        ],
        operator_message=msg,
        reviewer_summary=(
            "SoSe #10.1 makes the DBP side of ozonation explicit and supports risk-based trade-off decisions."
        ),
        yopi_sensitive=yopi_sensitive,
    )


def build_coliform_risk(prediction: float, yopi_sensitive: bool) -> Dict[str, Any]:
    threshold = 1.5
    deviation_ratio = 0.0 if threshold == 0 else max((threshold - prediction) / threshold, 0.0)

    # Higher prediction = better removal in your old interpretation
    if prediction >= 2.5:
        l_class, l_score = "Low", 1
        s_class, s_score = "Low", 1
        c_class, c_score = "Low", 1
        hazard_id = "strong_microbial_removal"
        hazard_description = "Predicted microbial removal efficiency is strong."
        msg = "Coliform removal appears robust under the current ozonation conditions."
    elif prediction >= 1.5:
        l_class, l_score = "Moderate", 3
        s_class, s_score = "Moderate", 3
        c_class, c_score = "Moderate", 3
        hazard_id = "borderline_microbial_removal"
        hazard_description = "Predicted microbial removal is borderline and should be reviewed."
        msg = "Coliform removal is not critical yet, but the microbial barrier should be watched closely."
    else:
        l_class, l_score = "High", 4
        s_class, s_score = "High", 4
        c_class, c_score = "High", 4
        hazard_id = "insufficient_microbial_removal"
        hazard_description = "Predicted microbial removal efficiency is insufficient."
        msg = "Microbial protection may be weakened; prioritize barrier reliability and verification."

    return build_risk_response(
        hazard_id=hazard_id,
        hazard_description=hazard_description,
        module="Treatment - Ozonation",
        sensor=SOSE_102_NAME,
        parameter="coliform_removal",
        prediction=prediction,
        threshold=threshold,
        monitoring_sensors=["Coliform removal proxy", "CT", "Ozone dosage", "Flow rate"],
        likelihood=likelihood_block(
            l_class,
            l_score,
            "Likelihood reflects the expected probability that current ozonation conditions do not provide adequate microbial removal robustness.",
        ),
        severity=severity_block(
            s_class,
            s_score,
            deviation_ratio,
            "Severity reflects the distance from the desired microbial-removal performance level.",
        ),
        consequence=consequence_block(
            c_class,
            c_score,
            base_class="Moderate",
        ),
        short_term_actions=[
            "Verify current ozone exposure conditions and CT support.",
            "Review any simultaneous signs of low CT or source-water deterioration.",
            "Increase operator awareness when microbial safety margins narrow.",
        ],
        long_term_actions=[
            "Integrate microbial-risk outputs more explicitly with disinfection control logic.",
            "Validate the coliform model with plant and monitoring data.",
            "Use model outputs to support risk-based alarm tuning for microbial protection.",
        ],
        operator_message=msg,
        reviewer_summary=(
            "SoSe #10.2 supports the microbiological side of ozonation risk and complements CT-based interpretation."
        ),
        yopi_sensitive=yopi_sensitive,
    )


def build_aeromonas_risk(data: DistributionRiskInput) -> Dict[str, Any]:
    p = data.aeromonas_probability
    score_boost = 0
    active_drivers = []

    if data.residual_disinfectant_low:
        score_boost += 1
        active_drivers.append("low residual disinfectant")
    if data.warm_water_condition:
        score_boost += 1
        active_drivers.append("warm water condition")
    if data.stagnation_risk:
        score_boost += 1
        active_drivers.append("stagnation risk")

    if p < 0.20:
        base_l_score, base_s_score, base_c_score = 1, 2, 2
        base_l_class, base_s_class, base_c_class = "Low", "Moderate", "Low"
        msg = "Aeromonas risk appears low, but biological instability should still be monitored."
    elif p < 0.50:
        base_l_score, base_s_score, base_c_score = 3, 3, 3
        base_l_class, base_s_class, base_c_class = "Moderate", "Moderate", "Moderate"
        msg = "Aeromonas signal suggests possible biological instability in the distribution system."
    else:
        base_l_score, base_s_score, base_c_score = 4, 3, 3
        base_l_class, base_s_class, base_c_class = "High", "Moderate", "Moderate"
        msg = "Aeromonas-related risk is elevated; distribution conditions should be reviewed."

    l_score = min(base_l_score + score_boost, 4)
    s_score = min(base_s_score + (1 if data.yopi_sensitive else 0), 4)
    c_score = base_c_score + (1 if (data.yopi_sensitive and p >= 0.5) else 0)
    c_score = min(c_score, 4)

    l_class = level_from_score(l_score)
    s_class = level_from_score(s_score)
    c_class = level_from_score(c_score)

    return build_risk_response(
        hazard_id="distribution_biological_instability",
        hazard_description=(
            "Potential Aeromonas occurrence and biological instability in the distribution system, "
            "which may indicate regrowth-favouring conditions in treated drinking water."
        ),
        module=MODULE_DISTRIBUTION,
        sensor=SOSE_11_NAME,
        parameter="aeromonas_probability",
        prediction=p,
        threshold=0.50,
        monitoring_sensors=[
            "Aeromonas model output",
            "Residual disinfectant",
            "Temperature",
            "Residence time / stagnation indicators",
        ],
        likelihood=likelihood_block(
            l_class,
            l_score,
            "Likelihood reflects the probability that distribution conditions favour Aeromonas occurrence or broader biological instability.",
        ),
        severity=severity_block(
            s_class,
            s_score,
            p,
            "Severity reflects the strength of the Aeromonas signal and the importance of potentially favourable regrowth conditions.",
        ),
        consequence=consequence_block(
            c_class,
            c_score,
            base_class="Moderate",
        ),
        short_term_actions=[
            "Review low residual disinfectant zones and hydraulic weak points.",
            "Check whether warm water, stagnation, or residence time issues are present.",
            "Increase targeted distribution monitoring where biological instability is suspected.",
        ],
        long_term_actions=[
            "Improve distribution-system risk mapping for microbial regrowth vulnerability.",
            "Link Aeromonas predictions with network hydraulics and temperature information.",
            "Refine biological stability monitoring as SoSe #11 evolves.",
        ],
        operator_message=msg,
        reviewer_summary=(
            "SoSe #11 is treated as a distribution biological-instability signal, even while the model remains under evaluation."
        ),
        yopi_sensitive=data.yopi_sensitive,
        extra={
            "active_distribution_drivers": active_drivers,
            "model_status": "Under evaluation / subject to change",
        },
    )


# =========================================================
# OVERVIEW
# =========================================================
@router.get("/overview", summary="Risk module overview")
def risk_overview():
    return {
        "module": MODULE_RISK,
        "description": (
            "Transforms hard-sensor and soft-sensor signals into source-to-tap risk "
            "statements including likelihood, severity, consequence, overall risk, "
            "and mitigation actions."
        ),
        "available_risk_functions": [
            "/risk/source/sose-9/current",
            "/risk/coagulation",
            "/risk/treatment/rl-4/current",
            "/risk/ct",
            "/risk/bromate",
            "/risk/coliform",
            "/risk/ozonation/current",
            "/risk/distribution/sose-11/current",
            "/risk/treatment/current",
            "/risk/system/current",
        ],
        "reviewer_highlights": [
            "Hazard-to-risk translation",
            "Short-term and long-term mitigation guidance",
            "Combined ozonation risk",
            "Whole treatment risk",
            "Whole source-to-tap risk",
            "Graph-ready and decision-tree-ready output",
        ],
        "sensors_and_models_in_platform": [
            {"name": SOSE_9_NAME, "module": MODULE_SOURCE, "type": "Soft sensor", "status": "Implemented"},
            {"name": SOSE_8_NAME, "module": "Treatment - Coagulation", "type": "Soft sensor", "status": "Implemented"},
            {"name": RL_4_NAME, "module": "Treatment - Coagulation", "type": "Soft sensor", "status": "Implemented"},
            {"name": SOSE_10_NAME, "module": "Treatment - Ozonation", "type": "Soft sensor", "status": "Implemented"},
            {"name": SOSE_101_NAME, "module": "Treatment - Ozonation", "type": "Soft sensor", "status": "Implemented"},
            {"name": SOSE_102_NAME, "module": "Treatment - Ozonation", "type": "Soft sensor", "status": "Implemented"},
            {"name": SOSE_11_NAME, "module": MODULE_DISTRIBUTION, "type": "Soft sensor", "status": "Under evaluation / subject to change"},
            {"name": BACTOSENSE_4_NAME, "module": MODULE_TREATMENT, "type": "Hard sensor", "status": "Connected conceptually / placeholder"},
        ],
    }


# =========================================================
# SOURCE RISK
# =========================================================
@router.post("/source/sose-9/current", summary="Current source risk from SoSe #9")
def source_sose_9_risk(data: SourceRiskInput):
    return build_source_turbidity_risk(
        predicted_turbidity=data.predicted_turbidity,
        threshold=data.threshold,
        yopi_sensitive=data.yopi_sensitive,
    )


# =========================================================
# COAGULATION RISK
# =========================================================
@router.post("/coagulation", summary="Coagulation risk assessment")
def coagulation_risk(body: CoagulationInput, yopi_sensitive: bool = True):
    try:
        prediction = to_float(run_coagulation_prediction(body))
        return build_coagulation_risk(prediction, yopi_sensitive)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Coagulation risk assessment failed: {str(e)}")


# =========================================================
# RL #4 RISK
# =========================================================
@router.post("/treatment/rl-4/current", summary="RL #4 dosage recommendation risk")
def rl4_risk(data: RLDosageRiskInput, yopi_sensitive: bool = True):
    return build_rl_dosage_risk(data, yopi_sensitive)


# =========================================================
# CT RISK
# =========================================================
@router.post("/ct", summary="CT risk assessment")
def ct_risk(data: CTInput, yopi_sensitive: bool = True):
    try:
        pred = to_float(predict_ct([[
            data.Chamber,
            data.WaterTemperature,
            data.RFTurbidity,
            data.FlowRate,
            data.Ozonedosage,
        ]]))
        return build_ct_risk(pred, yopi_sensitive)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CT risk assessment failed: {str(e)}")


# =========================================================
# BROMATE RISK
# =========================================================
@router.post("/bromate", summary="Bromate risk assessment")
def bromate_risk(data: BromateInput, yopi_sensitive: bool = True):
    try:
        pred = to_float(predict_bromate([[
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
        ]]))
        return build_bromate_risk(pred, yopi_sensitive)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bromate risk assessment failed: {str(e)}")


# =========================================================
# COLIFORM RISK
# =========================================================
@router.post("/coliform", summary="Coliform-removal risk assessment")
def coliform_risk(data: ColiformInput, yopi_sensitive: bool = True):
    try:
        pred = to_float(predict_coliform([[
            data.Chamber,
            data.WaterTemperature,
            data.RFTurbidity,
            data.FlowRate,
            data.Ozonedosage,
            data.RFturbidity_1,
            data.CT_All,
        ]]))
        return build_coliform_risk(pred, yopi_sensitive)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Coliform risk assessment failed: {str(e)}")


# =========================================================
# DISTRIBUTION RISK
# =========================================================
@router.post("/distribution/sose-11/current", summary="Current distribution risk from SoSe #11")
def distribution_sose_11_risk(data: DistributionRiskInput):
    return build_aeromonas_risk(data)


# =========================================================
# COMBINED OZONATION RISK
# =========================================================
@router.post("/ozonation/current", summary="Combined ozonation risk")
def ozonation_risk(data: OzonationRiskInput):
    try:
        ct_pred = to_float(predict_ct([[
            data.ct.Chamber,
            data.ct.WaterTemperature,
            data.ct.RFTurbidity,
            data.ct.FlowRate,
            data.ct.Ozonedosage,
        ]]))

        br_pred = to_float(predict_bromate([[
            data.bromate.month,
            data.bromate.Chamber,
            data.bromate.WaterTemperature,
            data.bromate.RFTurbidity,
            data.bromate.FlowRate,
            data.bromate.Ozonedosage,
            data.bromate.Residencetime,
            data.bromate.WaterTemperature_1,
            data.bromate.RFturbidity_1,
            data.bromate.FlowRate_1,
            data.bromate.Ozonedosage_1,
            data.bromate.CT_All,
        ]]))

        col_pred = to_float(predict_coliform([[
            data.coliform.Chamber,
            data.coliform.WaterTemperature,
            data.coliform.RFTurbidity,
            data.coliform.FlowRate,
            data.coliform.Ozonedosage,
            data.coliform.RFturbidity_1,
            data.coliform.CT_All,
        ]]))

        ct_r = build_ct_risk(ct_pred, data.yopi_sensitive)
        br_r = build_bromate_risk(br_pred, data.yopi_sensitive)
        col_r = build_coliform_risk(col_pred, data.yopi_sensitive)

        overall = overall_risk_block(
            max(ct_r["likelihood"]["score"], br_r["likelihood"]["score"], col_r["likelihood"]["score"]),
            max(ct_r["severity"]["score"], br_r["severity"]["score"], col_r["severity"]["score"]),
            max(ct_r["consequence"]["score"], br_r["consequence"]["score"], col_r["consequence"]["score"]),
        )

        if overall["class"] == "High":
            action = "Prioritize ozonation review immediately and balance microbial protection against DBP formation."
        elif overall["class"] == "Moderate":
            action = "Review ozonation trade-offs and maintain tighter operator attention."
        else:
            action = "Maintain current ozonation monitoring and continue trend-based supervision."

        return {
            "module": MODULE_RISK,
            "submodule": "Treatment - Ozonation",
            "overall_risk": overall,
            "recommended_action": action,
            "source_to_tap_relevance": (
                "Ozonation risk affects both microbial protection and by-product control, "
                "making it a key barrier in source-to-tap decision support."
            ),
            "components": {
                "ct": ct_r,
                "bromate": br_r,
                "coliform": col_r,
            },
            "graph_payload": {
                "nodes": [
                    {"id": "ct", "label": "SoSe #10", "group": "sensor"},
                    {"id": "br", "label": "SoSe #10.1", "group": "sensor"},
                    {"id": "col", "label": "SoSe #10.2", "group": "sensor"},
                    {"id": "oz_hazard", "label": "Ozonation trade-off", "group": "hazard"},
                    {"id": "oz_risk", "label": overall["class"], "group": "risk"},
                ],
                "edges": [
                    {"source": "ct", "target": "oz_hazard"},
                    {"source": "br", "target": "oz_hazard"},
                    {"source": "col", "target": "oz_hazard"},
                    {"source": "oz_hazard", "target": "oz_risk"},
                ],
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Combined ozonation risk failed: {str(e)}")


# =========================================================
# TREATMENT CURRENT RISK
# =========================================================
@router.post("/treatment/current", summary="Current treatment risk")
def treatment_current_risk(data: TreatmentRiskInput):
    try:
        coag_pred = to_float(run_coagulation_prediction(data.coagulation))
        coag_r = build_coagulation_risk(coag_pred, data.yopi_sensitive)

        oz_r = ozonation_risk(data.ozonation)

        rl_r = None
        if data.rl is not None:
            rl_r = build_rl_dosage_risk(data.rl, data.yopi_sensitive)

        severity_scores = [coag_r["severity"]["score"], oz_r["overall_risk"]["score"]]
        likelihood_scores = [coag_r["likelihood"]["score"], int(round(oz_r["overall_risk"]["score"]))]
        consequence_scores = [coag_r["consequence"]["score"], int(round(oz_r["overall_risk"]["score"]))]

        if rl_r:
            severity_scores.append(rl_r["severity"]["score"])
            likelihood_scores.append(rl_r["likelihood"]["score"])
            consequence_scores.append(rl_r["consequence"]["score"])

        treatment_overall = overall_risk_block(
            max(likelihood_scores),
            max(severity_scores),
            max(consequence_scores),
        )

        if treatment_overall["class"] == "High":
            treatment_action = "Treatment barriers require coordinated review, starting with the dominant high-risk process."
        elif treatment_overall["class"] == "Moderate":
            treatment_action = "Treatment is under manageable stress; increase cross-process awareness and verify settings."
        else:
            treatment_action = "Treatment appears stable; continue routine barrier monitoring."

        return {
            "module": MODULE_RISK,
            "submodule": MODULE_TREATMENT,
            "overall_risk": treatment_overall,
            "recommended_action": treatment_action,
            "dominant_focus": (
                "coagulation"
                if coag_r["overall_risk"]["score"] >= oz_r["overall_risk"]["score"]
                else "ozonation"
            ),
            "components": {
                "coagulation": coag_r,
                "rl_optimization": rl_r,
                "ozonation": oz_r,
            },
            "reviewer_summary": (
                "This treatment endpoint aggregates barrier-level risks across coagulation and ozonation "
                "instead of reporting isolated model outputs."
            ),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Treatment current risk failed: {str(e)}")


# =========================================================
# SYSTEM CURRENT RISK
# =========================================================
@router.post("/system/current", summary="Current source-to-tap system-wide risk")
def system_current_risk(data: SystemRiskInput):
    try:
        source_r = build_source_turbidity_risk(
            predicted_turbidity=data.source.predicted_turbidity,
            threshold=data.source.threshold,
            yopi_sensitive=data.source.yopi_sensitive,
        )

        treatment_r = treatment_current_risk(data.treatment)

        distribution_r = build_aeromonas_risk(data.distribution)

        source_score = source_r["overall_risk"]["score"]
        treatment_score = treatment_r["overall_risk"]["score"]
        distribution_score = distribution_r["overall_risk"]["score"]

        barrier_scores = {
            "source": source_score,
            "treatment": treatment_score,
            "distribution": distribution_score,
        }

        dominant_module = max(barrier_scores, key=barrier_scores.get)
        dominant_score = barrier_scores[dominant_module]

        if dominant_score == source_score:
            dominant_hazard = source_r["hazard_description"]
        elif dominant_score == treatment_score:
            dominant_hazard = "Treatment barrier stress driven by coagulation and/or ozonation conditions."
        else:
            dominant_hazard = distribution_r["hazard_description"]

        system_overall = overall_risk_block(
            max(
                source_r["likelihood"]["score"],
                treatment_r["overall_risk"]["score"],
                distribution_r["likelihood"]["score"],
            ),
            max(
                source_r["severity"]["score"],
                int(round(treatment_r["overall_risk"]["score"])),
                distribution_r["severity"]["score"],
            ),
            max(
                source_r["consequence"]["score"],
                int(round(treatment_r["overall_risk"]["score"])),
                distribution_r["consequence"]["score"],
            ),
        )

        if system_overall["class"] == "High":
            operator_message = (
                "High source-to-tap risk detected. Prioritize the dominant module immediately and verify barrier continuity."
            )
        elif system_overall["class"] == "Moderate":
            operator_message = (
                "Moderate source-to-tap risk detected. Strengthen coordination between source, treatment, and distribution monitoring."
            )
        else:
            operator_message = (
                "Source-to-tap risk currently appears low. Continue preventive surveillance and trend analysis."
            )

        short_term_actions = [
            "Review the dominant module first.",
            "Check whether upstream conditions are cascading into downstream barriers.",
            "Increase monitoring frequency where barrier stress is highest.",
        ]
        long_term_actions = [
            "Implement a fully connected source-to-tap intervention pathway module.",
            "Use risk outputs to support integrated operator dashboards and alarm logic.",
            "Calibrate thresholds with plant data, expert feedback, and utility-specific practices.",
        ]

        return {
            "module": MODULE_RISK,
            "submodule": MODULE_SYSTEM,
            "scope": "Source-to-tap",
            "overall_risk": system_overall,
            "dominant_module": dominant_module,
            "dominant_hazard": dominant_hazard,
            "barrier_status": {
                "source": source_r["overall_risk"]["class"],
                "treatment": treatment_r["overall_risk"]["class"],
                "distribution": distribution_r["overall_risk"]["class"],
            },
            "operator_message": operator_message,
            "short_term_actions": short_term_actions,
            "long_term_actions": long_term_actions,
            "reviewer_summary": (
                "This system-wide endpoint integrates Source, Treatment, and Distribution signals into "
                "a single operational source-to-tap risk view."
            ),
            "components": {
                "source": source_r,
                "treatment": treatment_r,
                "distribution": distribution_r,
            },
            "graph_payload": {
                "nodes": [
                    {"id": "source", "label": "Source / Intake", "group": "module"},
                    {"id": "treatment", "label": "Treatment", "group": "module"},
                    {"id": "distribution", "label": "Distribution", "group": "module"},
                    {"id": "system_risk", "label": system_overall["class"], "group": "risk"},
                ],
                "edges": [
                    {"source": "source", "target": "treatment", "label": "cascading influence"},
                    {"source": "treatment", "target": "distribution", "label": "barrier continuity"},
                    {"source": "source", "target": "system_risk"},
                    {"source": "treatment", "target": "system_risk"},
                    {"source": "distribution", "target": "system_risk"},
                ],
                "decision_tree": {
                    "root_question": "Is the source-to-tap system within acceptable risk bounds?",
                    "if_no": {
                        "first_priority": dominant_module,
                        "dominant_hazard": dominant_hazard,
                        "short_term_actions": short_term_actions,
                        "long_term_actions": long_term_actions,
                    },
                    "if_yes": {
                        "message": "Continue routine integrated monitoring and preventive control."
                    },
                },
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System current risk failed: {str(e)}")


# =========================================================
# OPTIONAL GET PLACEHOLDER FOR UI COMPATIBILITY
# =========================================================
@router.get("/system/current", summary="Current system-wide risk placeholder")
def system_current_risk_placeholder():
    return {
        "module": MODULE_RISK,
        "submodule": MODULE_SYSTEM,
        "scope": "Source-to-tap",
        "note": (
            "Use POST /risk/system/current with Source, Treatment, and Distribution inputs "
            "to calculate the full dynamic system-wide risk."
        ),
        "status": "ready_for_connected_inputs",
    }