from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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
    threshold: float
    yopi_sensitive: bool = False


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


class DistributionRiskInput(BaseModel):
    aeromonas_probability: float
    residual_disinfectant_low: bool = False
    warm_water_condition: bool = False
    stagnation_risk: bool = False
    yopi_sensitive: bool = False


class TreatmentRiskInput(BaseModel):
    coagulation: CoagulationInput
    rl: RLRiskInput
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
RL_5_NAME = "RL #5 - RL Optimal FeCl3 dosage for coagulation process"
SOSE_10_NAME = "SoSe #10 - Prediction of the ozonation exposure, CT, to improve the ozonation process"
SOSE_101_NAME = "SoSe #10.1 - Bromate formation model"
SOSE_102_NAME = "SoSe #10.2 - Coliform removal model"
SOSE_11_NAME = "SoSe #11 - Aeromonas prediction model"
BACTOSENSE_4_NAME = "BactoSense #4"

# Thresholds currently used in the risk logic
SOURCE_TURBIDITY_THRESHOLD = 5.0
COAGULATION_TURBIDITY_THRESHOLD = 5.0
CT_THRESHOLD = 0.7
BROMATE_THRESHOLD = 8.0
COLIFORM_THRESHOLD = 2.5
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
def classify_source_risk(predicted_turbidity: float, threshold: float, yopi_sensitive: bool):
    ratio = predicted_turbidity / threshold if threshold > 0 else 0.0

    if ratio <= 1.0:
        likelihood_score = 2
    elif ratio <= 1.2:
        likelihood_score = 3
    else:
        likelihood_score = 5

    if ratio <= 1.0:
        severity_score = 2
    elif ratio <= 1.3:
        severity_score = 3
    else:
        severity_score = 4

    if yopi_sensitive:
        severity_score += 1

    severity_score = clamp_score(severity_score)
    consequence_score = max(likelihood_score, severity_score)
    overall = overall_from_scores(likelihood_score, severity_score, consequence_score)

    return build_response(
        submodule="Source / Intake",
        sensor="SoSe #9",
        sensor_or_model=SOSE_9_NAME,
        hazard_id="high_turbidity_source",
        hazard_description="Elevated turbidity at the intake may increase treatment stress and reduce operational robustness.",
        prediction=predicted_turbidity,
        threshold=threshold,
        likelihood=make_band(
            likelihood_score,
            {"probability_proxy": round(min(max(ratio - 1.0, 0.0), 1.0), 3)},
        ),
        severity=make_band(
            severity_score,
            {"deviation_ratio": round(ratio, 3)},
        ),
        consequence=make_band(consequence_score),
        overall_risk=overall,
        recommended_action=action_from_class(overall["class"]),
        yopi_sensitive=yopi_sensitive,
        short_term_actions=[
            "Increase intake-quality monitoring frequency.",
            "Review raw-water abstraction strategy.",
            "Alert treatment operators for possible upstream deterioration.",
        ],
        long_term_actions=[
            "Refine source-side alarm thresholds.",
            "Integrate upstream catchment indicators into the risk logic.",
        ],
        operator_message="Review intake conditions and prepare treatment-side mitigation if turbidity remains elevated.",
        graph_payload={"ratio_to_threshold": round(ratio, 3)},
    )


def classify_coagulation_risk(prediction: float):
    if prediction <= 2:
        likelihood_score = 2
    elif prediction <= COAGULATION_TURBIDITY_THRESHOLD:
        likelihood_score = 3
    else:
        likelihood_score = 5

    if prediction <= 2:
        severity_score = 2
    elif prediction <= 6:
        severity_score = 3
    else:
        severity_score = 4

    consequence_score = max(likelihood_score, severity_score)
    overall = overall_from_scores(likelihood_score, severity_score, consequence_score)

    return build_response(
        submodule="Treatment / Coagulation",
        sensor="SoSe #8",
        sensor_or_model=SOSE_8_NAME,
        hazard_id="high_turbidity_after_coagulation",
        hazard_description="Poor coagulation performance may result in insufficient particle removal and downstream treatment stress.",
        prediction=prediction,
        threshold=COAGULATION_TURBIDITY_THRESHOLD,
        likelihood=make_band(
            likelihood_score,
            {"probability_proxy": round(min(prediction / 10.0, 1.0), 3)},
        ),
        severity=make_band(
            severity_score,
            {"deviation_ratio": round(prediction / COAGULATION_TURBIDITY_THRESHOLD, 3)},
        ),
        consequence=make_band(consequence_score),
        overall_risk=overall,
        recommended_action=action_from_class(overall["class"]),
        short_term_actions=[
            "Review FeCl3 dosing.",
            "Verify raw water pH and temperature conditions.",
            "Inspect coagulation/flocculation performance.",
        ],
        long_term_actions=[
            "Refine coagulation control logic.",
            "Retrain or recalibrate the coagulation model if needed.",
        ],
        operator_message="Investigate coagulation performance if predicted turbidity remains elevated.",
        graph_payload={"predicted_turbidity": prediction},
    )


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
    if prediction <= 3:
        likelihood_score = 2
    elif prediction <= BROMATE_THRESHOLD:
        likelihood_score = 3
    else:
        likelihood_score = 5

    if prediction <= 3:
        severity_score = 2
    elif prediction <= BROMATE_THRESHOLD:
        severity_score = 3
    else:
        severity_score = 5

    consequence_score = max(likelihood_score, severity_score)
    overall = overall_from_scores(likelihood_score, severity_score, consequence_score)

    return build_response(
        submodule="Treatment / Ozonation",
        sensor="SoSe #10.1",
        sensor_or_model=SOSE_101_NAME,
        hazard_id="bromate_formation_risk",
        hazard_description="High bromate formation may threaten compliance and water-quality objectives.",
        prediction=prediction,
        threshold=BROMATE_THRESHOLD,
        likelihood=make_band(
            likelihood_score,
            {"probability_proxy": round(min(prediction / 10.0, 1.0), 3)},
        ),
        severity=make_band(
            severity_score,
            {"deviation_ratio": round(prediction / BROMATE_THRESHOLD, 3)},
        ),
        consequence=make_band(consequence_score),
        overall_risk=overall,
        recommended_action=action_from_class(overall["class"]),
        short_term_actions=[
            "Review ozone dosage and contact conditions.",
            "Verify bromate control constraints.",
        ],
        long_term_actions=[
            "Optimize bromate-aware control logic.",
            "Improve seasonal bromate forecasting.",
        ],
        operator_message="High bromate prediction requires immediate review of ozonation settings.",
        graph_payload={"bromate_prediction": prediction},
    )


def classify_coliform_risk(prediction: float):
    if prediction >= COLIFORM_THRESHOLD:
        likelihood_score = 2
    elif prediction >= 1.5:
        likelihood_score = 3
    else:
        likelihood_score = 5

    if prediction >= COLIFORM_THRESHOLD:
        severity_score = 2
    elif prediction >= 1.5:
        severity_score = 3
    else:
        severity_score = 4

    consequence_score = max(likelihood_score, severity_score)
    overall = overall_from_scores(likelihood_score, severity_score, consequence_score)

    return build_response(
        submodule="Treatment / Ozonation",
        sensor="SoSe #10.2",
        sensor_or_model=SOSE_102_NAME,
        hazard_id="insufficient_coliform_removal",
        hazard_description="Low predicted coliform removal may indicate insufficient microbial risk reduction.",
        prediction=prediction,
        threshold=COLIFORM_THRESHOLD,
        likelihood=make_band(
            likelihood_score,
            {"probability_proxy": round(max(0.0, COLIFORM_THRESHOLD - prediction), 3)},
        ),
        severity=make_band(
            severity_score,
            {"deviation_ratio": round(prediction / COLIFORM_THRESHOLD, 3)},
        ),
        consequence=make_band(consequence_score),
        overall_risk=overall,
        recommended_action=action_from_class(overall["class"]),
        short_term_actions=[
            "Review ozonation disinfection conditions.",
            "Inspect CT assumptions and supporting inputs.",
        ],
        long_term_actions=[
            "Refine microbial removal validation.",
            "Link model outputs to microbial safety margins.",
        ],
        operator_message="Low predicted coliform removal requires review of disinfection robustness.",
        graph_payload={"coliform_prediction": prediction},
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
            "/risk/treatment/rl-5/current",
            "/risk/ct",
            "/risk/bromate",
            "/risk/coliform",
            "/risk/ozonation/current",
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
                "type": "Soft sensor",
                "module": "Treatment - Coagulation",
                "status": "Implemented",
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
    try:
        return classify_rl_risk(
            current_fecl3_dose=data.current_fecl3_dose,
            recommended_fecl3_dose=data.recommended_fecl3_dose,
            output_turbidity=data.output_turbidity,
            confidence=data.confidence,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"RL #5 risk assessment failed: {str(e)}",
        )


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
        rl_component = rl5_risk(data.rl)
        ozonation_component = ozonation_risk(data.ozonation)

        overall = overall_from_scores(
            coag_component["overall_risk"]["score"],
            rl_component["overall_risk"]["score"],
            ozonation_component["overall_risk"]["score"],
        )

        return {
            "module": MODULE_RISK,
            "submodule": "Treatment",
            "overall_risk": overall,
            "recommended_action": action_from_class(overall["class"]),
            "components": {
                "coagulation": coag_component,
                "rl": rl_component,
                "ozonation": ozonation_component,
            },
            "reviewer_summary": "Treatment risk combines coagulation, RL dosage recommendation, and ozonation-related risks.",
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

        overall = overall_from_scores(
            source_component["overall_risk"]["score"],
            treatment_component["overall_risk"]["score"],
            distribution_component["overall_risk"]["score"],
        )

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