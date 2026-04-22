// ==========================================
// ToDrinQ UI - final unified version
// ==========================================

const ENDPOINTS = {
  coagulation: "/predict/coagulation",
  coagulationLive: "/predict/coagulation/live",
  ct: "/predict/ct",
  bromate: "/predict/bromate",
  coliform: "/predict/coliform",

  sourceOverview: "/source/overview",
  sourceLatest: "/source/sose-9/latest",

  treatmentOverview: "/treatment/overview",
  treatmentCoagLatest: "/treatment/coagulation/latest",
  treatmentRLLatest: "/treatment/coagulation/rl/latest",
  treatmentCT: "/treatment/ozonation/ct",
  treatmentBromate: "/treatment/ozonation/bromate",
  treatmentColiform: "/treatment/ozonation/coliform",
  treatmentBactoSense: "/treatment/hard-sensors/bactosense-4/latest",

  distributionOverview: "/distribution/overview",
  distributionLatest: "/distribution/sose-11/latest",

  riskOverview: "/risk/overview",
  riskSourceSose9: "/risk/source/sose-9/current",
  riskCoagulation: "/risk/coagulation",
  riskRL5: "/risk/treatment/rl-5/current",
  riskCT: "/risk/ct",
  riskBromate: "/risk/bromate",
  riskColiform: "/risk/coliform",
  riskOzonation: "/risk/ozonation/current",
  riskDistributionSose11: "/risk/distribution/sose-11/current",
  riskTreatmentCurrent: "/risk/treatment/current",
  riskSystemCurrent: "/risk/system/current"
};

const breadcrumbs = document.getElementById("breadcrumbs");

const screenTitles = {
  "screen-home": "Home",
  "screen-source": "Source Module – SoSe #9",
  "screen-treatment": "Treatment Module",
  "screen-treatment-overview": "Treatment Overview",
  "screen-hard-placeholder": "Hard Sensor Monitoring",
  "screen-soft-select": "Soft Sensor Platform Models",
  "screen-coagulation": "SoSe #8 – Coagulation-Flocculation Turbidity Estimation",
  "screen-rl5": "RL #5 – Optimal FeCl₃ Dosage",
  "screen-ozonation-select": "Ozonation Models",
  "screen-ct": "SoSe #10 – CT Prediction",
  "screen-bromate": "SoSe #10.1 – Bromate Formation",
  "screen-coliform": "SoSe #10.2 – Coliform Removal",
  "screen-ozonation-dashboard": "Ozonation Dashboard",
  "screen-hard-sensors": "BactoSense #4",
  "screen-distribution": "Distribution Module – SoSe #11",
  "screen-risk": "Risk Module",
  "screen-risk-overview": "Risk Overview",
  "screen-risk-source": "SoSe #9 Source Risk",
  "screen-risk-coagulation": "SoSe #8 Coagulation Risk",
  "screen-risk-rl5": "RL #5 Dosage Risk",
  "screen-risk-ozonation": "Combined Ozonation Risk",
  "screen-risk-distribution": "SoSe #11 Distribution Risk",
  "screen-risk-treatment": "Treatment Current Risk",
  "screen-risk-system": "Source-to-Tap System Risk"
};

const state = {
  coagulation: {
    lastInput: null,
    lastPrediction: null,
    lastRisk: null
  },
  rl5: {
    lastInput: null,
    lastRisk: null
  },
  ozonation: {
    ctInput: null,
    ctPrediction: null,
    bromateInput: null,
    bromatePrediction: null,
    coliformInput: null,
    coliformPrediction: null,
    combinedRisk: null
  }
};

function showScreen(id) {
  document.querySelectorAll(".screen").forEach((screen) => {
    screen.classList.remove("active");
  });

  const target = document.getElementById(id);
  if (target) {
    target.classList.add("active");
    updateBreadcrumbs(id);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

function updateBreadcrumbs(id) {
  const label = screenTitles[id] || "Platform";
  breadcrumbs.innerHTML = `
    <button type="button" data-nav="screen-home">Home</button>
    <span>›</span>
    <span>${label}</span>
  `;
}

document.addEventListener("click", (e) => {
  const navEl = e.target.closest("[data-nav]");
  if (navEl) {
    e.preventDefault();
    showScreen(navEl.dataset.nav);
  }
});

updateBreadcrumbs("screen-home");

// ------------------------------
// Helpers
// ------------------------------
function formDataToObject(form) {
  const out = {};
  new FormData(form).forEach((value, key) => {
    if (value === "") {
      out[key] = value;
      return;
    }
    const n = Number(value);
    out[key] = Number.isNaN(n) ? value : n;
  });
  return out;
}

function formDataToNestedObject(form) {
  const out = {};
  new FormData(form).forEach((value, key) => {
    const parts = key.split(".");
    let ref = out;

    for (let i = 0; i < parts.length - 1; i++) {
      if (!ref[parts[i]]) ref[parts[i]] = {};
      ref = ref[parts[i]];
    }

    const n = Number(value);
    ref[parts[parts.length - 1]] = Number.isNaN(n) ? value : n;
  });
  return out;
}

function normalizeBooleanStrings(obj) {
  for (const key of Object.keys(obj)) {
    if (typeof obj[key] === "object" && obj[key] !== null) {
      normalizeBooleanStrings(obj[key]);
    } else if (obj[key] === "true") {
      obj[key] = true;
    } else if (obj[key] === "false") {
      obj[key] = false;
    }
  }
  return obj;
}

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`${r.status} ${text}`);
  }
  return r.json();
}

async function postJSON(url, payload) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!r.ok) {
    const text = await r.text();
    throw new Error(`${r.status} ${text}`);
  }

  return r.json();
}

function renderJSON(id, data) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = JSON.stringify(data, null, 2);
}

function setText(id, value, digits = 2) {
  const el = document.getElementById(id);
  if (!el) return;

  if (value === null || value === undefined || Number.isNaN(value)) {
    el.textContent = "–";
    return;
  }

  if (typeof value === "number") {
    el.textContent = value.toFixed(digits);
  } else {
    el.textContent = value;
  }
}

function setHtml(id, html) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = html;
}

function setValue(id, value) {
  const el = document.getElementById(id);
  if (!el) return;
  el.value = value ?? "";
}

function setBadge(id, text, level = "info") {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.classList.remove("info", "low", "moderate", "high");
  el.classList.add(level);
}

function extractNumber(value) {
  if (Array.isArray(value)) {
    if (!value.length) return null;
    return extractNumber(value[0]);
  }
  if (typeof value === "number") return value;
  if (typeof value === "string") {
    const n = Number(value);
    return Number.isNaN(n) ? null : n;
  }
  return null;
}

function classifyPrediction(value, low, high) {
  if (value === null || value === undefined || Number.isNaN(value)) return "–";
  if (value <= low) return "Low";
  if (value <= high) return "Moderate";
  return "High";
}

function classifyInverse(value, moderateMin, highMin) {
  if (value === null || value === undefined || Number.isNaN(value)) return "–";
  if (value >= highMin) return "High";
  if (value >= moderateMin) return "Moderate";
  return "Low";
}

function levelFromText(text) {
  if (text === "Low") return "low";
  if (text === "Moderate") return "moderate";
  if (text === "High" || text === "Major") return "high";
  return "info";
}

function pickPrediction(data, keys = []) {
  for (const key of keys) {
    if (key in data) {
      const value = extractNumber(data[key]);
      if (value !== null) return value;
    }
  }

  if ("prediction" in data) return extractNumber(data.prediction);
  return null;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function renderList(items) {
  if (!items || !items.length) return "<li>–</li>";
  return items.map(item => `<li>${escapeHtml(item)}</li>`).join("");
}

function riskBadgeClass(level) {
  const text = String(level || "").toLowerCase();
  if (text === "low") return "low";
  if (text === "moderate") return "moderate";
  if (text === "high" || text === "major") return "high";
  return "info";
}

function renderRichRisk(id, data) {
  const el = document.getElementById(id);
  if (!el) return;

  if (!data || data.error) {
    el.innerHTML = `<pre class="json-box">${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
    return;
  }

  const overall = data.overall_risk || {};
  const likelihood = data.likelihood || {};
  const severity = data.severity || {};
  const consequence = data.consequence || {};
  const vulnerable = data.vulnerable_groups || {};

  const componentsHtml = data.components
    ? `<details class="risk-details-block">
         <summary>Show component details</summary>
         <pre class="json-box">${escapeHtml(JSON.stringify(data.components, null, 2))}</pre>
       </details>`
    : "";

  const graphHtml = data.graph_payload
    ? `<details class="risk-details-block">
         <summary>Show graph / decision-tree payload</summary>
         <pre class="json-box">${escapeHtml(JSON.stringify(data.graph_payload, null, 2))}</pre>
       </details>`
    : "";

  el.innerHTML = `
    <div class="risk-rich-card">
      <div class="status-row">
        <span class="badge ${riskBadgeClass(overall.class)}">Overall risk: ${escapeHtml(overall.class || "–")}</span>
        <span class="badge info">Module: ${escapeHtml(data.module || "–")}</span>
        ${data.submodule ? `<span class="badge info">Scope: ${escapeHtml(data.submodule)}</span>` : ""}
      </div>

      <div class="metric-grid">
        <div class="metric">
          <span class="metric-label">Sensor / model</span>
          <strong class="metric-value small">${escapeHtml(data.sensor || data.sensor_or_model || "–")}</strong>
        </div>
        <div class="metric">
          <span class="metric-label">Prediction</span>
          <strong class="metric-value small">${escapeHtml(data.prediction ?? "–")}</strong>
        </div>
        <div class="metric">
          <span class="metric-label">Threshold</span>
          <strong class="metric-value small">${escapeHtml(data.threshold ?? "–")}</strong>
        </div>
      </div>

      ${data.hazard_id ? `<div class="info-box"><strong>Hazard:</strong> ${escapeHtml(data.hazard_id)}<br>${escapeHtml(data.hazard_description || "–")}</div>` : ""}
      ${data.dominant_hazard ? `<div class="info-box"><strong>Dominant hazard:</strong><br>${escapeHtml(data.dominant_hazard)}</div>` : ""}

      <div class="metric-grid">
        <div class="metric">
          <span class="metric-label">Likelihood</span>
          <strong class="metric-value small">${escapeHtml(likelihood.class || "–")}</strong>
          <div class="metric-unit">Score: ${escapeHtml(likelihood.score ?? "–")} | Proxy: ${escapeHtml(likelihood.probability_proxy ?? "–")}</div>
        </div>
        <div class="metric">
          <span class="metric-label">Severity</span>
          <strong class="metric-value small">${escapeHtml(severity.class || "–")}</strong>
          <div class="metric-unit">Score: ${escapeHtml(severity.score ?? "–")} | Deviation: ${escapeHtml(severity.deviation_ratio ?? "–")}</div>
        </div>
        <div class="metric">
          <span class="metric-label">Consequence</span>
          <strong class="metric-value small">${escapeHtml(consequence.class || "–")}</strong>
          <div class="metric-unit">Score: ${escapeHtml(consequence.score ?? "–")}</div>
        </div>
      </div>

      ${data.operator_message ? `<div class="info-box"><strong>Operator message:</strong><br>${escapeHtml(data.operator_message)}</div>` : ""}
      ${data.reviewer_summary ? `<div class="info-box"><strong>Reviewer summary:</strong><br>${escapeHtml(data.reviewer_summary)}</div>` : ""}
      ${data.recommended_action ? `<div class="info-box"><strong>Recommended action:</strong><br>${escapeHtml(data.recommended_action)}</div>` : ""}

      <div class="two-col">
        <div class="panel">
          <h4>Short-term actions</h4>
          <ul class="result-list">${renderList(data.short_term_actions)}</ul>
        </div>
        <div class="panel">
          <h4>Long-term actions</h4>
          <ul class="result-list">${renderList(data.long_term_actions)}</ul>
        </div>
      </div>

      ${vulnerable.note ? `<div class="info-box"><strong>Vulnerable groups:</strong><br>${escapeHtml(vulnerable.note)}</div>` : ""}
      ${componentsHtml}
      ${graphHtml}
    </div>
  `;
}

// ------------------------------
// Coagulation-specific helpers
// ------------------------------
function getCoagulationOperationalThreshold(rawTurbidity) {
  const raw = extractNumber(rawTurbidity);

  if (raw === null) {
    return {
      threshold: null,
      basis: "No raw-water turbidity available"
    };
  }

  if (raw <= 10) {
    return {
      threshold: 1.0,
      basis: "Operational target based on low raw-water turbidity conditions"
    };
  }

  if (raw <= 20) {
    return {
      threshold: 2.0,
      basis: "Operational target based on moderate raw-water turbidity conditions"
    };
  }

  return {
    threshold: 2.0,
    basis: "Conservative operational review target for higher raw-water turbidity"
  };
}

function calculateRemovalEfficiency(rawTurbidity, predictedOutlet) {
  const raw = extractNumber(rawTurbidity);
  const pred = extractNumber(predictedOutlet);

  if (raw === null || pred === null || raw <= 0) return null;

  return ((raw - pred) / raw) * 100;
}

function updateCoagulationOperationalSummary(input, prediction) {
  const raw = extractNumber(input?.ftu_raw_water);
  const pred = extractNumber(prediction);

  const targetInfo = getCoagulationOperationalThreshold(raw);
  const efficiency = calculateRemovalEfficiency(raw, pred);

  setText("coagulation-threshold", targetInfo.threshold, 2);
  setText("coagulation-efficiency", efficiency, 1);

  const thresholdBasis = document.getElementById("coagulation-threshold-basis");
  if (thresholdBasis) thresholdBasis.textContent = targetInfo.basis;

  return targetInfo;
}

function populateCoagulationRiskForms(payload) {
  const mapping = {
    risk_coag_ftu_raw_water: payload.ftu_raw_water,
    risk_coag_fecl3_concentration: payload.fecl3_concentration,
    risk_coag_temperature_raw_water: payload.temperature_raw_water,
    risk_coag_ph_raw_water: payload.ph_raw_water,
    risk_coag_after_dredging: payload.after_dredging,
    risk_coag_lane: payload.lane,
    risk_coag_year: payload.year
  };

  Object.entries(mapping).forEach(([id, value]) => {
    const el = document.getElementById(id);
    if (el && value !== undefined && value !== null) {
      el.value = value;
    }
  });

  const treatmentSelectors = {
    'input[name="coagulation.ftu_raw_water"]': payload.ftu_raw_water,
    'input[name="coagulation.fecl3_concentration"]': payload.fecl3_concentration,
    'input[name="coagulation.temperature_raw_water"]': payload.temperature_raw_water,
    'input[name="coagulation.ph_raw_water"]': payload.ph_raw_water,
    'input[name="coagulation.after_dredging"]': payload.after_dredging,
    'input[name="coagulation.lane"]': payload.lane,
    'input[name="coagulation.year"]': payload.year,
    'input[name="treatment.coagulation.ftu_raw_water"]': payload.ftu_raw_water,
    'input[name="treatment.coagulation.fecl3_concentration"]': payload.fecl3_concentration,
    'input[name="treatment.coagulation.temperature_raw_water"]': payload.temperature_raw_water,
    'input[name="treatment.coagulation.ph_raw_water"]': payload.ph_raw_water,
    'input[name="treatment.coagulation.after_dredging"]': payload.after_dredging,
    'input[name="treatment.coagulation.lane"]': payload.lane,
    'input[name="treatment.coagulation.year"]': payload.year
  };

  Object.entries(treatmentSelectors).forEach(([selector, value]) => {
    const el = document.querySelector(selector);
    if (el && value !== undefined && value !== null) {
      el.value = value;
    }
  });
}

async function runAutomaticCoagulationRisk(payload) {
  try {
    populateCoagulationRiskForms(payload);
    const data = await postJSON(ENDPOINTS.riskCoagulation, payload);

    state.coagulation.lastRisk = data;

    renderRichRisk("coagulation-risk-output", data);
    renderRichRisk("risk-coagulation-output", data);

    const riskClass = data?.overall_risk?.class || "–";
    setBadge("coagulation-risk-badge", `Risk: ${riskClass}`, riskBadgeClass(riskClass));
  } catch (err) {
    renderJSON("coagulation-risk-output", { error: err.message });
    renderJSON("risk-coagulation-output", { error: err.message });
    setBadge("coagulation-risk-badge", "Risk: error", "high");
  }
}

// ------------------------------
// RL helpers
// ------------------------------
function syncRL5DisplayFromInputs() {
  const current = Number(document.getElementById("rl5_current_fecl3_dose")?.value);
  const recommended = Number(document.getElementById("rl5_recommended_fecl3_dose")?.value);
  const confidence = Number(document.getElementById("rl5_confidence")?.value);

  setText("rl5-current-dose-display", current, 2);
  setText("rl5-recommended-dose-display", recommended, 2);
  setText("rl5-confidence-display", confidence, 2);
}

function populateRL5RiskForms(payload) {
  setValue("risk_rl_current_fecl3_dose", payload.current_fecl3_dose);
  setValue("risk_rl_recommended_fecl3_dose", payload.recommended_fecl3_dose);
  setValue("risk_rl_output_turbidity", payload.output_turbidity);
  setValue("risk_rl_confidence", payload.confidence);

  const treatmentSelectors = {
    'input[name="rl.current_fecl3_dose"]': payload.current_fecl3_dose,
    'input[name="rl.recommended_fecl3_dose"]': payload.recommended_fecl3_dose,
    'input[name="rl.output_turbidity"]': payload.output_turbidity,
    'input[name="rl.confidence"]': payload.confidence,
    'input[name="treatment.rl.current_fecl3_dose"]': payload.current_fecl3_dose,
    'input[name="treatment.rl.recommended_fecl3_dose"]': payload.recommended_fecl3_dose,
    'input[name="treatment.rl.output_turbidity"]': payload.output_turbidity,
    'input[name="treatment.rl.confidence"]': payload.confidence
  };

  Object.entries(treatmentSelectors).forEach(([selector, value]) => {
    const el = document.querySelector(selector);
    if (el && value !== undefined && value !== null) {
      el.value = value;
    }
  });
}

function getRL5PayloadFromInputs() {
  return {
    current_fecl3_dose: Number(document.getElementById("rl5_current_fecl3_dose")?.value),
    recommended_fecl3_dose: Number(document.getElementById("rl5_recommended_fecl3_dose")?.value),
    output_turbidity: Number(document.getElementById("rl5_output_turbidity")?.value),
    confidence: Number(document.getElementById("rl5_confidence")?.value)
  };
}

async function runAutomaticRL5Risk(payload) {
  try {
    populateRL5RiskForms(payload);
    const data = await postJSON(ENDPOINTS.riskRL5, payload);

    state.rl5.lastInput = payload;
    state.rl5.lastRisk = data;

    renderRichRisk("rl5-risk-output", data);
    renderRichRisk("risk-rl5-output", data);

    const riskClass = data?.overall_risk?.class || "–";
    setBadge("rl5-risk-badge", `Risk: ${riskClass}`, riskBadgeClass(riskClass));
  } catch (err) {
    renderJSON("rl5-risk-output", { error: err.message });
    renderJSON("risk-rl5-output", { error: err.message });
    setBadge("rl5-risk-badge", "Risk: error", "high");
  }
}

// ------------------------------
// Ozonation helpers
// ------------------------------
function populateOzonationRiskForms() {
  const ct = state.ozonation.ctInput;
  const bromate = state.ozonation.bromateInput;
  const coliform = state.ozonation.coliformInput;

  if (ct) {
    const ctMap = {
      'input[name="ct.Chamber"]': ct.Chamber,
      'input[name="ct.WaterTemperature"]': ct.WaterTemperature,
      'input[name="ct.RFTurbidity"]': ct.RFTurbidity,
      'input[name="ct.FlowRate"]': ct.FlowRate,
      'input[name="ct.Ozonedosage"]': ct.Ozonedosage,
      'input[name="ozonation.ct.Chamber"]': ct.Chamber,
      'input[name="ozonation.ct.WaterTemperature"]': ct.WaterTemperature,
      'input[name="ozonation.ct.RFTurbidity"]': ct.RFTurbidity,
      'input[name="ozonation.ct.FlowRate"]': ct.FlowRate,
      'input[name="ozonation.ct.Ozonedosage"]': ct.Ozonedosage,
      'input[name="treatment.ozonation.ct.Chamber"]': ct.Chamber,
      'input[name="treatment.ozonation.ct.WaterTemperature"]': ct.WaterTemperature,
      'input[name="treatment.ozonation.ct.RFTurbidity"]': ct.RFTurbidity,
      'input[name="treatment.ozonation.ct.FlowRate"]': ct.FlowRate,
      'input[name="treatment.ozonation.ct.Ozonedosage"]': ct.Ozonedosage
    };

    Object.entries(ctMap).forEach(([selector, value]) => {
      const el = document.querySelector(selector);
      if (el) el.value = value ?? "";
    });
  }

  if (bromate) {
    const brMap = {
      'input[name="bromate.month"]': bromate.month,
      'input[name="bromate.Chamber"]': bromate.Chamber,
      'input[name="bromate.WaterTemperature"]': bromate.WaterTemperature,
      'input[name="bromate.RFTurbidity"]': bromate.RFTurbidity,
      'input[name="bromate.FlowRate"]': bromate.FlowRate,
      'input[name="bromate.Ozonedosage"]': bromate.Ozonedosage,
      'input[name="bromate.Residencetime"]': bromate.Residencetime,
      'input[name="bromate.WaterTemperature_1"]': bromate.WaterTemperature_1,
      'input[name="bromate.RFturbidity_1"]': bromate.RFturbidity_1,
      'input[name="bromate.FlowRate_1"]': bromate.FlowRate_1,
      'input[name="bromate.Ozonedosage_1"]': bromate.Ozonedosage_1,
      'input[name="bromate.CT_All"]': bromate.CT_All,

      'input[name="ozonation.bromate.month"]': bromate.month,
      'input[name="ozonation.bromate.Chamber"]': bromate.Chamber,
      'input[name="ozonation.bromate.WaterTemperature"]': bromate.WaterTemperature,
      'input[name="ozonation.bromate.RFTurbidity"]': bromate.RFTurbidity,
      'input[name="ozonation.bromate.FlowRate"]': bromate.FlowRate,
      'input[name="ozonation.bromate.Ozonedosage"]': bromate.Ozonedosage,
      'input[name="ozonation.bromate.Residencetime"]': bromate.Residencetime,
      'input[name="ozonation.bromate.WaterTemperature_1"]': bromate.WaterTemperature_1,
      'input[name="ozonation.bromate.RFturbidity_1"]': bromate.RFturbidity_1,
      'input[name="ozonation.bromate.FlowRate_1"]': bromate.FlowRate_1,
      'input[name="ozonation.bromate.Ozonedosage_1"]': bromate.Ozonedosage_1,
      'input[name="ozonation.bromate.CT_All"]': bromate.CT_All,

      'input[name="treatment.ozonation.bromate.month"]': bromate.month,
      'input[name="treatment.ozonation.bromate.Chamber"]': bromate.Chamber,
      'input[name="treatment.ozonation.bromate.WaterTemperature"]': bromate.WaterTemperature,
      'input[name="treatment.ozonation.bromate.RFTurbidity"]': bromate.RFTurbidity,
      'input[name="treatment.ozonation.bromate.FlowRate"]': bromate.FlowRate,
      'input[name="treatment.ozonation.bromate.Ozonedosage"]': bromate.Ozonedosage,
      'input[name="treatment.ozonation.bromate.Residencetime"]': bromate.Residencetime,
      'input[name="treatment.ozonation.bromate.WaterTemperature_1"]': bromate.WaterTemperature_1,
      'input[name="treatment.ozonation.bromate.RFturbidity_1"]': bromate.RFturbidity_1,
      'input[name="treatment.ozonation.bromate.FlowRate_1"]': bromate.FlowRate_1,
      'input[name="treatment.ozonation.bromate.Ozonedosage_1"]': bromate.Ozonedosage_1,
      'input[name="treatment.ozonation.bromate.CT_All"]': bromate.CT_All
    };

    Object.entries(brMap).forEach(([selector, value]) => {
      const el = document.querySelector(selector);
      if (el) el.value = value ?? "";
    });
  }

  if (coliform) {
    const colMap = {
      'input[name="coliform.Chamber"]': coliform.Chamber,
      'input[name="coliform.WaterTemperature"]': coliform.WaterTemperature,
      'input[name="coliform.RFTurbidity"]': coliform.RFTurbidity,
      'input[name="coliform.FlowRate"]': coliform.FlowRate,
      'input[name="coliform.Ozonedosage"]': coliform.Ozonedosage,
      'input[name="coliform.RFturbidity_1"]': coliform.RFturbidity_1,
      'input[name="coliform.CT_All"]': coliform.CT_All,

      'input[name="ozonation.coliform.Chamber"]': coliform.Chamber,
      'input[name="ozonation.coliform.WaterTemperature"]': coliform.WaterTemperature,
      'input[name="ozonation.coliform.RFTurbidity"]': coliform.RFTurbidity,
      'input[name="ozonation.coliform.FlowRate"]': coliform.FlowRate,
      'input[name="ozonation.coliform.Ozonedosage"]': coliform.Ozonedosage,
      'input[name="ozonation.coliform.RFturbidity_1"]': coliform.RFturbidity_1,
      'input[name="ozonation.coliform.CT_All"]': coliform.CT_All,

      'input[name="treatment.ozonation.coliform.Chamber"]': coliform.Chamber,
      'input[name="treatment.ozonation.coliform.WaterTemperature"]': coliform.WaterTemperature,
      'input[name="treatment.ozonation.coliform.RFTurbidity"]': coliform.RFTurbidity,
      'input[name="treatment.ozonation.coliform.FlowRate"]': coliform.FlowRate,
      'input[name="treatment.ozonation.coliform.Ozonedosage"]': coliform.Ozonedosage,
      'input[name="treatment.ozonation.coliform.RFturbidity_1"]': coliform.RFturbidity_1,
      'input[name="treatment.ozonation.coliform.CT_All"]': coliform.CT_All
    };

    Object.entries(colMap).forEach(([selector, value]) => {
      const el = document.querySelector(selector);
      if (el) el.value = value ?? "";
    });
  }
}

async function runAutomaticOzonationRisk() {
  if (!state.ozonation.ctInput || !state.ozonation.bromateInput || !state.ozonation.coliformInput) {
    return;
  }

  try {
    populateOzonationRiskForms();

    const payload = {
      ct: state.ozonation.ctInput,
      bromate: state.ozonation.bromateInput,
      coliform: state.ozonation.coliformInput,
      yopi_sensitive: true
    };

    const data = await postJSON(ENDPOINTS.riskOzonation, payload);
    state.ozonation.combinedRisk = data;

    renderRichRisk("ozonation-risk-output", data);
    renderRichRisk("risk-ozonation-output", data);

    const riskClass = data?.overall_risk?.class || "–";
    setBadge("ozonation-risk-badge", `Risk: ${riskClass}`, riskBadgeClass(riskClass));
  } catch (err) {
    renderJSON("ozonation-risk-output", { error: err.message });
    renderJSON("risk-ozonation-output", { error: err.message });
    setBadge("ozonation-risk-badge", "Risk: error", "high");
  }
}

// ------------------------------
// Coagulation chart helpers
// ------------------------------
let coagulationLiveInterval = null;
let coagulationHistoryLabels = [];
let coagulationRawHistory = [];
let coagulationHistoryValues = [];
let coagulationThresholdHistory = [];

function makeLineChart(canvasId, label) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;

  return new Chart(canvas.getContext("2d"), {
    type: "line",
    data: {
      labels: [],
      datasets: [{
        label,
        data: [],
        tension: 0.35,
        fill: true,
        borderWidth: 3,
        pointRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false
    }
  });
}

function makeBarChart(canvasId, label) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;

  return new Chart(canvas.getContext("2d"), {
    type: "bar",
    data: {
      labels: [label],
      datasets: [{
        label,
        data: [0],
        borderWidth: 1,
        borderRadius: 10
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false
    }
  });
}

function makeDoughnutChart(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;

  return new Chart(canvas.getContext("2d"), {
    type: "doughnut",
    data: {
      labels: ["CT", "Bromate", "Coliform"],
      datasets: [{
        data: [0, 0, 0],
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "68%"
    }
  });
}

const charts = {
  coagulation: makeLineChart("chart-coagulation", "Coagulation prediction"),
  ct: makeBarChart("chart-ct", "CT"),
  bromate: makeBarChart("chart-bromate", "Bromate"),
  coliform: makeBarChart("chart-coliform", "Coliform"),
  ozonationSummary: makeDoughnutChart("chart-ozonation-summary")
};

function ensureCoagulationChartDatasets() {
  if (!charts.coagulation) return;

  const datasets = charts.coagulation.data.datasets;
  if (datasets.length >= 3) return;

  charts.coagulation.data.datasets = [
    {
      label: "Raw water turbidity",
      data: [],
      tension: 0.35,
      fill: false,
      borderWidth: 3,
      pointRadius: 4
    },
    {
      label: "Predicted outlet turbidity",
      data: [],
      tension: 0.35,
      fill: true,
      borderWidth: 3,
      pointRadius: 4
    },
    {
      label: "Operational target",
      data: [],
      tension: 0,
      fill: false,
      borderWidth: 2,
      pointRadius: 0,
      borderDash: [6, 4]
    }
  ];
}

function updateCoagulationChartSingle(label, raw, pred, threshold) {
  if (!charts.coagulation) return;
  ensureCoagulationChartDatasets();

  charts.coagulation.data.labels = [label];
  charts.coagulation.data.datasets[0].data = [raw ?? 0];
  charts.coagulation.data.datasets[1].data = [pred ?? 0];
  charts.coagulation.data.datasets[2].data = [threshold ?? 0];
  charts.coagulation.update();
}

function updateCoagulationChartHistory(label, raw, pred, threshold) {
  if (!charts.coagulation) return;
  ensureCoagulationChartDatasets();

  coagulationHistoryLabels.push(label);
  coagulationRawHistory.push(raw ?? 0);
  coagulationHistoryValues.push(pred ?? 0);
  coagulationThresholdHistory.push(threshold ?? 0);

  if (coagulationHistoryLabels.length > 12) {
    coagulationHistoryLabels.shift();
    coagulationRawHistory.shift();
    coagulationHistoryValues.shift();
    coagulationThresholdHistory.shift();
  }

  charts.coagulation.data.labels = coagulationHistoryLabels;
  charts.coagulation.data.datasets[0].data = coagulationRawHistory;
  charts.coagulation.data.datasets[1].data = coagulationHistoryValues;
  charts.coagulation.data.datasets[2].data = coagulationThresholdHistory;
  charts.coagulation.update();
}

ensureCoagulationChartDatasets();

// ------------------------------
// Static load buttons
// ------------------------------
document.getElementById("btn-source-overview")?.addEventListener("click", async () => {
  try {
    renderJSON("source-overview", await getJSON(ENDPOINTS.sourceOverview));
  } catch (err) {
    renderJSON("source-overview", { error: err.message });
  }
});

document.getElementById("btn-source-latest")?.addEventListener("click", async () => {
  try {
    renderJSON("source-latest", await getJSON(ENDPOINTS.sourceLatest));
  } catch (err) {
    renderJSON("source-latest", { error: err.message });
  }
});

document.getElementById("btn-treatment-overview")?.addEventListener("click", async () => {
  try {
    renderJSON("treatment-overview", await getJSON(ENDPOINTS.treatmentOverview));
  } catch (err) {
    renderJSON("treatment-overview", { error: err.message });
  }
});

document.getElementById("btn-treatment-coag-latest")?.addEventListener("click", async () => {
  try {
    renderJSON("treatment-coag-latest", await getJSON(ENDPOINTS.treatmentCoagLatest));
  } catch (err) {
    renderJSON("treatment-coag-latest", { error: err.message });
  }
});

document.getElementById("btn-rl5-latest")?.addEventListener("click", async () => {
  try {
    const data = await getJSON(ENDPOINTS.treatmentRLLatest);
    renderJSON("rl5-latest", data);

    const currentDose = extractNumber(data.current_fecl3_dose ?? data.current_dose);
    const recommendedDose = extractNumber(data.recommended_fecl3_dose ?? data.recommended_dose);
    const outputTurbidity = extractNumber(data.output_turbidity ?? data.predicted_output_turbidity);
    const confidence = extractNumber(data.confidence);

    if (currentDose !== null) setValue("rl5_current_fecl3_dose", currentDose);
    if (recommendedDose !== null) setValue("rl5_recommended_fecl3_dose", recommendedDose);
    if (outputTurbidity !== null) setValue("rl5_output_turbidity", outputTurbidity);
    if (confidence !== null) setValue("rl5_confidence", confidence);

    syncRL5DisplayFromInputs();

    const payload = getRL5PayloadFromInputs();
    if (
      !Number.isNaN(payload.current_fecl3_dose) &&
      !Number.isNaN(payload.recommended_fecl3_dose) &&
      !Number.isNaN(payload.output_turbidity) &&
      !Number.isNaN(payload.confidence)
    ) {
      await runAutomaticRL5Risk(payload);
    }
  } catch (err) {
    renderJSON("rl5-latest", { error: err.message });
  }
});

document.getElementById("btn-bactosense-latest")?.addEventListener("click", async () => {
  try {
    renderJSON("bactosense-latest", await getJSON(ENDPOINTS.treatmentBactoSense));
  } catch (err) {
    renderJSON("bactosense-latest", { error: err.message });
  }
});

document.getElementById("btn-distribution-overview")?.addEventListener("click", async () => {
  try {
    renderJSON("distribution-overview", await getJSON(ENDPOINTS.distributionOverview));
  } catch (err) {
    renderJSON("distribution-overview", { error: err.message });
  }
});

document.getElementById("btn-distribution-latest")?.addEventListener("click", async () => {
  try {
    renderJSON("distribution-latest", await getJSON(ENDPOINTS.distributionLatest));
  } catch (err) {
    renderJSON("distribution-latest", { error: err.message });
  }
});

document.getElementById("btn-risk-overview")?.addEventListener("click", async () => {
  try {
    renderJSON("risk-overview", await getJSON(ENDPOINTS.riskOverview));
  } catch (err) {
    renderJSON("risk-overview", { error: err.message });
  }
});

// ------------------------------
// Demo prefills
// ------------------------------
document.getElementById("btn-coagulation-demo")?.addEventListener("click", () => {
  setValue("coag_ftu_raw_water", 6.2);
  setValue("coag_fecl3_concentration", 14.5);
  setValue("coag_temperature_raw_water", 12.0);
  setValue("coag_ph_raw_water", 7.4);
  setValue("coag_after_dredging", 45);
  setValue("coag_lane", 2);
  setValue("coag_year", 2025);
});

document.getElementById("btn-rl5-demo")?.addEventListener("click", async () => {
  const payload = {
    current_fecl3_dose: 14.5,
    recommended_fecl3_dose: 16.0,
    output_turbidity: 5.4,
    confidence: 0.75
  };

  setValue("rl5_current_fecl3_dose", payload.current_fecl3_dose);
  setValue("rl5_recommended_fecl3_dose", payload.recommended_fecl3_dose);
  setValue("rl5_output_turbidity", payload.output_turbidity);
  setValue("rl5_confidence", payload.confidence);

  syncRL5DisplayFromInputs();
  await runAutomaticRL5Risk(payload);
});

document.getElementById("btn-ct-demo")?.addEventListener("click", () => {
  setValue("ct_Chamber", 2);
  setValue("ct_WaterTemperature", 11.5);
  setValue("ct_RFTurbidity", 3.5);
  setValue("ct_FlowRate", 1200);
  setValue("ct_Ozonedosage", 1.8);
});

document.getElementById("btn-bromate-demo")?.addEventListener("click", () => {
  setValue("br_month", 4);
  setValue("br_Chamber", 2);
  setValue("br_WaterTemperature", 11.5);
  setValue("br_RFTurbidity", 3.5);
  setValue("br_FlowRate", 1200);
  setValue("br_Ozonedosage", 1.8);
  setValue("br_Residencetime", 8.4);
  setValue("br_WaterTemperature_1", 11.2);
  setValue("br_RFturbidity_1", 3.3);
  setValue("br_FlowRate_1", 1180);
  setValue("br_Ozonedosage_1", 1.75);
  setValue("br_CT_All", 0.55);
});

document.getElementById("btn-coliform-demo")?.addEventListener("click", () => {
  setValue("col_Chamber", 2);
  setValue("col_WaterTemperature", 11.5);
  setValue("col_RFTurbidity", 3.5);
  setValue("col_FlowRate", 1200);
  setValue("col_Ozonedosage", 1.8);
  setValue("col_RFturbidity_1", 3.3);
  setValue("col_CT_All", 0.55);
});

// ------------------------------
// RL display sync
// ------------------------------
["rl5_current_fecl3_dose", "rl5_recommended_fecl3_dose", "rl5_confidence", "rl5_output_turbidity"].forEach((id) => {
  document.getElementById(id)?.addEventListener("input", async () => {
    syncRL5DisplayFromInputs();

    const payload = getRL5PayloadFromInputs();
    if (
      !Number.isNaN(payload.current_fecl3_dose) &&
      !Number.isNaN(payload.recommended_fecl3_dose) &&
      !Number.isNaN(payload.output_turbidity) &&
      !Number.isNaN(payload.confidence)
    ) {
      await runAutomaticRL5Risk(payload);
    }
  });
});

syncRL5DisplayFromInputs();

// ------------------------------
// Ozonation dashboard state
// ------------------------------
const latestOzonation = {
  ct: null,
  bromate: null,
  coliform: null
};

function refreshOzonationDashboard() {
  setText("dash-ct", latestOzonation.ct, 3);
  setText("dash-bromate", latestOzonation.bromate, 3);
  setText("dash-coliform", latestOzonation.coliform, 3);

  const list = document.getElementById("dash-list");
  if (list) {
    const items = [];
    if (latestOzonation.ct !== null) items.push("<li>CT prediction has been generated successfully.</li>");
    if (latestOzonation.bromate !== null) items.push("<li>Bromate prediction has been generated successfully.</li>");
    if (latestOzonation.coliform !== null) items.push("<li>Coliform prediction has been generated successfully.</li>");
    if (!items.length) items.push("<li>No ozonation model has been run yet.</li>");
    list.innerHTML = items.join("");
  }

  if (charts.ozonationSummary) {
    charts.ozonationSummary.data.datasets[0].data = [
      latestOzonation.ct ?? 0,
      latestOzonation.bromate ?? 0,
      latestOzonation.coliform ?? 0
    ];
    charts.ozonationSummary.update();
  }
}

refreshOzonationDashboard();

// ------------------------------
// Coagulation manual/live
// ------------------------------
function stopCoagulationLiveMode() {
  if (coagulationLiveInterval) {
    clearInterval(coagulationLiveInterval);
    coagulationLiveInterval = null;
  }
  setBadge("coagulation-mode-badge", "Mode: manual", "info");
}

document.getElementById("form-coagulation")?.addEventListener("submit", async (e) => {
  e.preventDefault();

  try {
    const payload = formDataToObject(e.target);
    const data = await postJSON(ENDPOINTS.coagulation, payload);

    const pred = pickPrediction(data, ["prediction"]);
    state.coagulation.lastInput = payload;
    state.coagulation.lastPrediction = pred;

    setText("coagulation-prediction", pred, 3);

    const targetInfo = updateCoagulationOperationalSummary(payload, pred);
    const status = classifyPrediction(pred, targetInfo.threshold ?? 1, (targetInfo.threshold ?? 1) + 1);

    setText("coagulation-status", status, 0);
    setBadge("coagulation-badge", `Status: ${status}`, levelFromText(status));
    setBadge("coagulation-mode-badge", "Mode: manual", "info");
    const lastUpdateEl = document.getElementById("coagulation-last-update");
    if (lastUpdateEl) lastUpdateEl.textContent = "manual";

    setText("live-ftu", payload.ftu_raw_water, 2);
    setText("live-fecl3", payload.fecl3_concentration, 2);
    setText("live-temp", payload.temperature_raw_water, 2);
    setText("live-ph", payload.ph_raw_water, 2);
    setText("live-dredging", payload.after_dredging, 0);
    setText("live-lane", payload.lane, 0);
    setText("live-year", payload.year, 0);

    updateCoagulationChartSingle(
      "Manual run",
      extractNumber(payload.ftu_raw_water),
      pred,
      targetInfo.threshold
    );

    await runAutomaticCoagulationRisk(payload);
  } catch (err) {
    alert("Coagulation request failed: " + err.message);
  }
});

async function updateLiveCoagulationOnce() {
  try {
    const data = await getJSON(ENDPOINTS.coagulationLive);
    const pred = pickPrediction(data, ["prediction"]);
    const input = data.input_data || {};
    const timestamp = data.timestamp || "–";

    state.coagulation.lastInput = input;
    state.coagulation.lastPrediction = pred;

    setText("coagulation-prediction", pred, 3);

    const targetInfo = updateCoagulationOperationalSummary(input, pred);
    const status = classifyPrediction(pred, targetInfo.threshold ?? 1, (targetInfo.threshold ?? 1) + 1);

    setText("coagulation-status", status, 0);
    setBadge("coagulation-badge", `Status: ${status}`, levelFromText(status));
    setBadge("coagulation-mode-badge", "Mode: live", "info");
    const lastUpdateEl = document.getElementById("coagulation-last-update");
    if (lastUpdateEl) lastUpdateEl.textContent = timestamp;

    setText("live-ftu", input.ftu_raw_water, 2);
    setText("live-fecl3", input.fecl3_concentration, 2);
    setText("live-temp", input.temperature_raw_water, 2);
    setText("live-ph", input.ph_raw_water, 2);
    setText("live-dredging", input.after_dredging, 0);
    setText("live-lane", input.lane, 0);
    setText("live-year", input.year, 0);

    setValue("coag_ftu_raw_water", input.ftu_raw_water);
    setValue("coag_fecl3_concentration", input.fecl3_concentration);
    setValue("coag_temperature_raw_water", input.temperature_raw_water);
    setValue("coag_ph_raw_water", input.ph_raw_water);
    setValue("coag_after_dredging", input.after_dredging);
    setValue("coag_lane", input.lane);
    setValue("coag_year", input.year);

    let shortLabel = timestamp;
    try {
      shortLabel = new Date(timestamp).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
      });
    } catch (_) {}

    updateCoagulationChartHistory(
      shortLabel,
      extractNumber(input.ftu_raw_water),
      pred,
      targetInfo.threshold
    );

    await runAutomaticCoagulationRisk(input);
  } catch (err) {
    console.error(err);
    setBadge("coagulation-badge", "Status: live error", "high");
    setBadge("coagulation-risk-badge", "Risk: error", "high");
  }
}

document.getElementById("btn-coagulation-live-start")?.addEventListener("click", async () => {
  stopCoagulationLiveMode();
  coagulationHistoryLabels = [];
  coagulationRawHistory = [];
  coagulationHistoryValues = [];
  coagulationThresholdHistory = [];
  await updateLiveCoagulationOnce();
  coagulationLiveInterval = setInterval(updateLiveCoagulationOnce, 5000);
});

document.getElementById("btn-coagulation-live-stop")?.addEventListener("click", () => {
  stopCoagulationLiveMode();
});

// ------------------------------
// Ozonation forms
// ------------------------------
document.getElementById("form-ct")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = formDataToObject(e.target);

    let data;
    try {
      data = await postJSON(ENDPOINTS.treatmentCT, payload);
    } catch (_) {
      data = await postJSON(ENDPOINTS.ct, payload);
    }

    const pred = pickPrediction(data, ["ct_prediction", "prediction"]);
    state.ozonation.ctInput = payload;
    state.ozonation.ctPrediction = pred;

    setText("ct-prediction", pred, 3);

    const status = classifyPrediction(pred, 0.3, 0.7);
    setText("ct-status", status, 0);

    if (charts.ct) {
      charts.ct.data.datasets[0].data = [pred ?? 0];
      charts.ct.update();
    }

    latestOzonation.ct = pred;
    refreshOzonationDashboard();

    await runAutomaticOzonationRisk();
  } catch (err) {
    alert("CT request failed: " + err.message);
  }
});

document.getElementById("form-bromate")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = formDataToObject(e.target);

    let data;
    try {
      data = await postJSON(ENDPOINTS.treatmentBromate, payload);
    } catch (_) {
      data = await postJSON(ENDPOINTS.bromate, payload);
    }

    const pred = pickPrediction(data, ["bromate_prediction", "prediction"]);
    state.ozonation.bromateInput = payload;
    state.ozonation.bromatePrediction = pred;

    setText("bromate-prediction", pred, 3);

    const status = classifyPrediction(pred, 3, 8);
    setText("bromate-status", status, 0);

    if (charts.bromate) {
      charts.bromate.data.datasets[0].data = [pred ?? 0];
      charts.bromate.update();
    }

    latestOzonation.bromate = pred;
    refreshOzonationDashboard();

    await runAutomaticOzonationRisk();
  } catch (err) {
    alert("Bromate request failed: " + err.message);
  }
});

document.getElementById("form-coliform")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = formDataToObject(e.target);

    let data;
    try {
      data = await postJSON(ENDPOINTS.treatmentColiform, payload);
    } catch (_) {
      data = await postJSON(ENDPOINTS.coliform, payload);
    }

    const pred = pickPrediction(data, ["coliform_prediction", "prediction"]);
    state.ozonation.coliformInput = payload;
    state.ozonation.coliformPrediction = pred;

    setText("coliform-prediction", pred, 3);

    const status = classifyInverse(pred, 1.5, 2.5);
    setText("coliform-status", status, 0);

    if (charts.coliform) {
      charts.coliform.data.datasets[0].data = [pred ?? 0];
      charts.coliform.update();
    }

    latestOzonation.coliform = pred;
    refreshOzonationDashboard();

    await runAutomaticOzonationRisk();
  } catch (err) {
    alert("Coliform request failed: " + err.message);
  }
});

// ------------------------------
// Risk forms - manual screens still work
// ------------------------------
document.getElementById("form-risk-source")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = normalizeBooleanStrings(formDataToObject(e.target));
    const data = await postJSON(ENDPOINTS.riskSourceSose9, payload);
    renderRichRisk("risk-source-output", data);
  } catch (err) {
    renderJSON("risk-source-output", { error: err.message });
  }
});

document.getElementById("form-risk-coagulation")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = formDataToObject(e.target);
    const data = await postJSON(ENDPOINTS.riskCoagulation, payload);
    state.coagulation.lastRisk = data;
    renderRichRisk("risk-coagulation-output", data);
  } catch (err) {
    renderJSON("risk-coagulation-output", { error: err.message });
  }
});

document.getElementById("form-risk-rl5")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = normalizeBooleanStrings(formDataToObject(e.target));
    const data = await postJSON(ENDPOINTS.riskRL5, payload);
    state.rl5.lastRisk = data;
    renderRichRisk("risk-rl5-output", data);
  } catch (err) {
    renderJSON("risk-rl5-output", { error: err.message });
  }
});

document.getElementById("form-risk-ozonation")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = normalizeBooleanStrings(formDataToNestedObject(e.target));
    const data = await postJSON(ENDPOINTS.riskOzonation, payload);
    state.ozonation.combinedRisk = data;
    renderRichRisk("risk-ozonation-output", data);
  } catch (err) {
    renderJSON("risk-ozonation-output", { error: err.message });
  }
});

document.getElementById("form-risk-distribution")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = normalizeBooleanStrings(formDataToObject(e.target));
    const data = await postJSON(ENDPOINTS.riskDistributionSose11, payload);
    renderRichRisk("risk-distribution-output", data);
  } catch (err) {
    renderJSON("risk-distribution-output", { error: err.message });
  }
});

document.getElementById("form-risk-treatment")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = normalizeBooleanStrings(formDataToNestedObject(e.target));
    const data = await postJSON(ENDPOINTS.riskTreatmentCurrent, payload);
    renderRichRisk("risk-treatment-output", data);
  } catch (err) {
    renderJSON("risk-treatment-output", { error: err.message });
  }
});

document.getElementById("form-risk-system")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = normalizeBooleanStrings(formDataToNestedObject(e.target));
    const data = await postJSON(ENDPOINTS.riskSystemCurrent, payload);
    renderRichRisk("risk-system-output", data);
  } catch (err) {
    renderJSON("risk-system-output", { error: err.message });
  }
});