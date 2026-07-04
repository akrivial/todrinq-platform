// ==========================================
// ToDrinQ UI - final unified version
// ==========================================

const ENDPOINTS = {
  coagulation: "/predict/coagulation",
  coagulationLive: "/predict/coagulation/live",

  sourceOverview: "/source/overview",
  sourceLatest: "/source/sose-9/latest",
  sourcePredict: "/source/sose-9/predict",
  sose9Live: "/source/sose-9/live",

  treatmentOverview: "/treatment/overview",
  treatmentCoagLatest: "/treatment/coagulation/latest",
  treatmentRLLatest: "/treatment/coagulation/rl/latest",
  treatmentCT: "/treatment/ozonation/ct",
  treatmentBromate: "/treatment/ozonation/bromate",
  treatmentColiform: "/treatment/ozonation/coliform",
  treatmentCTLatest: "/treatment/ozonation/ct/latest",
  treatmentBromateLatest: "/treatment/ozonation/bromate/latest",
  treatmentColiformLatest: "/treatment/ozonation/coliform/latest",
  treatmentBactoSense: "/treatment/hard-sensors/bactosense-4/latest",
  rwsLatest: "/source/hard-sensors/rws/latest",
  rwsTimeseries: "/source/hard-sensors/rws/timeseries",


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
  riskOzonationOp: "/risk/ozonation/operational",
  riskDistributionSose11: "/risk/distribution/sose-11/current",
  riskTreatmentCurrent: "/risk/treatment/current",
  riskSystemCurrent: "/risk/system/current"
};

const breadcrumbs = document.getElementById("breadcrumbs");

const screenTitles = {
  "screen-home": "ToDrinQ Platform / Home Page",
  "screen-source": "Source Module – Inlet Turbidity Prediction — SoSe #9",
  "screen-treatment": "Treatment Module",
  "screen-treatment-overview": "Treatment Overview",
  "screen-hard-placeholder": "Hard Sensor Monitoring",
  "screen-soft-select": "Soft Sensor Platform Models",
  "screen-coagulation": "Turbidity After Coagulation, Flocculation and Sedimentation — SoSe #8",
  "screen-rl5": "FeCl₃ Dosing Advisory — RL #5",
  "screen-ozonation-select": "Ozonation Models — SoSe #10 / #10.1 / #10.2",
  "screen-ct": "CT / Ozone Exposure — SoSe #10",
  "screen-bromate": "Bromate Formation — SoSe #10.1",
  "screen-coliform": "Microbial Removal — SoSe #10.2",
  "screen-ozonation-dashboard": "Ozonation Decision Support — SoSe #10 / #10.1 / #10.2",
  "screen-hard-sensors": "BactoSense Monitoring — Hard Sensor #4",
  "screen-distribution": "Distribution Module – SoSe #11",
  "screen-risk": "Risk Module",
  "screen-risk-overview": "Risk Overview",
  "screen-risk-source": "Inlet Turbidity Attention — SoSe #9",
  "screen-risk-coagulation": "Outlet Turbidity Risk — SoSe #8",
  "screen-risk-rl5": "RL #5 Advisory Validation",
  "screen-risk-ozonation": "Combined Ozonation Risk — SoSe #10 / #10.1 / #10.2",
  "screen-risk-distribution": "SoSe #11 Distribution Risk",
  "screen-risk-treatment": "Treatment Current Risk",
  "screen-risk-system": "Source-to-Tap System Risk"
};

const state = {
  source: {
    lastInput: null,
    lastPrediction: null,
    lastRisk: null,
    lastTimestamp: null
  },
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
    combinedRisk: null,
    operationalRisk: null
  },
  distribution: {
    lastInput: null,
    lastRisk: null
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
    <button type="button" data-nav="screen-home">ToDrinQ Platform / Home Page</button>
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

const TOKEN = "todrinq-demo-2026";

function withToken(url) {
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}token=${TOKEN}`;
}

async function getJSON(url) {
  const r = await fetch(withToken(url));
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`${r.status} ${text}`);
  }
  return r.json();
}

async function postJSON(url, payload) {
  const r = await fetch(withToken(url), {
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

function renderStatusCard(id, title, data) {
  const el = document.getElementById(id);
  if (!el) return;
  const status = data?.status || data?.validation_status || "awaiting_data";
  const message = data?.message || data?.validation_message || "Awaiting validated data.";
  const todos = data?.validation_todos || (data?.todo ? [data.todo] : []);
  el.innerHTML = `
    <div class="info-box">
      <strong>${escapeHtml(title)}</strong><br>
      Status: ${escapeHtml(status)}<br>
      ${escapeHtml(message)}
      ${todos.length ? `<ul class="result-list">${renderList(todos)}</ul>` : ""}
    </div>`;
}

function renderRL5Advisory(id, data) {
  const el = document.getElementById(id);
  if (!el) return;
  const advisory = data?.operator_advisory || {};
  const dose = extractNumber(advisory.recommended_fecl3_dose ?? data?.recommended_fecl3_concentration?.value);
  const turb = extractNumber(advisory.predicted_effluent_turbidity ?? data?.predicted_outlet_turbidity?.value);
  const flow = extractNumber(data?.recommended_fecl3_dosing_flow?.value);
  const status = advisory.confidence_status || data?.validation_status || "under validation";
  el.innerHTML = `
    <div class="rc rc--moderate">
      <div class="rc-header">
        <span class="rc-icon">&#9888;</span>
        <div class="rc-header-text">
          <span class="rc-sensor">FeCl3 dosing advisory</span>
          <div class="rc-level">${escapeHtml(status).toUpperCase()}</div>
        </div>
      </div>
      <div class="rc-body">
        <div class="rc-detail-grid">
          <div><span>Recommended FeCl3 dose</span><strong>${dose == null ? "Awaiting run" : dose.toFixed(2)} mg/L</strong></div>
          <div><span>Predicted effluent turbidity</span><strong>${turb == null ? "Awaiting validation" : turb.toFixed(3)} NTU</strong></div>
          <div><span>Dosing-flow conversion</span><strong>${flow == null ? "Awaiting flow input" : flow.toFixed(2)}</strong></div>
          <div><span>Timestamp</span><strong>&#128337; ${escapeHtml(data?.timestamp || "latest advisory run")}</strong></div>
        </div>
        <div class="rc-message">${escapeHtml(data?.validation_message || "RL #5 is advisory support only and remains under validation.")}</div>
        ${_rcActions(data?.validation_todos || ["TODO(Greg): verify ACTION_MAP, unit conversion, and model-output interpretation before final release."])}
      </div>
    </div>`;
}

function renderBactoSenseStatus(id, data) {
  const el = document.getElementById(id);
  if (!el) return;
  const measures = data?.measurements || {};
  const rows = [
    ["Influent ozone", measures.influent_ozone],
    ["Effluent ozone", measures.effluent_ozone],
    ["Influent UV", measures.influent_uv],
    ["Effluent UV", measures.effluent_uv],
    ["Influent intact cell number", measures.influent_bactosense_intact_cell_number],
    ["Effluent intact cell number", measures.effluent_bactosense_intact_cell_number],
  ];
  el.innerHTML = `
    <div class="rc rc--low">
      <div class="rc-header">
        <span class="rc-icon">&#128337;</span>
        <div class="rc-header-text">
          <span class="rc-sensor">BactoSense hard-sensor connection</span>
          <div class="rc-level">${escapeHtml(data?.status || "AWAITING DATA").toUpperCase()}</div>
        </div>
      </div>
      <div class="rc-body">
        <div class="rc-detail-grid">
          ${rows.map(([label, value]) => `<div><span>${escapeHtml(label)}</span><strong>${value == null ? "Awaiting data" : escapeHtml(value)}</strong></div>`).join("")}
        </div>
        <div class="rc-message">${escapeHtml(data?.message || "No BactoSense values are connected yet.")}</div>
        ${data?.todo ? _rcActions([data.todo]) : ""}
      </div>
    </div>`;
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

// Sensor-specific threshold hints (colored dots, matching Coagulation card style)
const SENSOR_HINTS = {
  "Inlet turbidity prediction": "Reference period 2022-2024: P5 7.8 FTU · P50 15 FTU · P90 23 FTU (top 10%) · P95 28 FTU. 20 FTU is an attention/reference line: be attentive for coagulation.",
  "SoSe #10":   "&#128994; &ge;0.7 mg*min/L &nbsp;&middot;&nbsp; &#128993; 0.3&ndash;0.7 &nbsp;&middot;&nbsp; &#128308; &lt;0.3. CT scaling requires validation.",
  "Bromate": "&#128994; &lt;5 ug/L &nbsp;&middot;&nbsp; &#128993; 5&ndash;10 ug/L &nbsp;&middot;&nbsp; &#128308; &ge;10 ug/L",
  "Microbial removal": "&#128994; &gt;1.2 log removal &nbsp;&middot;&nbsp; &#128993; 0.85&ndash;1.2 &nbsp;&middot;&nbsp; &#128308; &lt;0.85",
  "SoSe #11":   "&#128994; p &lt;0.15 &nbsp;&middot;&nbsp; &#128993; 0.15&ndash;0.40 &nbsp;&middot;&nbsp; &#128308; &ge;0.40",
};

// Unified .rc card renderer for all build_response()-structured endpoints
// (RL #5, Source SoSe #9, Distribution SoSe #11, CT individual)
function renderRichRisk(id, data) {
  const el = document.getElementById(id);
  if (!el) return;

  if (!data || data.error) {
    el.innerHTML = `<pre class="json-box">${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
    return;
  }

  // If it's a combined ozonation response (has .components), delegate
  if (data.components && !data.traffic_light) {
    el.innerHTML = buildRichRiskHtml(data);
    return;
  }

  const overall = data.overall_risk || {};
  const lh = data.likelihood || {};
  const sv = data.severity   || {};
  const cq = data.consequence || {};
  const mod = _rcClass(overall.class);

  // Determine icon from level
  const icon = mod === "low" ? "🟢" : mod === "high" ? "🔴" : "🟡";

  // Prediction value + unit (sensor-specific)
  const predVal = typeof data.prediction === "number" ? data.prediction.toFixed(3) : (data.prediction ?? "–");
  const predUnit = (() => {
    const s = (data.sensor || "").toLowerCase();
    if (s.includes("outlet turbidity")) return "NTU";
    if (s.includes("inlet turbidity")) return "FTU";
    if (s.includes("bromate")) return "ug/L";
    if (s.includes("microbial")) return "log removal";
    if (s.includes("#10")) return "mg/L·min";
    if (s.includes("#11")) return "probability";
    if (s.includes("rl")) return "mg/L";
    return "";
  })();

  const lhScore   = lh.score || 1;
  const svScore   = sv.score || 1;
  const riskScore = lhScore * svScore;

  // Sensor-specific threshold hint (colored dots, matching Coagulation card)
  const thresholdHint = SENSOR_HINTS[data.sensor] || null;
  const mainMsg = data.operator_message || data.recommended_action || "";
  const distanceMsg = data.distance_to_high_threshold?.message;
  const highThreshold = data.traffic_light?.thresholds?.high_boundary;
  const sose9 = data.sose9_persistence;
  const sose9Details = sose9 ? `
    <div class="rc-detail-grid">
      <div><span>Latest prediction</span><strong>${Number(sose9.latest_prediction ?? sose9.latest_3h_ahead_prediction).toFixed(3)} ${escapeHtml(sose9.unit || "FTU")}</strong></div>
      <div><span>Prediction frequency</span><strong>${escapeHtml(sose9.prediction_frequency || "hourly")}</strong></div>
      <div><span>Primary horizon</span><strong>${escapeHtml(sose9.primary_horizon || "1h preferred when available")}</strong></div>
      <div><span>Very unusual band</span><strong>${escapeHtml(sose9.high_threshold_label || ">P95")}</strong></div>
      <div><span>Consecutive hourly values above P95</span><strong>${escapeHtml(sose9.display_count || "0/3")}</strong></div>
      <div><span>Operational attention</span><strong>${escapeHtml(sose9.operational_risk || overall.class || "–")}</strong></div>
    </div>` : "";

  el.innerHTML = `
    <div class="rc rc--${mod}">
      <div class="rc-header">
        <span class="rc-icon">${icon}</span>
        <div class="rc-header-text">
          <span class="rc-sensor">${escapeHtml(data.sensor || data.submodule || "Risk")}</span>
          <div class="rc-level">${(overall.class || "–").toUpperCase()} RISK</div>
        </div>
        <span class="rc-score-chip">Score ${riskScore}/9</span>
      </div>
      <div class="rc-body">
        <div class="rc-value-row">
          <span class="rc-value">${predVal}</span>
          ${predUnit ? `<span class="rc-unit">${predUnit}</span>` : ""}
          ${data.threshold != null ? `<span style="margin-left:12px;font-size:.78rem;color:var(--muted);">threshold ${data.threshold} ${predUnit}</span>` : ""}
          ${highThreshold != null ? `<span style="margin-left:12px;font-size:.78rem;color:var(--muted);">high ${highThreshold} ${predUnit}</span>` : ""}
        </div>
        ${thresholdHint ? `<div class="rc-threshold-hint">${thresholdHint}</div>` : ""}
        ${mainMsg ? `<div class="rc-message">${escapeHtml(mainMsg)}</div>` : ""}
        ${sose9Details}
        ${distanceMsg ? `<div class="rc-distance">${escapeHtml(distanceMsg)}</div>` : ""}
        ${_rcActions(data.short_term_actions)}
        ${data.long_term_actions?.length ? `
          <details style="margin-top:10px;">
            <summary style="cursor:pointer;font-size:.8rem;color:var(--muted);font-weight:600;">Long-term actions</summary>
            ${_rcActions(data.long_term_actions)}
          </details>` : ""}
      </div>
      ${_rcFooter([
        ["Likelihood", `${lh.class || "–"} (p=${lh.probability_proxy ?? lh.score ?? "–"})`],
        ["Severity",   `${sv.class || "–"} (dev=${sv.deviation_ratio ?? sv.deviation_above_low_threshold ?? sv.score ?? "–"})`],
        ["Risk score", `${riskScore} — ${overall.class || "–"}`],
        ["Thresholds",  highThreshold != null ? `${data.threshold ?? "–"} / ${highThreshold} ${predUnit}` : `${data.threshold ?? "–"} ${predUnit}`],
      ])}
    </div>`;
}

function classifyCT(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "–";
  if (value >= 0.7) return "Adequate";
  if (value >= 0.3) return "Review";
  return "Insufficient";
}

// For combined responses (ozonation current, treatment, system)
function buildRichRiskHtml(data) {
  const overall = data.overall_risk || {};
  const mod = _rcClass(overall.class);
  const icon = mod === "low" ? "🟢" : mod === "high" ? "🔴" : "🟡";

  const compsHtml = data.components ? Object.entries(data.components).map(([k, c]) => {
    const cm = _rcClass(c.overall_risk?.class);
    return `<div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #edf2f8;">
      <span style="font-size:1.1rem;">${cm==="low"?"🟢":cm==="high"?"🔴":"🟡"}</span>
      <div style="flex:1;">
        <strong style="font-size:.85rem;">${escapeHtml(c.sensor || k)}</strong>
        <span style="font-size:.75rem;color:var(--muted);margin-left:8px;">${(c.overall_risk?.class||"–").toUpperCase()}</span>
      </div>
      ${c.prediction != null ? `<span style="font-size:.82rem;font-weight:600;">${typeof c.prediction==="number"?c.prediction.toFixed(3):c.prediction}</span>` : ""}
    </div>`;
  }).join("") : "";

  return `
    <div class="rc rc--${mod}">
      <div class="rc-header">
        <span class="rc-icon">${icon}</span>
        <div class="rc-header-text">
          <span class="rc-sensor">${escapeHtml(data.submodule || data.module || "Risk")}</span>
          <div class="rc-level">${(overall.class || "–").toUpperCase()} RISK</div>
        </div>
      </div>
      <div class="rc-body">
        ${data.recommended_action ? `<div class="rc-message">${escapeHtml(data.recommended_action)}</div>` : ""}
        ${compsHtml ? `<div style="margin-top:10px;"><strong style="font-size:.8rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);">Components</strong>${compsHtml}</div>` : ""}
      </div>
    </div>`;
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

// ------------------------------
// Coagulation risk rendering — unified .rc design system
// ------------------------------
function renderCoagulationRisk(data, inlineId, fullId) {
  if (!data) return;
  const tl  = data.traffic_light;
  const row = data.risk_table_row;
  if (!tl) return;

  const mod = _rcClass(tl.level);
  const icon = tl.icon || (mod === "low" ? "🟢" : mod === "high" ? "🔴" : "🟡");

  const scoreBadgeMod = (row?.risk_score >= 6) ? "high" : (row?.risk_score >= 3) ? "mod" : "low";

  const cardHtml = `
    <div class="rc rc--${mod}">
      <div class="rc-header">
        <span class="rc-icon">${icon}</span>
        <div class="rc-header-text">
          <span class="rc-sensor">SoSe #8 · Coagulation-Flocculation</span>
          <div class="rc-level">${(tl.level || "low").toUpperCase()} RISK</div>
        </div>
        ${row ? `<span class="rc-score-chip">Score ${row.risk_score}/9</span>` : ""}
      </div>
      <div class="rc-body">
        <div class="rc-value-row">
          <span class="rc-value">${typeof data.prediction === "number" ? data.prediction.toFixed(2) : "–"}</span>
          <span class="rc-unit">NTU</span>
        </div>
        <div class="rc-threshold-hint">
          🟢 0–${tl.thresholds?.low_boundary} NTU &nbsp;·&nbsp; 🟡 ${tl.thresholds?.low_boundary}–${tl.thresholds?.medium_boundary} NTU &nbsp;·&nbsp; 🔴 &gt;${tl.thresholds?.medium_boundary} NTU
        </div>
        <div class="rc-message">${tl.operator_card || data.operator_message || ""}</div>
        ${_rcActions(data.short_term_actions)}
      </div>
      ${row ? _rcFooter([
        ["Likelihood", `${row.likelihood_class} (p=${row.likelihood_p})`],
        ["Severity",   `${row.severity_class} (dev=${row.severity_dev})`],
        ["Risk score", `${row.risk_score} — ${row.risk_class}`],
        ["Threshold",  `${row.threshold} NTU`],
      ]) : ""}
    </div>`;

  const inlineEl = document.getElementById(inlineId);
  if (inlineEl) inlineEl.innerHTML = cardHtml;

  if (!fullId) return;
  const fullEl = document.getElementById(fullId);
  if (!fullEl) return;

  // Build matrix for the full Risk Module view
  const lh = row?.likelihood_num || 1;
  const sv = row?.severity_num   || 1;
  const matBg = [
    ["#00b894","#00b894","#e67e22"],
    ["#00b894","#e67e22","#e74c3c"],
    ["#e67e22","#e74c3c","#e74c3c"],
  ];
  const colLbls = ["Low","Moderate","High"];
  const rowLbls = ["Low","Moderate","High"];

  let matHtml = `
    <div class="rc-matrix-wrap">
      <div class="rc-matrix-title">
        Severity–Likelihood matrix &nbsp;
        <span class="rc-matrix-legend">
          <span style="color:#00b894">■</span> Low &nbsp;
          <span style="color:#e67e22">■</span> Moderate &nbsp;
          <span style="color:#e74c3c">■</span> High &nbsp;|&nbsp;
          T8 = SoSe #8 position
        </span>
      </div>
      <table style="border-collapse:collapse;">
        <tr><th style="font-size:.68rem;color:var(--muted);padding:4px 8px;text-align:right;">Severity ↓&nbsp;/&nbsp;Likelihood →</th>
        ${colLbls.map(l=>`<th style="font-size:.68rem;color:var(--muted);padding:4px 10px;text-align:center;">${l}</th>`).join("")}</tr>
        ${rowLbls.map((rl,r) => `<tr>
          <td style="font-size:.68rem;color:var(--muted);padding:4px 8px;text-align:right;font-weight:600;">${rl}</td>
          ${[0,1,2].map(c => {
            const here = r === sv-1 && c === lh-1;
            return `<td style="width:60px;height:50px;background:${matBg[r][c]};text-align:center;vertical-align:middle;border:2px solid #fff;border-radius:4px;">
              ${here ? `<span style="display:inline-block;background:#fff;color:#222;border-radius:50%;width:26px;height:26px;line-height:26px;font-size:.68rem;font-weight:800;box-shadow:0 2px 8px rgba(0,0,0,.2);">T8</span>` : ""}
            </td>`;
          }).join("")}
        </tr>`).join("")}
      </table>
    </div>`;

  fullEl.innerHTML = cardHtml + matHtml;
}

async function runAutomaticCoagulationRisk(payload) {
  try {
    populateCoagulationRiskForms(payload);
    const data = await postJSON(ENDPOINTS.riskCoagulation, payload);

    state.coagulation.lastRisk = data;

    renderCoagulationRisk(data, "coagulation-risk-output", "risk-coagulation-output");

    const riskClass = data?.traffic_light?.level || data?.overall_risk?.class || "–";
    setBadge("coagulation-risk-badge", `Risk: ${riskClass}`, riskBadgeClass(riskClass));
    updateRiskOverview();
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

  setText("rl5-current-dose-display", current, 2);
  setText("rl5-recommended-dose-display", recommended, 2);
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
  populateRL5RiskForms(payload);
  state.rl5.lastInput = payload;
  state.rl5.lastRisk = null;
  renderStatusCard("rl5-risk-output", "RL #5 advisory status", {
    validation_status: "under validation",
    validation_message: "RL #5 supports mitigation/advisory dosing only and is excluded from risk calculations.",
    validation_todos: ["TODO(Greg): verify ACTION_MAP, unit conversion, and model-output interpretation before final release."]
  });
  renderStatusCard("risk-rl5-output", "RL #5 advisory status", {
    validation_status: "under validation",
    validation_message: "RL #5 is not a risk-producing output and is excluded from system/process risk aggregation.",
  });
  setBadge("rl5-risk-badge", "Advisory: under validation", "moderate");
  updateRiskOverview();
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

// ------------------------------
// Risk design-system helpers
// ------------------------------
const TRAFFIC_COLORS = { green: "#00b894", amber: "#e67e22", red: "#e74c3c" };
const TL_BG          = { green: "#e8faf3", amber: "#fff8ee", red: "#fff0ee" };

// Map backend level strings to CSS modifier class
function _rcClass(level) {
  const l = (level || "").toLowerCase();
  if (l === "critical")              return "critical";
  if (l === "high")                  return "high";
  if (l === "moderate" || l === "medium") return "moderate";
  return "low";
}

// Small utility: build the footer metrics strip
function _rcFooter(items) {
  return `<div class="rc-footer">${items.map(([lbl,val]) =>
    `<div class="rc-metric-cell"><span class="rc-metric-lbl">${lbl}</span><span class="rc-metric-val">${val}</span></div>`
  ).join("")}</div>`;
}

// Build a single action list
function _rcActions(actions) {
  if (!actions?.length) return "";
  return `<ul class="rc-actions">${actions.map(a => `<li>${a}</li>`).join("")}</ul>`;
}

// (colour lookup kept for badge helpers that still use hex values)
function _riskColor(cls) {
  const c = (cls || "").toLowerCase();
  return c === "low" ? TRAFFIC_COLORS.green : (c === "high" || c === "critical") ? TRAFFIC_COLORS.red : TRAFFIC_COLORS.amber;
}

// Two-box dual indicator (inline Bromate card) — unified .rc system
function renderInlineOzonationRisk(data, containerId) {
  const el = document.getElementById(containerId);
  if (!el || !data) return;

  const br = data.bromate_indicator;
  const co = data.coliform_indicator;
  if (!br || !co) return;

  const brMod = _rcClass(br.level);
  const coMod = _rcClass(co.level);
  const ovMod = _rcClass(data.overall_risk?.class);

  el.innerHTML = `
    <div class="rc-duo">
      <div class="rc-duo-card rc-duo--${brMod}">
        <div class="rc-duo-header">${br.icon} Bromate Risk · SoSe #10.1</div>
        <div class="rc-duo-body">
          <div class="rc-duo-level">${br.level.toUpperCase()}</div>
          <div class="rc-duo-value">${br.value.toFixed(2)} ${br.unit}</div>
          <div style="font-size:.68rem;color:var(--muted);margin-bottom:6px;">
            &lt;${br.thresholds.low_boundary} low · ${br.thresholds.low_boundary}–${br.thresholds.high_boundary} moderate · &gt;${br.thresholds.high_boundary} high
            ${br.guideline ? `<br>${br.guideline}` : ""}
          </div>
          <div class="rc-duo-msg">${br.message || ""}</div>
        </div>
      </div>

      <div class="rc-duo-card rc-duo--${coMod}">
        <div class="rc-duo-header">${co.icon} Microbial removal risk</div>
        <div class="rc-duo-body">
          <div class="rc-duo-level">${co.level.toUpperCase()}</div>
          <div class="rc-duo-value">${co.value.toFixed(3)} ${co.unit}</div>
          <div style="font-size:.68rem;color:var(--muted);margin-bottom:6px;">
            &gt;${co.thresholds.low_boundary} low · ${co.thresholds.moderate_boundary}–${co.thresholds.low_boundary} moderate · &lt;${co.thresholds.moderate_boundary} high
          </div>
          <div class="rc-duo-msg">${co.message || ""}</div>
        </div>
      </div>
    </div>

    <div class="rc-combined rc-combined--${ovMod}">
      <strong>Overall ozonation risk: ${(data.overall_risk?.class || "").toUpperCase()}
        ${data.trade_off_detected ? '<span class="rc-trade-off-badge">⚠ TRADE-OFF</span>' : ""}
      </strong><br>
      ${data.combined_message || ""}
      ${_rcActions(data.short_term_actions)}
    </div>`;
}

// Prioritized risk table — unified rc-table classes
function renderRiskTable(containerId, data) {
  const el = document.getElementById(containerId);
  if (!el || !data?.risk_table) return;

  const rows = data.risk_table.map(r => {
    const sMod = r.risk_score >= 6 ? "high" : r.risk_score >= 3 ? "mod" : "low";
    const tlMod = _rcClass(r.traffic_light);
    return `<tr>
      <td>${r.hazard}</td>
      <td class="right"><strong>${r.predicted_value}</strong> ${r.unit}</td>
      <td class="right">${r.threshold} ${r.unit}</td>
      <td class="center">${r.likelihood_class}<br><small style="color:var(--muted)">p=${r.likelihood_p}</small></td>
      <td class="center">${r.severity_class}<br><small style="color:var(--muted)">dev=${r.severity_dev}</small></td>
      <td class="center"><span class="rc-score-badge rc-score-badge--${sMod}">${r.risk_score}</span></td>
      <td class="center"><span class="rc-score-badge rc-score-badge--${sMod}">${(r.risk_class||"").toUpperCase()}</span></td>
      <td style="font-size:.78rem;">${r.mitigation}</td>
    </tr>`;
  }).join("");

  el.innerHTML = `
    <table class="rc-table">
      <thead><tr>
        <th>Hazard</th><th class="right">Predicted</th><th class="right">Threshold</th>
        <th class="center">Likelihood</th><th class="center">Severity</th>
        <th class="center">Score L×S</th><th class="center">Risk class</th>
        <th>Mitigation</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <div style="margin-top:6px;font-size:.7rem;color:var(--muted);">
      Score = Likelihood × Severity (1–9). ${data.severity_likelihood_matrix?.score_formula || ""}
    </div>`;
}

// Severity-likelihood matrix — unified style
function renderSeverityMatrix(containerId, data) {
  const el = document.getElementById(containerId);
  if (!el || !data?.severity_likelihood_matrix) return;
  const m = data.severity_likelihood_matrix;

  const matBg = [
    ["#00b894","#00b894","#e67e22"],
    ["#00b894","#e67e22","#e74c3c"],
    ["#e67e22","#e74c3c","#e74c3c"],
  ];
  const colLbls = ["Low","Moderate","High"];
  const rowLbls = ["Low","Moderate","High"];

  const points = {
    bromate:  { r: m.bromate.severity-1,  c: m.bromate.likelihood-1,  label: "B" },
    ct:       { r: m.ct.severity-1,       c: m.ct.likelihood-1,       label: "CT" },
    coliform: { r: m.coliform.severity-1, c: m.coliform.likelihood-1, label: "M" },
  };

  const header = `<tr>
    <th style="font-size:.68rem;color:var(--muted);padding:4px 8px;text-align:right;font-weight:500;">Severity ↓ / Likelihood →</th>
    ${colLbls.map(l=>`<th style="font-size:.68rem;color:var(--muted);padding:4px 10px;text-align:center;">${l}</th>`).join("")}
  </tr>`;

  const body = rowLbls.map((rl,r) => `<tr>
    <td style="font-size:.68rem;color:var(--muted);padding:4px 8px;text-align:right;font-weight:600;">${rl}</td>
    ${[0,1,2].map(c => {
      const marks = Object.values(points).filter(p=>p.r===r&&p.c===c)
        .map(p=>`<span style="display:inline-block;background:#fff;color:#222;border-radius:50%;width:26px;height:26px;line-height:26px;font-size:.65rem;font-weight:800;box-shadow:0 2px 6px rgba(0,0,0,.15);margin:1px;">${p.label}</span>`).join("");
      return `<td style="width:64px;height:52px;background:${matBg[r][c]};text-align:center;vertical-align:middle;border:2px solid #fff;border-radius:3px;">${marks}</td>`;
    }).join("")}
  </tr>`).join("");

  el.innerHTML = `
    <div class="rc-matrix-wrap">
      <div class="rc-matrix-title">
        Severity–Likelihood Matrix
        <span class="rc-matrix-legend">
          <span style="color:#00b894">■</span> Low &nbsp;
          <span style="color:#e67e22">■</span> Moderate &nbsp;
          <span style="color:#e74c3c">■</span> High &nbsp;|&nbsp;
          B=Bromate &nbsp; CT=CT &nbsp; M=Microbial removal
        </span>
      </div>
      <table style="border-collapse:collapse;">${header}${body}</table>
      ${m.scale_likelihood ? `<div style="font-size:.68rem;color:var(--muted);margin-top:5px;">${m.scale_likelihood}<br>${m.scale_severity}</div>` : ""}
    </div>`;
}

function renderOzonationOperational(data, inlineId, fullId) {
  if (!data) return;
  renderInlineOzonationRisk(data, inlineId);
  if (!fullId) return;

  const ovMod = _rcClass(data.overall_risk?.class);
  const msgEl = document.getElementById(`${fullId}-message`);
  if (msgEl) {
    msgEl.innerHTML = `
      <div class="rc-combined rc-combined--${ovMod}">
        <strong>Overall ozonation risk: ${(data.overall_risk?.class||"").toUpperCase()}
          ${data.trade_off_detected ? '<span class="rc-trade-off-badge">&#9888; CRITICAL TRADE-OFF</span>' : ""}
        </strong><br>
        ${data.combined_message || ""}
        ${_rcActions(data.short_term_actions)}
      </div>`;
  }
  renderRiskTable(`${fullId}-table`, data);
  renderSeverityMatrix(`${fullId}-matrix`, data);
}

// ------------------------------
// Risk Overview — auto-populated grid from stored state
// ------------------------------
// ------------------------------
// Live Process-Flow Diagram + Intervention Decision Tree
// ------------------------------
const COAG_LOW = 6, COAG_HIGH = 9;
const BROMATE_TH_LOW = 5, BROMATE_TH_HIGH = 10;
const COLIFORM_TH_LOW = 0.85, COLIFORM_TH_HIGH = 1.2;
const CT_TH = 0.7;

function _levelFromValue(val, thresholds) {
  // thresholds: {low, high} — below low = low, between = moderate, above high = high
  // For "higher is better" invert with thresholds.invert = true
  if (val == null) return null;
  if (thresholds.invert) {
    return val > thresholds.high ? "low" : val >= thresholds.low ? "moderate" : "high";
  }
  return val <= thresholds.low ? "low" : val <= thresholds.high ? "moderate" : "high";
}

function setFlowNode(id, level, value, unit) {
  const node  = document.getElementById(id);
  const valEl = document.getElementById(`${id}-val`);
  const badge = document.getElementById(`${id}-badge`);
  if (!node) return;
  const mod = _rcClass(level || "pending");
  node.classList.remove("flow--low","flow--moderate","flow--high","flow--pending");
  node.classList.add(level ? `flow--${mod}` : "flow--pending");
  if (valEl && value != null)
    valEl.textContent = (typeof value === "number" ? value.toFixed(2) : value) + (unit ? ` ${unit}` : "");
  if (badge)
    badge.textContent = (level ? (level === "low" ? "✓ OK" : level.toUpperCase()) : "Pending");
}

function updateDecisionTree() {
  const rank = l => (l==="high"||l==="critical") ? 3 : (l==="moderate"||l==="medium") ? 2 : l === "low" ? 1 : 0;
  const levels = [];

  // ── Source / SoSe #9 ───────────────────────────────────
  const sourceRisk = state.source.lastRisk;
  const sourcePred = state.source.lastPrediction;
  const sourceLevel = sourceRisk?.overall_risk?.class || null;
  setFlowNode("flow-source", sourceLevel, sourcePred, "FTU");
  if (sourceLevel) levels.push(sourceLevel);

  // ── Coagulation ──────────────────────────────────────────
  const coagPred = state.coagulation.lastPrediction;
  const coagLevel = coagPred != null
    ? _levelFromValue(coagPred, {low: COAG_LOW, high: COAG_HIGH})
    : (state.coagulation.lastRisk?.traffic_light?.level || null);
  setFlowNode("flow-coag", coagLevel, coagPred, "NTU");
  if (coagLevel) levels.push(coagLevel);

  const rlData = null;
  setFlowNode("flow-rl", "low", state.rl5.lastInput?.recommended_fecl3_dose, "mg/L advisory");

  // ── CT (SoSe #10) ────────────────────────────────────────
  const ctPred = state.ozonation.ctPrediction;
  const ctLevel = ctPred != null
    ? _levelFromValue(ctPred, {low: CT_TH, high: CT_TH + 0.3, invert: true})
    : (state.ozonation.operationalRisk?.ct_indicator?.level || null);
  setFlowNode("flow-ct", ctLevel, ctPred, "mg/L·min");
  if (ctLevel) levels.push(ctLevel);

  // ── Bromate (SoSe #10.1) ─────────────────────────────────
  const brPred = state.ozonation.bromatePrediction;
  const brLevel = brPred != null
    ? _levelFromValue(brPred, {low: BROMATE_TH_LOW, high: BROMATE_TH_HIGH})
    : (state.ozonation.operationalRisk?.bromate_indicator?.level || null);
  setFlowNode("flow-bromate", brLevel, brPred, "µg/L");
  if (brLevel) levels.push(brLevel);

  // ── Coliform (SoSe #10.2) ────────────────────────────────
  const colPred = state.ozonation.coliformPrediction;
  const colLevel = colPred != null
    ? _levelFromValue(colPred, {low: COLIFORM_TH_LOW, high: COLIFORM_TH_HIGH, invert: true})
    : (state.ozonation.operationalRisk?.coliform_indicator?.level || null);
  setFlowNode("flow-coliform", colLevel, colPred, "log removal");
  if (colLevel) levels.push(colLevel);

  // ── Distribution / SoSe #11 ─────────────────────────────
  const distRisk = state.distribution.lastRisk;
  const distPred = distRisk?.prediction;
  const distLevel = distRisk?.overall_risk?.class || null;
  setFlowNode("flow-dist", distLevel, distPred, "probability");
  if (distLevel) levels.push(distLevel);

  // ── Overall system node ───────────────────────────────────
  if (levels.length) {
    const systemLevel = levels.reduce((w, l) => rank(l) > rank(w) ? l : w, "low");
    setFlowNode("flow-system", systemLevel, null, null);
    const sysVal = document.getElementById("flow-system-val");
    if (sysVal) sysVal.textContent = `${levels.length} sensor${levels.length>1?"s":""} active`;
  }

  // ── Intervention pathway support ──────────────────────────
  updateInterventionTree(coagLevel, brLevel, colLevel, ctLevel, rlData);
  updateRiskDashboard();
}

function updateInterventionTree(coagLevel, brLevel, colLevel, ctLevel, rlData) {
  const rlLevel = null;

  function setDt(id, level, value, unit, message) {
    const el = document.getElementById(id);
    if (!el) return;
    const mod = _rcClass(level || "pending");
    el.className = el.className.replace(/dt--\w+/g, "").trim() + ` dt--${mod}`;
    const valEl = el.querySelector(".dt-val");
    const msgEl = el.querySelector(".dt-msg");
    if (valEl && value != null)
      valEl.textContent = (typeof value === "number" ? value.toFixed(2) : value) + (unit ? ` ${unit}` : "");
    if (msgEl && message) msgEl.textContent = message;
  }

  function showAction(id, show, message) {
    const el = document.getElementById(id);
    if (!el) return;
    el.style.display = show ? "block" : "none";
    if (message) {
      const m = el.querySelector(".dt-action-msg");
      if (m) m.textContent = message;
    }
  }

  const coagPred = state.coagulation.lastPrediction;
  const brPred   = state.ozonation.bromatePrediction;
  const colPred  = state.ozonation.coliformPrediction;
  const ctPred   = state.ozonation.ctPrediction;
  const rlRec    = state.rl5.lastInput?.recommended_fecl3_dose;

  // Treatment check
  setDt("dt-treatment-check", coagLevel,
    coagPred, "NTU",
    coagPred != null ? `Outlet turbidity: ${coagPred.toFixed(2)} NTU (limit: ${COAG_LOW} NTU)` : null);
  showAction("dt-action-coag", coagLevel === "moderate" || coagLevel === "high",
    rlRec != null ? `Adjust FeCl₃ dose. RL #5 recommends ${rlRec.toFixed(2)} mg/L.` : "Adjust FeCl₃ dosage. Check flocculation.");

  // Ozonation check — use worst of bromate/coliform/ct
  const rank = l => l==="high"?3:l==="moderate"?2:l==="low"?1:0;
  const ozLevels = [brLevel, colLevel, ctLevel].filter(Boolean);
  const ozWorst = ozLevels.length ? ozLevels.reduce((w,l)=>rank(l)>rank(w)?l:w,"low") : null;
  setDt("dt-ozonation-check", ozWorst,
    null, null,
    (() => {
      if (!ozLevels.length) return null;
      const parts = [];
      if (brPred != null) parts.push(`Bromate: ${brPred.toFixed(2)} µg/L`);
      if (ctPred != null) parts.push(`CT: ${ctPred.toFixed(3)} mg/L·min`);
      if (colPred != null) parts.push(`Microbial log-removal: ${colPred.toFixed(3)}`);
      return parts.join(" · ");
    })());

  // Trade-off
  const tradeOff = brLevel === "high" && colLevel === "high";
  showAction("dt-action-ozon-tradeoff", tradeOff,
    "TRADE-OFF: Bromate is high and disinfection is insufficient. Do not change ozone dose automatically. Escalate to operator review.");
  showAction("dt-action-ozon-bromate", !tradeOff && brLevel === "high",
    `Bromate ${brPred?.toFixed(2)} µg/L exceeds EU limit (10 µg/L). Optimise ozone dose, check bromide/pH/temperature.`);
  showAction("dt-action-ozon-coliform", !tradeOff && colLevel === "high",
    `Microbial log-removal ${colPred?.toFixed(3)} is insufficient (<0.85). Improve CT/disinfection only after bromate review.`);
  showAction("dt-action-ozon-ok", !tradeOff && ozLevels.length > 0 && ozWorst === "low", null);

  // ── Update all decision oval nodes ─────────────────────
  function setOval(id, level, val, unit) {
    const el = document.getElementById(id);
    if (!el) return;
    el.className = "dt-oval" + (level ? ` dt--${_rcClass(level)}` : " dt--pending");
    const v = el.querySelector(".dt-val");
    if (v && val != null)
      v.textContent = (typeof val === "number" ? val.toFixed(2) : val) + (unit ? ` ${unit}` : "");
  }

  setOval("dt-treatment-check", coagLevel, coagPred, "NTU");
  const ozWorst2 = ozLevels.length ? ozLevels.reduce((w,l)=>rank(l)>rank(w)?l:w,"low") : null;
  setOval("dt-ozonation-check", ozWorst2,
    brPred != null && ctPred != null ? `Br ${brPred.toFixed(1)} µg/L · CT ${ctPred.toFixed(2)} · Col ${colPred?.toFixed(2)}` : null, "");

  // ── Customer node ─────────────────────────────────────
  const allLevels = [coagLevel, brLevel, colLevel, ctLevel].filter(Boolean);
  const customerLevel = allLevels.length ? allLevels.reduce((w,l)=>rank(l)>rank(w)?l:w,"low") : null;
  const customerEl = document.getElementById("dt-customer");
  const customerMsg = document.getElementById("dt-customer-msg");
  if (customerEl && customerLevel) {
    customerEl.className = `dt-final dt--${_rcClass(customerLevel)}`;
    if (customerMsg) {
      customerMsg.textContent = customerLevel === "low"
        ? "&#10003; All parameters within operational limits. Safe water delivery."
        : customerLevel === "moderate"
        ? "&#9888; Monitor closely. Some parameters in warning zone."
        : "&#128308; Immediate attention required. See intervention recommendations.";
    }
  }
}

function updateRiskOverview() {
  const grid  = document.getElementById("risk-overview-grid");
  const matEl = document.getElementById("risk-overview-matrix");
  if (!grid) {
    updateRiskDashboard();
    return;
  }

  const entries = [];

  if (state.source.lastRisk)
    entries.push({ key:"source", label:"Inlet turbidity", data: state.source.lastRisk });
  if (state.coagulation.lastRisk)
    entries.push({ key:"coag", label:"Outlet turbidity after coagulation/sedimentation", data: state.coagulation.lastRisk });
  if (state.ozonation.operationalRisk) {
    const op = state.ozonation.operationalRisk;
    if (op.bromate_indicator)  entries.push({ key:"br",  label:"Bromate",  data: _opIndicatorToRisk(op.bromate_indicator,  "Bromate") });
    if (op.ct_indicator)       entries.push({ key:"ct",  label:"CT",       data: _opIndicatorToRisk(op.ct_indicator,       "CT") });
    if (op.coliform_indicator) entries.push({ key:"col", label:"Microbial removal",  data: _opIndicatorToRisk(op.coliform_indicator, "Microbial removal") });
  }
  if (state.distribution.lastRisk)
    entries.push({ key:"dist", label:"SoSe #11 &middot; Distribution", data: state.distribution.lastRisk });

  if (!entries.length) {
    grid.innerHTML = `<article class="panel risk-overview-placeholder">No active sensor risk assessments are available yet.</article>`;
    updateRiskDashboard();
    return;
  }

  grid.innerHTML = entries.map(e => {
    const mod  = _rcClass(e.data.overall_risk?.class || e.data.level);
    const icon = mod === "low" ? "&#128994;" : mod === "high" ? "&#128308;" : "&#128993;";
    const val  = e.data.prediction ?? e.data.value;
    const unit = e.data.unit || "";
    const msg  = e.data.operator_message || e.data.message || e.data.recommended_action || "";
    return `
      <div class="rc rc--${mod}">
        <div class="rc-header">
          <span class="rc-icon">${icon}</span>
          <div class="rc-header-text">
            <span class="rc-sensor">${e.label}</span>
            <div class="rc-level">${((e.data.overall_risk?.class || e.data.level || "")).toUpperCase()} RISK</div>
          </div>
        </div>
        <div class="rc-body">
          ${val != null ? `<div class="rc-value-row"><span class="rc-value">${typeof val==="number"?val.toFixed(3):val}</span>${unit?`<span class="rc-unit">${unit}</span>`:""}</div>` : ""}
          ${msg ? `<div class="rc-message">${escapeHtml(msg)}</div>` : ""}
          ${_rcActions((e.data.short_term_actions||[]).slice(0,3))}
        </div>
      </div>`;
  }).join("");

  // Combined overview matrix
  if (matEl) {
    const points = entries.map(e => ({
      label: e.label.replace(/&[^;]+;/g,"").replace("·","·").trim().split("·")[0].trim(),
      lh: e.data.likelihood?.score ?? 1,
      sv: e.data.severity?.score   ?? 1,
    }));
    matEl.innerHTML = _buildOverviewMatrix(points);
  }

  // ── Dedicated full-card panels in Risk Overview ───────
  // Coagulation: full rc-card WITH matrix (same id = card + matrix rendered together)
  if (state.coagulation.lastRisk)
    renderCoagulationRisk(state.coagulation.lastRisk, "risk-overview-coag", "risk-overview-coag");

  // Ozonation: full inline dual-indicator card
  if (state.ozonation.operationalRisk)
    renderInlineOzonationRisk(state.ozonation.operationalRisk, "risk-overview-ozon");

  updateRiskTables();
  updateDecisionTree();
  updateRiskDashboard();
}

function _opIndicatorToRisk(ind, sensor) {
  const score = ind.level === "high" ? 3 : ind.level === "moderate" ? 2 : 1;
  return {
    overall_risk: { class: ind.level, score },
    level: ind.level,
    prediction: ind.value,
    unit: ind.unit,
    operator_message: ind.message,
    short_term_actions: [],
    sensor,
    likelihood: { score },
    severity:   { score },
  };
}

function _buildOverviewMatrix(points) {
  const matBg = [
    ["#00b894","#00b894","#e67e22"],
    ["#00b894","#e67e22","#e74c3c"],
    ["#e67e22","#e74c3c","#e74c3c"],
  ];
  const lbLs = ["Low","Moderate","High"];
  let cellData = Array.from({length:3},()=>Array.from({length:3},()=>[]));
  points.forEach(p => {
    const r = Math.min(Math.max((p.sv||1)-1,0),2);
    const c = Math.min(Math.max((p.lh||1)-1,0),2);
    cellData[r][c].push(p.label);
  });
  const header = `<tr><th style="font-size:.72rem;color:var(--muted);padding:4px 8px;font-weight:500;text-align:right;">Severity &#8595; / Likelihood &#8594;</th>
    ${lbLs.map(l=>`<th style="font-size:.72rem;color:var(--muted);padding:4px 12px;text-align:center;">${l}</th>`).join("")}</tr>`;
  const body = lbLs.map((rl,r)=>`<tr>
    <td style="font-size:.72rem;color:var(--muted);padding:4px 8px;text-align:right;font-weight:600;">${rl}</td>
    ${[0,1,2].map(c=>{
      const chips = cellData[r][c].map(n=>`<span style="display:inline-block;background:#fff;color:#222;border-radius:999px;padding:2px 7px;font-size:.62rem;font-weight:700;box-shadow:0 1px 4px rgba(0,0,0,.2);margin:2px;">${n}</span>`).join("");
      return `<td style="min-width:110px;min-height:56px;background:${matBg[r][c]};text-align:center;vertical-align:middle;border:2px solid #fff;border-radius:4px;padding:6px;">${chips}</td>`;
    }).join("")}
  </tr>`).join("");
  return `<table style="border-collapse:collapse;width:100%;">${header}${body}</table>
    <p class="muted-hint" style="margin-top:6px;">Each chip = one sensor. Likelihood = P(exceeds threshold). Severity = consequence of deviation.</p>`;
}

function _riskLevelText(level) {
  const mod = _rcClass(level);
  if (mod === "high") return "High";
  if (mod === "moderate") return "Moderate";
  if (mod === "critical") return "High";
  if (mod === "low") return "Low";
  return "Pending";
}

function _riskTimestamp(ts) {
  if (!ts) return "latest available";
  try {
    return new Date(ts).toLocaleString([], {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit"
    });
  } catch (_) {
    return ts;
  }
}

function _formatRiskValue(value, unit, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return "No prediction available";
  const shown = typeof value === "number" ? value.toFixed(digits) : value;
  return unit ? `${shown} ${unit}` : String(shown);
}

function _maxRiskLevel(levels) {
  const rank = l => {
    const mod = _rcClass(l);
    if (mod === "high" || mod === "critical") return 3;
    if (mod === "moderate") return 2;
    if (mod === "low") return 1;
    return 0;
  };
  return levels.filter(Boolean).reduce((worst, item) => rank(item) > rank(worst) ? item : worst, "Low");
}

function _riskDashboardEntries() {
  const nowLabel = "live dashboard";
  const entries = [];

  const source = state.source.lastRisk;
  entries.push({
    id: "source",
    short: "SoSe #9",
    title: "Inlet Turbidity Prediction — SoSe #9",
    processName: "Source Monitoring — SoSe #9",
    predictionLabel: "Predicted Turbidity",
    prediction: state.source.lastPrediction,
    unit: "FTU",
    threshold: "Reference percentiles 2022-2024: P5 7.8; P50 15; P90 23; P95 28 FTU. 20 FTU = attention line.",
    risk: source?.overall_risk?.class || "Low",
    reason: source?.operator_message || "Predicted inlet turbidity is below 15 FTU and within the acceptable inlet range.",
    implication: _rcClass(source?.overall_risk?.class) === "high"
      ? "Persistent source-water turbidity can increase coagulation demand and downstream filter loading."
      : _rcClass(source?.overall_risk?.class) === "moderate"
      ? "Increased coagulation demand may be expected if the forecast continues to rise."
      : "Source-water quality is not currently driving operational concern.",
    action: source?.short_term_actions?.[0] || "Continue routine monitoring of raw water quality.",
    likelihood: source?.likelihood?.score || 1,
    severity: source?.severity?.score || 1,
    timestamp: _riskTimestamp(state.source.lastTimestamp),
  });

  const coag = state.coagulation.lastRisk;
  entries.push({
    id: "coag",
    short: "SoSe #8",
    title: "Outlet Turbidity After Coagulation/Sedimentation — SoSe #8",
    processName: "Coagulation, Flocculation and Sedimentation — SoSe #8",
    predictionLabel: "Predicted Outlet Turbidity",
    prediction: state.coagulation.lastPrediction ?? coag?.prediction,
    unit: "NTU",
    threshold: "Low <=6 NTU; Moderate 6-9 NTU; High >9 NTU",
    risk: coag?.overall_risk?.class || coag?.traffic_light?.level || "Low",
    reason: coag?.operator_message || "Coagulation outlet turbidity is within the current operational target.",
    implication: _rcClass(coag?.overall_risk?.class || coag?.traffic_light?.level) === "high"
      ? "High outlet turbidity may increase filtration stress and requires immediate process review."
      : _rcClass(coag?.overall_risk?.class || coag?.traffic_light?.level) === "moderate"
      ? "Treatment performance is in a warning zone; filter loading may increase."
      : "Coagulation is not currently increasing downstream risk.",
    action: coag?.short_term_actions?.[0] || "Maintain routine turbidity and filter-performance monitoring.",
    likelihood: coag?.likelihood?.score || coag?.risk_table_row?.likelihood_num || 1,
    severity: coag?.severity?.score || coag?.risk_table_row?.severity_num || 1,
    timestamp: nowLabel,
  });

  const oz = state.ozonation.operationalRisk;
  const ozRisk = oz?.overall_risk?.class || "Low";
  entries.push({
    id: "oz",
    short: "SoSe #10",
    title: "Ozonation Decision Support — SoSe #10 / #10.1 / #10.2",
    processName: "Ozonation — SoSe #10 / #10.1 / #10.2",
    predictionLabel: "CT / Bromate / Microbial removal",
    prediction: null,
    unit: "",
    displayPrediction: [
      `CT ${_formatRiskValue(state.ozonation.ctPrediction, "mg*min/L", 3)}`,
      `Bromate ${_formatRiskValue(state.ozonation.bromatePrediction, "ug/L", 3)}`,
      `Microbial removal ${_formatRiskValue(state.ozonation.coliformPrediction, "log removal", 3)}`
    ].join(" | "),
    threshold: "CT adequacy must be validated; Bromate <5 low, 5-10 moderate, >=10 ug/L high; microbial removal >1.2 adequate",
    risk: ozRisk,
    reason: oz?.combined_message || "Ozonation indicators are not currently showing an elevated operational trade-off.",
    implication: _rcClass(ozRisk) === "high"
      ? "Ozonation risk may indicate bromate formation, insufficient disinfection, or an operational trade-off."
      : _rcClass(ozRisk) === "moderate"
      ? "Ozonation conditions require closer monitoring before intervention."
      : "Ozonation is not currently driving system risk.",
    action: oz?.short_term_actions?.[0] || "Maintain routine monitoring of ozone residual, bromate, and microbial removal.",
    likelihood: Math.max(
      oz?.severity_likelihood_matrix?.bromate?.likelihood || 1,
      oz?.severity_likelihood_matrix?.ct?.likelihood || 1,
      oz?.severity_likelihood_matrix?.coliform?.likelihood || 1
    ),
    severity: Math.max(
      oz?.severity_likelihood_matrix?.bromate?.severity || 1,
      oz?.severity_likelihood_matrix?.ct?.severity || 1,
      oz?.severity_likelihood_matrix?.coliform?.severity || 1
    ),
    timestamp: nowLabel,
  });

  const dist = state.distribution.lastRisk;
  entries.push({
    id: "dist",
    short: "SoSe #11",
    title: "SoSe #11 - Distribution Risk",
    processName: "Distribution — SoSe #11",
    predictionLabel: "Aeromonas Prediction",
    prediction: dist?.prediction,
    unit: "probability",
    threshold: "Aeromonas probability and biological instability indicators",
    risk: dist?.overall_risk?.class || "Low",
    reason: dist?.operator_message || "Distribution biological instability indicators are not currently elevated.",
    implication: _rcClass(dist?.overall_risk?.class) === "high"
      ? "Distribution conditions may increase Aeromonas occurrence and downstream health risk."
      : _rcClass(dist?.overall_risk?.class) === "moderate"
      ? "Distribution conditions should be watched for biological instability."
      : "Distribution is not currently driving source-to-tap risk.",
    action: dist?.short_term_actions?.[0] || "Maintain routine distribution monitoring.",
    likelihood: dist?.likelihood?.score || 1,
    severity: dist?.severity?.score || 1,
    timestamp: nowLabel,
  });

  return entries;
}

function updateRiskDashboard() {
  renderRiskDashboardFlow();
  renderRiskDashboardCards();
  renderRiskDashboardMatrix();
  renderRiskDashboardPathway();
}

function renderRiskDashboardFlow() {
  const el = document.getElementById("risk-dashboard-flow");
  if (!el) return;
  const entries = _riskDashboardEntries();
  const flowEntries = entries.filter(e => e.id !== "rl5");
  const activeLevels = entries
    .filter(e => e.prediction !== null && e.prediction !== undefined || e.displayPrediction)
    .map(e => e.risk);
  const systemRisk = _maxRiskLevel(activeLevels);
  const nodes = [
    { stage: "Intake", name: "Raw Water", risk: "Low", value: "Source-water intake", timestamp: "live dashboard" },
    ...flowEntries.map(e => ({
      stage: e.short,
      name: e.processName,
      risk: e.risk,
      value: `${e.predictionLabel}: ${e.displayPrediction || _formatRiskValue(e.prediction, e.unit, e.id === "source" ? 3 : 2)}`,
      timestamp: e.timestamp,
    })),
    { stage: "Decision", name: "Risk Assessment", risk: systemRisk, value: `Overall: ${_riskLevelText(systemRisk)} Risk`, timestamp: "live dashboard" },
    { stage: "Outcome", name: "Safe Drinking Water", risk: systemRisk, value: _rcClass(systemRisk) === "high" ? "Intervention required before confidence is restored" : "Operationally acceptable", timestamp: "live dashboard" },
  ];

  el.innerHTML = nodes.map(node => {
    const mod = _rcClass(node.risk);
    return `<div class="risk-chain-node risk-node--${mod}">
      <div class="risk-chain-stage">${escapeHtml(node.stage)}</div>
      <div class="risk-chain-name">${escapeHtml(node.name)}</div>
      <div class="risk-chain-risk">Risk: ${escapeHtml(_riskLevelText(node.risk))}</div>
      <div class="risk-chain-value">${escapeHtml(node.value)}</div>
      <div class="risk-chain-time">Timestamp: ${escapeHtml(node.timestamp)}</div>
    </div>`;
  }).join("");
}

function renderRiskDashboardCards() {
  const el = document.getElementById("risk-dashboard-cards");
  if (!el) return;
  const entries = _riskDashboardEntries();

  el.innerHTML = entries.map(e => {
    const mod = _rcClass(e.risk);
    return `<article class="risk-summary-card risk-node--${mod}">
      <h5>${escapeHtml(e.title)}</h5>
      <div class="risk-summary-row"><span>Prediction</span><strong>${escapeHtml(e.displayPrediction || _formatRiskValue(e.prediction, e.unit, e.id === "source" ? 3 : 2))}</strong></div>
      <div class="risk-summary-row"><span>Risk</span><strong>${escapeHtml(_riskLevelText(e.risk))}</strong></div>
      <div class="risk-summary-row"><span>Threshold used</span><strong>${escapeHtml(e.threshold)}</strong></div>
      <div class="risk-summary-row"><span>Reason</span><strong>${escapeHtml(e.reason)}</strong></div>
      <div class="risk-summary-row"><span>Operational implication</span><strong>${escapeHtml(e.implication)}</strong></div>
      <div class="risk-summary-row"><span>Recommended action</span><strong>${escapeHtml(e.action)}</strong></div>
    </article>`;
  }).join("");
}

function _toFivePointScore(value, risk) {
  if (value >= 4) return Math.min(value, 5);
  const mod = _rcClass(risk);
  if (mod === "high") return 5;
  if (mod === "moderate") return 3;
  return Math.max(1, value || 1);
}

function renderRiskDashboardMatrix() {
  const el = document.getElementById("risk-dashboard-matrix");
  if (!el) return;
  const entries = _riskDashboardEntries();
  const cellData = Array.from({ length: 5 }, () => Array.from({ length: 5 }, () => []));

  entries.forEach(e => {
    const likelihood = _toFivePointScore(e.likelihood, e.risk);
    const severity = _toFivePointScore(e.severity, e.risk);
    const row = 5 - severity;
    const col = likelihood - 1;
    cellData[row][col].push(e);
  });

  const likelihoodLabels = ["1 Very unlikely", "2 Unlikely", "3 Possible", "4 Likely", "5 Almost certain"];
  const severityLabels = ["5 Critical", "4 Major", "3 Moderate", "2 Low", "1 Low"];

  const rows = cellData.map((rowCells, r) => `<tr>
    <th>${severityLabels[r]}</th>
    ${rowCells.map((items, c) => {
      const score = (5 - r) * (c + 1);
      const cls = score >= 15 ? "matrix--high" : score >= 6 ? "matrix--medium" : "";
      return `<td class="risk-matrix-cell ${cls}">
        ${items.map(item => `<span class="risk-marker risk-node--${_rcClass(item.risk)}">${escapeHtml(item.short)}</span>`).join("")}
      </td>`;
    }).join("")}
  </tr>`).join("");

  el.innerHTML = `<div class="risk-matrix-wrap">
    <table class="risk-matrix-table">
      <thead>
        <tr>
          <th>Severity / Likelihood</th>
          ${likelihoodLabels.map(label => `<th>${escapeHtml(label)}</th>`).join("")}
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
    <p class="muted-hint">Markers move automatically as each sensor risk assessment updates. Green = Low, yellow = Moderate, red = High.</p>
  </div>`;
}

function renderRiskDashboardPathway() {
  const el = document.getElementById("risk-dashboard-pathway");
  if (!el) return;
  const entries = _riskDashboardEntries();
  const elevated = entries.filter(e => _rcClass(e.risk) !== "low");
  const branches = [];

  const addBranch = (level, title, steps) => {
    branches.push({ level, title, steps });
  };

  const source = entries.find(e => e.id === "source");
  if (_rcClass(source?.risk) === "high") {
    addBranch("high", "Short-term intervention pathway - inlet turbidity trend", [
      "Investigate persistent source-water turbidity trend",
      "Check coagulation readiness and source-water conditions",
      "Review downstream operational pressure"
    ]);
  } else if (_rcClass(source?.risk) === "moderate") {
    addBranch("moderate", "Short-term intervention pathway - inlet turbidity attention", [
      "Watch P90/P95 reference-band position",
      "Check coagulation readiness",
      "Review source-water conditions"
    ]);
  }

  const oz = state.ozonation.operationalRisk;
  const bromateLevel = oz?.bromate_indicator?.level;
  if (_rcClass(bromateLevel) === "high") {
    addBranch("high", "Short-term intervention pathway - bromate", [
      "Review/reduce ozone dose only where disinfection requirements allow",
      "Review bromide concentration, pH, water temperature, and contact time",
      "Escalate to operator/process review"
    ]);
  }

  const coag = entries.find(e => e.id === "coag");
  if (_rcClass(coag?.risk) === "high") {
    addBranch("high", "Short-term intervention pathway - outlet turbidity", [
      "Check FeCl3 dosage",
      "Check pH",
      "Check temperature",
      "Check flow conditions",
      "Monitor filters/backwashing and inspect mixing/flocculation"
    ]);
  } else if (_rcClass(coag?.risk) === "moderate") {
    addBranch("moderate", "Short-term intervention pathway - coagulation attention", [
      "Review FeCl3 dosage",
      "Consult RL #5 only as advisory dosing support",
      "Verify mixing conditions",
      "Increase turbidity monitoring",
      "Watch downstream filter loading"
    ]);
  }

  const dist = entries.find(e => e.id === "dist");
  if (_rcClass(dist?.risk) !== "low") {
    addBranch(dist.risk, "Short-term intervention pathway - distribution", [
      "Check residual disinfectant",
      "Review warm-water and stagnation indicators",
      "Inspect sensitive network zones",
      "Increase Aeromonas monitoring"
    ]);
  }

  if (!branches.length) {
    addBranch("low", "Short-term intervention pathway", [
      "Continue routine monitoring",
      "Keep soft-sensor dashboard active",
      "Review changes at the next operational check"
    ]);
  } else if (elevated.length) {
    addBranch("moderate", "Long-term intervention pathway", [
      "Track dependencies: source turbidity can affect coagulation attention; outlet turbidity can affect filters/backwashing; CT, bromate and microbial removal interact through ozone dose and disinfection credits.",
      "Investigate repeated trends, maintenance needs, model/input drift, and validation gaps.",
      "Document operator action and follow-up."
    ]);
  }

  el.innerHTML = branches.map(branch => `<div class="risk-pathway-branch risk-node--${_rcClass(branch.level)}">
    <h5>${escapeHtml(branch.title)}</h5>
    <div class="risk-pathway-steps">
      ${branch.steps.map((step, idx) => `${idx ? '<span class="risk-pathway-arrow">-&gt;</span>' : ""}<span class="risk-pathway-step">${escapeHtml(step)}</span>`).join("")}
    </div>
  </div>`).join("");
}

// Short-term (high risk) and long-term (moderate risk) tables for System Risk screen
function updateRiskTables() {
  const allRisks = [];
  const pushRisk = (label, data) => {
    if (!data?.overall_risk) return;
    allRisks.push({ label, ...data });
  };
  pushRisk("Inlet turbidity", state.source.lastRisk);
  pushRisk("Outlet turbidity after coagulation/sedimentation", state.coagulation.lastRisk);
  if (state.ozonation.operationalRisk) {
    const op = state.ozonation.operationalRisk;
    ["bromate_indicator","ct_indicator","coliform_indicator"].forEach(k => {
      if (op[k]) pushRisk(k.replace("_indicator","").replace("_"," ").toUpperCase(), _opIndicatorToRisk(op[k], k));
    });
  }
  pushRisk("SoSe #11 Distribution", state.distribution.lastRisk);

  const shortEl = document.getElementById("risk-system-short-table");
  const longEl  = document.getElementById("risk-system-long-table");

  const makeTable = (rows, emptyMsg) => {
    if (!rows.length) return `<p class="muted-hint">${emptyMsg}</p>`;
    return `<table class="rc-table"><thead><tr>
      <th>Process / output</th><th class="center">Risk level</th><th>Operator action</th>
    </tr></thead><tbody>${rows.map(r=>{
      const mod = _rcClass(r.overall_risk?.class);
      const icon = mod==="low"?"&#128994;":mod==="high"?"&#128308;":"&#128993;";
      const action = (r.short_term_actions||[])[0] || r.recommended_action || r.operator_message || "–";
      return `<tr><td>${r.label}</td>
        <td class="center"><span class="rc-score-badge rc-score-badge--${mod==="high"?"high":mod==="moderate"?"mod":"low"}">${icon} ${(r.overall_risk?.class||"").toUpperCase()}</span></td>
        <td style="font-size:.8rem;">${escapeHtml(action)}</td></tr>`;
    }).join("")}</tbody></table>`;
  };

  if (shortEl) shortEl.innerHTML = makeTable(allRisks.filter(r=>_rcClass(r.overall_risk?.class)==="high"), "No high-risk predictions at this time.");
  if (longEl)  longEl.innerHTML  = makeTable(allRisks.filter(r=>_rcClass(r.overall_risk?.class)==="moderate"), "No moderate-risk predictions at this time.");
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

  // Operational risk — lightweight endpoint using pre-computed predictions
  const ctPred   = state.ozonation.ctPrediction;
  const brPred   = state.ozonation.bromatePrediction;
  const colPred  = state.ozonation.coliformPrediction;
  if (ctPred == null || brPred == null || colPred == null) return;

  try {
    const opData = await postJSON(ENDPOINTS.riskOzonationOp, {
      bromate_pred: brPred,
      ct_pred: ctPred,
      coliform_pred: colPred,
    });
    state.ozonation.operationalRisk = opData;
    renderOzonationOperational(opData, "oz-inline-risk", "oz-full-risk");
    const cls = opData?.overall_risk?.class || "–";
    setBadge("ozonation-risk-badge", `Risk: ${cls}`, riskBadgeClass(cls));
    updateRiskOverview();
  } catch (err) {
    console.error("Operational ozonation risk error:", err);
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

// Ozonation rolling history (max 30 points each)
const OZ_HISTORY_MAX = 30;
let ctHistoryLabels = [], ctHistoryPred = [], ctHistoryRef = [];
let bromateHistoryLabels = [], bromateHistoryPred = [];
let coliformHistoryLabels = [], coliformHistoryPred = [];

function pushOzonationHistory(chart, labelsArr, label, predsArr, pred, refArr, ref) {
  const ts = label || new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  labelsArr.push(ts);
  predsArr.push(pred ?? 0);
  if (refArr !== null) refArr.push(ref ?? 0);
  if (labelsArr.length > OZ_HISTORY_MAX) {
    labelsArr.shift();
    predsArr.shift();
    if (refArr !== null) refArr.shift();
  }
  if (!chart) return;
  chart.data.labels = labelsArr;
  chart.data.datasets[0].data = predsArr;
  if (refArr !== null && chart.data.datasets[1]) chart.data.datasets[1].data = refArr;
  chart.update();
}

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
      labels: ["CT", "Bromate", "Microbial removal"],
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

function makeCTHistoryChart(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;
  return new Chart(canvas.getContext("2d"), {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Predicted CT",
          data: [],
          borderColor: "#e67e22",
          backgroundColor: "rgba(230,126,34,0.08)",
          borderWidth: 2,
          tension: 0.35,
          fill: false,
          pointRadius: 3,
          pointBackgroundColor: "#e67e22"
        },
        {
          label: "EPA CT (ref.)",
          data: [],
          borderColor: "#2980b9",
          backgroundColor: "transparent",
          borderWidth: 2,
          borderDash: [6, 4],
          tension: 0.5,
          fill: false,
          pointRadius: 2,
          pointBackgroundColor: "#2980b9"
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: true, position: "top" } },
      scales: {
        y: { title: { display: true, text: "CT Value (mg/L·min)" } },
        x: { title: { display: true, text: "Time" }, ticks: { maxTicksLimit: 8 } }
      }
    }
  });
}

function makeOzonationHistoryChart(canvasId, label, color) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;
  return new Chart(canvas.getContext("2d"), {
    type: "line",
    data: {
      labels: [],
      datasets: [{
        label,
        data: [],
        borderColor: color,
        backgroundColor: color.replace(")", ",0.08)").replace("rgb", "rgba"),
        borderWidth: 2,
        tension: 0.35,
        fill: false,
        pointRadius: 3,
        pointBackgroundColor: color
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: true, position: "top" } },
      scales: {
        y: { title: { display: true, text: label } },
        x: { title: { display: true, text: "Time" }, ticks: { maxTicksLimit: 8 } }
      }
    }
  });
}

function makeSoSe9Chart(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;
  return new Chart(canvas.getContext("2d"), {
    type: "line",
    data: {
      labels: ["\uD83D\uDD57 measurement time", "+1h primary", "+2h secondary", "+3h secondary"],
      datasets: [
        {
          label: "Current (measured)",
          data: [null, null, null, null],
          borderColor: "#0ab4c8",
          backgroundColor: "rgba(10,180,200,0.15)",
          pointRadius: 6, pointBorderWidth: 2,
          tension: 0.3, spanGaps: false,
        },
        {
          label: "Predicted 3h",
          data: [null, null, null, null],
          borderColor: "#0d1f3c",
          backgroundColor: "rgba(13,31,60,0.12)",
          pointRadius: 6, pointBorderWidth: 2,
          borderDash: [6, 3],
          tension: 0.3, spanGaps: false,
        },
        {
          label: "P50 reference (15 FTU)",
          data: [15, 15, 15, 15],
          borderColor: "#e67e22", borderWidth: 1.5,
          borderDash: [5, 4], pointRadius: 0, fill: false,
        },
        {
          label: "Attention reference (20 FTU)",
          data: [20, 20, 20, 20],
          borderColor: "#e74c3c", borderWidth: 1.5,
          borderDash: [5, 4], pointRadius: 0, fill: false,
        },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: true,
      scales: {
        y: {
          title: { display: true, text: "Turbidity (FTU)", font: { size: 12 } },
          beginAtZero: true, suggestedMax: 40,
        },
        x: { title: { display: true, text: "Time horizon" } },
      },
      plugins: { legend: { position: "bottom" } },
    },
  });
}

function renderSoSe9Chart(currentVal, predictedVal) {
  if (!charts.sose9) return;
  charts.sose9.data.datasets[0].data = [currentVal != null ? currentVal : null, null, null, null];
  charts.sose9.data.datasets[1].data = [null, null, null, predictedVal != null ? predictedVal : null];
  charts.sose9.update();
}

const charts = {
  coagulation: makeLineChart("chart-coagulation", "Coagulation prediction"),
  ct: makeBarChart("chart-ct", "CT"),
  bromate: makeBarChart("chart-bromate", "Bromate"),
  coliform: makeBarChart("chart-coliform", "Microbial removal"),
  ozonationSummary: makeDoughnutChart("chart-ozonation-summary"),
  ctHistory: makeCTHistoryChart("chart-ct-history"),
  bromateHistory: makeOzonationHistoryChart("chart-bromate-history", "Predicted bromate (µg/L)", "rgb(142,68,173)"),
  coliformHistory: makeOzonationHistoryChart("chart-coliform-history", "Microbial log removal", "rgb(39,174,96)"),
  bromateHistoryRisk: makeOzonationHistoryChart("chart-bromate-history-risk", "Predicted bromate (µg/L)", "rgb(142,68,173)"),
  coliformHistoryRisk: makeOzonationHistoryChart("chart-coliform-history-risk", "Microbial log removal", "rgb(39,174,96)"),
  bactosenseOzone: makeOzonationHistoryChart("chart-bactosense-ozone", "Influent/effluent ozone (awaiting data)", "rgb(41,128,185)"),
  bactosenseUv: makeOzonationHistoryChart("chart-bactosense-uv", "Influent/effluent UV (awaiting data)", "rgb(243,156,18)"),
  bactosenseCells: makeOzonationHistoryChart("chart-bactosense-cells", "BactoSense intact cell number (awaiting data)", "rgb(39,174,96)")
};

// sose9 chart is created on first use (canvas is inside display:none screen at load time)
charts.sose9 = null;

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

// ------------------------------
// SoSe #9 — mock PIMS live flow
// ------------------------------
let sose9LiveInterval = null;

async function updateSoSe9Once() {
  try {
    // Create chart on first use (canvas is visible by now)
    if (!charts.sose9) {
      charts.sose9 = makeSoSe9Chart("sose9-chart");
    }

    const data      = await getJSON(ENDPOINTS.sose9Live);
    const predicted = data?.prediction?.turbidity_3h_ahead_FTU;
    const inp       = data?.input_summary || {};

    console.log("[SoSe9 debug] raw API response", data);
    console.log("[SoSe9 debug] raw input payload", data?.debug?.raw_input_payload);
    console.log("[SoSe9 debug] processed model input vector", data?.debug?.processed_shifted_input_vector);
    console.log("[SoSe9 debug] scaled input vector", data?.debug?.scaled_input_vector);
    console.log("[SoSe9 debug] raw model output", data?.debug?.raw_model_output);
    console.log("[SoSe9 debug] inverse-transformed output", data?.debug?.inverse_transformed_output);
    console.log("[SoSe9 debug] final displayed prediction", predicted, "FTU");

    // Update readings strip
    const readingsEl = document.getElementById("sose9-readings");
    if (readingsEl) readingsEl.classList.remove("sose9-hidden");
    setText("sose9-live-turb",  inp.sensor_turbidity, 2);
    setText("sose9-live-hag",   inp.Hag_dis,          1);
    setText("sose9-live-temp",  inp.sensor_temperature, 1);
    setText("sose9-live-month", inp.month,             0);
    setText("sose9-live-pred",  predicted,             4);

    renderSoSe9Chart(inp.sensor_turbidity, predicted);

    const riskData = await postJSON(ENDPOINTS.riskSourceSose9, {
      predicted_turbidity: predicted,
      current_turbidity: inp.sensor_turbidity,
      prediction_timestamp: data?.timestamp,
      threshold: 15.0,
      yopi_sensitive: false,
    });

    state.source.lastInput = inp;
    state.source.lastPrediction = predicted;
    state.source.lastRisk = riskData;
    state.source.lastTimestamp = data?.timestamp || null;

    renderRichRisk("sose9-risk-output", riskData);

    const riskClass = riskData?.overall_risk?.class || "–";
    const riskLabel = riskData?.sose9_persistence?.operational_risk || riskClass;
    setBadge("sose9-status-badge", `Risk: ${riskLabel}`, riskBadgeClass(riskClass));
    updateRiskOverview();
  } catch (err) {
    setBadge("sose9-status-badge", "Error", "error");
    const out = document.getElementById("sose9-risk-output");
    if (out) out.innerHTML = `<pre class="json-box">${escapeHtml(err.message)}</pre>`;
  }
}

function stopSoSe9Live() {
  if (sose9LiveInterval) { clearInterval(sose9LiveInterval); sose9LiveInterval = null; }
  const startBtn = document.getElementById("btn-sose9-live-start");
  const stopBtn  = document.getElementById("btn-sose9-live-stop");
  if (startBtn) startBtn.style.display = "";
  if (stopBtn)  stopBtn.style.display  = "none";
  setBadge("sose9-status-badge", "Stopped", "info");
}

document.getElementById("btn-sose9-once")?.addEventListener("click", async () => {
  console.log("[SoSe9] Load from mock PIMS clicked");
  setBadge("sose9-status-badge", "Loading...", "info");
  await updateSoSe9Once();
});

document.getElementById("btn-sose9-live-start")?.addEventListener("click", async () => {
  stopSoSe9Live();
  await updateSoSe9Once();
  sose9LiveInterval = setInterval(updateSoSe9Once, 5000);
});

document.getElementById("btn-sose9-live-stop")?.addEventListener("click", () => {
  stopSoSe9Live();
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
    const baseInput = state.coagulation.lastInput || {
      ftu_raw_water: 15.2,
      fecl3_concentration: 5,
      temperature_raw_water: 16,
      ph_raw_water: 7.4,
      after_dredging: 450,
      lane: 1,
      year: 2026
    };

    const lane = Number(baseInput.lane || 1);

    const payload = {
      ...baseInput,
      [`flow_coagulation_${lane}`]: 1000
    };

    const data = await postJSON("/treatment/coagulation/rl", payload);
    renderRL5Advisory("rl5-latest", data);

    const currentDose = extractNumber(data.input_data?.fecl3_concentration);
    const recommendedDose = extractNumber(data.recommended_fecl3_concentration?.value);
    const outputTurbidity = extractNumber(data.predicted_outlet_turbidity?.value);
    const dosingFlow = extractNumber(data.recommended_fecl3_dosing_flow?.value);

    if (currentDose !== null) setValue("rl5_current_fecl3_dose", currentDose);
    if (recommendedDose !== null) setValue("rl5_recommended_fecl3_dose", recommendedDose);
    if (outputTurbidity !== null) setValue("rl5_output_turbidity", outputTurbidity);
    if (dosingFlow !== null) setValue("rl5_dosing_flow", dosingFlow);

    setText("rl5-current-dose-display", currentDose, 2);
    setText("rl5-recommended-dose-display", recommendedDose, 2);
    setText("rl5-output-turbidity-display", outputTurbidity, 3);
    setText("rl5-dosing-flow-display", dosingFlow, 2);
    setText("rl5-validation-status-display", "under validation", 0);

    const riskPayload = {
      current_fecl3_dose: currentDose,
      recommended_fecl3_dose: recommendedDose,
      output_turbidity: outputTurbidity,
      confidence: 0
    };

    await runAutomaticRL5Risk(riskPayload);

  } catch (err) {
    renderStatusCard("rl5-latest", "RL #5 advisory unavailable", { status: "error", message: err.message });
  }
});

document.getElementById("btn-bactosense-latest")?.addEventListener("click", async () => {
  try {
    renderBactoSenseStatus("bactosense-latest", await getJSON(ENDPOINTS.treatmentBactoSense));
  } catch (err) {
    renderStatusCard("bactosense-latest", "BactoSense unavailable", { status: "error", message: err.message });
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

document.getElementById("btn-rl5-demo")?.remove();

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
    if (latestOzonation.coliform !== null) items.push("<li>Microbial-removal prediction has been generated successfully.</li>");
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
// Coagulation manual/live + automatic RL #5 update
// ------------------------------
function stopCoagulationLiveMode() {
  if (coagulationLiveInterval) {
    clearInterval(coagulationLiveInterval);
    coagulationLiveInterval = null;
  }
  setBadge("coagulation-mode-badge", "Mode: manual", "info");
}

async function updateRL5FromCoagulationInput(input) {
  try {
    const lane = Number(input.lane || 1);

    const payload = {
      ...input,
      [`flow_coagulation_${lane}`]: input[`flow_coagulation_${lane}`] ?? 1000
    };

    const data = await postJSON("/treatment/coagulation/rl", payload);
    renderRL5Advisory("rl5-latest", data);

    const currentDose = extractNumber(data.input_data?.fecl3_concentration);
    const recommendedDose = extractNumber(data.recommended_fecl3_concentration?.value);
    const outputTurbidity = extractNumber(data.predicted_outlet_turbidity?.value);
    const dosingFlow = extractNumber(data.recommended_fecl3_dosing_flow?.value);

    setValue("rl5_current_fecl3_dose", currentDose);
    setValue("rl5_recommended_fecl3_dose", recommendedDose);
    setValue("rl5_output_turbidity", outputTurbidity);
    setValue("rl5_dosing_flow", dosingFlow);

    setText("rl5-current-dose-display", currentDose, 2);
    setText("rl5-recommended-dose-display", recommendedDose, 2);
    setText("rl5-output-turbidity-display", outputTurbidity, 3);
    setText("rl5-dosing-flow-display", dosingFlow, 2);
    setText("rl5-validation-status-display", "under validation", 0);

    const riskPayload = {
      current_fecl3_dose: currentDose,
      recommended_fecl3_dose: recommendedDose,
      output_turbidity: outputTurbidity,
      confidence: 0
    };

    await runAutomaticRL5Risk(riskPayload);

  } catch (err) {
    renderStatusCard("rl5-latest", "RL #5 advisory unavailable", { status: "error", message: err.message });
  }
}

document.getElementById("form-coagulation")?.addEventListener("submit", async (e) => {
  e.preventDefault();

  try {
    const payload = formDataToObject(e.target);
    const data = await postJSON(ENDPOINTS.coagulation, payload);

    const pred = pickPrediction(data, ["prediction"]);
    state.coagulation.lastInput = payload;
    state.coagulation.lastPrediction = pred;
    updateDecisionTree();

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

    // Same SoSe #8 / PIMS input now automatically feeds RL #5
    await updateRL5FromCoagulationInput(payload);

  } catch (err) {
    alert("Coagulation request failed: " + err.message);
  }
});

document.getElementById("form-rl5")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = formDataToObject(e.target);
  await updateRL5FromCoagulationInput(payload);
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
    const status = classifyPrediction(
      pred,
      targetInfo.threshold ?? 1,
      (targetInfo.threshold ?? 1) + 1
    );

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

    // Same live/mock-PIMS input now automatically feeds RL #5
    await updateRL5FromCoagulationInput(input);

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

    const data = await postJSON(ENDPOINTS.treatmentCT, payload);

    const pred = pickPrediction(data, ["ct_prediction", "prediction"]);
    state.ozonation.ctInput = payload;
    state.ozonation.ctPrediction = pred;
    updateDecisionTree();

    setText("ct-prediction", pred, 3);

    const status = classifyCT(pred);
    setText("ct-status", status, 0);

    if (charts.ct) {
      charts.ct.data.datasets[0].data = [pred ?? 0];
      charts.ct.update();
    }

    latestOzonation.ct = pred;
    pushOzonationHistory(charts.ctHistory, ctHistoryLabels, null, ctHistoryPred, pred, ctHistoryRef, 1.2);
    refreshOzonationDashboard();

    // Individual CT risk card
    try {
      const ctRisk = await postJSON(ENDPOINTS.riskCT, payload);
      renderRichRisk("ct-risk-card", ctRisk);
    } catch (_) {}

    await runAutomaticOzonationRisk();
  } catch (err) {
    alert("CT request failed: " + err.message);
  }
});

document.getElementById("form-bromate")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = formDataToObject(e.target);

    const data = await postJSON(ENDPOINTS.treatmentBromate, payload);

    const pred = pickPrediction(data, ["bromate_prediction", "prediction"]);
    state.ozonation.bromateInput = payload;
    state.ozonation.bromatePrediction = pred;
    updateDecisionTree();

    setText("bromate-prediction", pred, 3);

    const status = classifyPrediction(pred, 5, 10);
    setText("bromate-status", status, 0);

    if (charts.bromate) {
      charts.bromate.data.datasets[0].data = [pred ?? 0];
      charts.bromate.update();
    }

    latestOzonation.bromate = pred;
    pushOzonationHistory(charts.bromateHistory, bromateHistoryLabels, null, bromateHistoryPred, pred, null, null);
    refreshOzonationDashboard();

    // Individual bromate risk card
    try {
      const brRisk = await postJSON(ENDPOINTS.riskBromate, payload);
      renderRichRisk("bromate-risk-card", brRisk);
    } catch (_) {}

    await runAutomaticOzonationRisk();
  } catch (err) {
    alert("Bromate request failed: " + err.message);
  }
});

document.getElementById("form-coliform")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = formDataToObject(e.target);

    const data = await postJSON(ENDPOINTS.treatmentColiform, payload);

    const pred = pickPrediction(data, ["coliform_prediction", "prediction"]);
    state.ozonation.coliformInput = payload;
    state.ozonation.coliformPrediction = pred;
    updateDecisionTree();

    setText("coliform-prediction", pred, 3);

    const status = classifyInverse(pred, 0.85, 1.2);
    setText("coliform-status", status, 0);

    if (charts.coliform) {
      charts.coliform.data.datasets[0].data = [pred ?? 0];
      charts.coliform.update();
    }

    latestOzonation.coliform = pred;
    pushOzonationHistory(charts.coliformHistory, coliformHistoryLabels, null, coliformHistoryPred, pred, null, null);
    refreshOzonationDashboard();

    // Individual coliform risk card
    try {
      const colRisk = await postJSON(ENDPOINTS.riskColiform, payload);
      renderRichRisk("coliform-risk-card", colRisk);
    } catch (_) {}

    await runAutomaticOzonationRisk();
  } catch (err) {
    alert("Coliform request failed: " + err.message);
  }
});

// ------------------------------
// Ozonation live mode (PIMS synthetic feed)
// CT: real-time resolution | Bromate & Coliform: 1h resolution
// ------------------------------
let ozonationLiveInterval = null;

function stopOzonationLiveMode() {
  if (ozonationLiveInterval) {
    clearInterval(ozonationLiveInterval);
    ozonationLiveInterval = null;
  }
  setBadge("ct-mode-badge", "Mode: manual", "info");
  setBadge("bromate-mode-badge", "Mode: manual (1h res.)", "info");
  setBadge("coliform-mode-badge", "Mode: manual (1h res.)", "info");
  setBadge("ozonation-mode-badge", "Mode: manual", "info");
}

async function updateLiveOzonationOnce() {
  // --- CT (SoSe #10) ---
  try {
    const ctData = await getJSON(ENDPOINTS.treatmentCTLatest);
    const ctPred = pickPrediction(ctData, ["prediction"]);
    const ctInput = ctData.input_data;
    state.ozonation.ctInput = ctInput;
    state.ozonation.ctPrediction = ctPred;

    setValue("ct_Chamber", ctInput.Chamber);
    setValue("ct_WaterTemperature", ctInput.WaterTemperature);
    setValue("ct_RFTurbidity", ctInput.RFTurbidity);
    setValue("ct_FlowRate", ctInput.FlowRate);
    setValue("ct_Ozonedosage", ctInput.Ozonedosage);

    setText("ct-prediction", ctPred, 3);
    setText("ct-status", classifyCT(ctPred), 0);
    if (charts.ct) { charts.ct.data.datasets[0].data = [ctPred ?? 0]; charts.ct.update(); }
    latestOzonation.ct = ctPred;
    const ctRef = 1.2;
    pushOzonationHistory(charts.ctHistory, ctHistoryLabels, ctData.timestamp?.slice(11, 19), ctHistoryPred, ctPred, ctHistoryRef, ctRef);
    setBadge("ct-mode-badge", `Mode: live — ${ctData.timestamp?.slice(11, 19) ?? ""}`, "info");
    try { renderRichRisk("ct-risk-card", await postJSON(ENDPOINTS.riskCT, ctData.input_data)); } catch(_) {}
  } catch (err) {
    console.error("CT live error:", err);
    setBadge("ct-mode-badge", "Mode: live error", "high");
  }

  // --- Bromate (SoSe #10.1) — 1h resolution ---
  try {
    const brData = await getJSON(ENDPOINTS.treatmentBromateLatest);
    const brPred = pickPrediction(brData, ["prediction"]);
    const brInput = brData.input_data;
    state.ozonation.bromateInput = brInput;
    state.ozonation.bromatePrediction = brPred;

    setValue("br_month", brInput.month);
    setValue("br_Chamber", brInput.Chamber);
    setValue("br_WaterTemperature", brInput.WaterTemperature);
    setValue("br_RFTurbidity", brInput.RFTurbidity);
    setValue("br_FlowRate", brInput.FlowRate);
    setValue("br_Ozonedosage", brInput.Ozonedosage);
    setValue("br_Residencetime", brInput.Residencetime);
    setValue("br_WaterTemperature_1", brInput.WaterTemperature_1);
    setValue("br_RFturbidity_1", brInput.RFturbidity_1);
    setValue("br_FlowRate_1", brInput.FlowRate_1);
    setValue("br_Ozonedosage_1", brInput.Ozonedosage_1);
    setValue("br_CT_All", brInput.CT_All);

    setText("bromate-prediction", brPred, 3);
    setText("bromate-status", classifyPrediction(brPred, 5, 10), 0);
    if (charts.bromate) { charts.bromate.data.datasets[0].data = [brPred ?? 0]; charts.bromate.update(); }
    latestOzonation.bromate = brPred;
    pushOzonationHistory(charts.bromateHistory, bromateHistoryLabels, brData.timestamp?.slice(11, 19), bromateHistoryPred, brPred, null, null);
    pushOzonationHistory(charts.bromateHistoryRisk, bromateHistoryLabels, brData.timestamp?.slice(11, 19), [...bromateHistoryPred], brPred, null, null);
    setBadge("bromate-mode-badge", "Mode: live (1h res.)", "info");
    try { renderRichRisk("bromate-risk-card", await postJSON(ENDPOINTS.riskBromate, brData.input_data)); } catch(_) {}
  } catch (err) {
    console.error("Bromate live error:", err);
    setBadge("bromate-mode-badge", "Mode: live error", "high");
  }

  // --- Coliform (SoSe #10.2) — 1h resolution ---
  try {
    const colData = await getJSON(ENDPOINTS.treatmentColiformLatest);
    const colPred = pickPrediction(colData, ["prediction"]);
    const colInput = colData.input_data;
    state.ozonation.coliformInput = colInput;
    state.ozonation.coliformPrediction = colPred;

    setValue("col_Chamber", colInput.Chamber);
    setValue("col_WaterTemperature", colInput.WaterTemperature);
    setValue("col_RFTurbidity", colInput.RFTurbidity);
    setValue("col_FlowRate", colInput.FlowRate);
    setValue("col_Ozonedosage", colInput.Ozonedosage);
    setValue("col_RFturbidity_1", colInput.RFturbidity_1);
    setValue("col_CT_All", colInput.CT_All);

    setText("coliform-prediction", colPred, 3);
    setText("coliform-status", classifyInverse(colPred, 0.85, 1.2), 0);
    if (charts.coliform) { charts.coliform.data.datasets[0].data = [colPred ?? 0]; charts.coliform.update(); }
    latestOzonation.coliform = colPred;
    pushOzonationHistory(charts.coliformHistory, coliformHistoryLabels, colData.timestamp?.slice(11, 19), coliformHistoryPred, colPred, null, null);
    pushOzonationHistory(charts.coliformHistoryRisk, coliformHistoryLabels, colData.timestamp?.slice(11, 19), [...coliformHistoryPred], colPred, null, null);
    setBadge("coliform-mode-badge", "Mode: live (1h res.)", "info");
  } catch (err) {
    console.error("Coliform live error:", err);
    setBadge("coliform-mode-badge", "Mode: live error", "high");
  }

  setBadge("ozonation-mode-badge", "Mode: live", "info");
  refreshOzonationDashboard();
  await runAutomaticOzonationRisk();
}

document.getElementById("btn-ozonation-live-start")?.addEventListener("click", async () => {
  stopOzonationLiveMode();
  await updateLiveOzonationOnce();
  ozonationLiveInterval = setInterval(updateLiveOzonationOnce, 5000);
});

document.getElementById("btn-ozonation-live-stop")?.addEventListener("click", () => {
  stopOzonationLiveMode();
});

// ------------------------------
// Risk forms - manual screens still work
// ------------------------------
document.getElementById("form-risk-source")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = normalizeBooleanStrings(formDataToObject(e.target));
    const data = await postJSON(ENDPOINTS.riskSourceSose9, payload);
    state.source.lastInput = { sensor_turbidity: payload.current_turbidity };
    state.source.lastPrediction = payload.predicted_turbidity;
    state.source.lastRisk = data;
    state.source.lastTimestamp = payload.prediction_timestamp || null;
    renderRichRisk("risk-source-output", data);
    updateRiskOverview();
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
    state.coagulation.lastInput = payload;
    state.coagulation.lastPrediction = data?.prediction ?? state.coagulation.lastPrediction;
    renderCoagulationRisk(data, "coagulation-risk-output", "risk-coagulation-output");
    const riskClass = data?.traffic_light?.level || data?.overall_risk?.class || "–";
    setBadge("coagulation-risk-badge", `Risk: ${riskClass}`, riskBadgeClass(riskClass));
    updateRiskOverview();
  } catch (err) {
    renderJSON("risk-coagulation-output", { error: err.message });
  }
});

document.getElementById("form-risk-rl5")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = normalizeBooleanStrings(formDataToObject(e.target));
    const data = await postJSON(ENDPOINTS.riskRL5, payload);
    state.rl5.lastInput = payload;
    state.rl5.lastRisk = null;
    renderStatusCard("risk-rl5-output", "RL #5 advisory validation", data);
    updateRiskOverview();
  } catch (err) {
    renderStatusCard("risk-rl5-output", "RL #5 advisory unavailable", { status: "error", message: err.message });
  }
});

document.getElementById("form-risk-ozonation")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = normalizeBooleanStrings(formDataToNestedObject(e.target));
    const data = await postJSON(ENDPOINTS.riskOzonation, payload);
    state.ozonation.combinedRisk = data;
    renderRichRisk("risk-ozonation-output", data);
    updateRiskOverview();
  } catch (err) {
    renderJSON("risk-ozonation-output", { error: err.message });
  }
});

document.getElementById("form-risk-distribution")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = normalizeBooleanStrings(formDataToObject(e.target));
    const data = await postJSON(ENDPOINTS.riskDistributionSose11, payload);
    state.distribution.lastInput = payload;
    state.distribution.lastRisk = data;
    renderRichRisk("risk-distribution-output", data);
    updateRiskOverview();
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

updateRiskDashboard();

// ==========================================
// RWS HARD SENSORS
// ==========================================
// ==========================================
// RWS HARD SENSORS + TIMESERIES
// ==========================================

const rwsCharts = {};

const rwsParametersByLocation = {
  hagestein_boven: [
    "water_temperature",
    "water_level",
    "discharge"
  ],

  nieuwegein_lekkanaal: [
    "water_temperature",
    "water_level",
    "discharge",
    "chloride"
  ],

  nieuwegein_doorslag: [
    "water_level",
    "discharge"
  ]
};

const rwsParameterLabels = {
  water_temperature: "Water temperature",
  water_level: "Water level",
  discharge: "Discharge",
  chloride: "Chloride concentration"
};


// ==========================================
// LOAD LATEST VALUE
// ==========================================

async function loadRwsLatest(location, parameter) {

  const url =
    `${ENDPOINTS.rwsLatest}?location=${location}&parameter=${parameter}`;

  return getJSON(url);
}


// ==========================================
// LOAD TIMESERIES
// ==========================================

async function loadRwsTimeseries(
  location,
  parameter,
  daysBack = 2
) {

  const url =
    `${ENDPOINTS.rwsTimeseries}?location=${location}&parameter=${parameter}&days_back=${daysBack}`;

  return getJSON(url);
}


// ==========================================
// RENDER LATEST
// ==========================================

function renderRwsLatest(
  location,
  parameter,
  data
) {

  const el =
    document.getElementById(
      `${location}-${parameter}-latest`
    );

  if (!el) return;

  el.innerHTML = `
    <span class="metric-label">
      ${rwsParameterLabels[parameter]}
    </span>

    <strong class="metric-value">
      ${data.latest_value ?? "–"}
    </strong>

    <div class="metric-unit">
      ${data.unit ?? ""}
    </div>

    <div class="metric-unit">
      Updated:
      ${data.timestamp ?? "–"}
    </div>
  `;
}


// ==========================================
// RENDER CHART
// ==========================================

function renderRwsChart(
  location,
  parameter,
  data
) {

  const canvasId =
    `chart-${location}-${parameter}`;

  const canvas =
    document.getElementById(canvasId);

  if (!canvas) return;

  const labels =
    data.timeseries.map(item => {

      const d = new Date(item.timestamp);

      return d.toLocaleString([], {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit"
      });
    });

  const values =
    data.timeseries.map(item => item.value);

  if (rwsCharts[canvasId]) {
    rwsCharts[canvasId].destroy();
  }

  rwsCharts[canvasId] =
    new Chart(canvas.getContext("2d"), {

      type: "line",

      data: {
        labels,

        datasets: [{
          label:
            `${data.label} (${data.unit})`,

          data: values,

          tension: 0.3,
          fill: false,
          borderWidth: 2,
          pointRadius: 0
        }]
      },

      options: {
        responsive: true,
        maintainAspectRatio: false,

        interaction: {
          mode: "index",
          intersect: false
        },

        plugins: {
          legend: {
            display: true
          }
        },

        scales: {
          x: {
            ticks: {
              maxTicksLimit: 8
            }
          }
        }
      }
    });
}


// ==========================================
// LOAD WHOLE STATION DASHBOARD
// ==========================================

async function loadRwsStationDashboard(location) {

  const parameters =
    rwsParametersByLocation[location] || [];

  for (const parameter of parameters) {

    try {

      // latest
      const latest =
        await loadRwsLatest(
          location,
          parameter
        );

      renderRwsLatest(
        location,
        parameter,
        latest
      );

      // timeseries
      const timeseries =
        await loadRwsTimeseries(
          location,
          parameter,
          2
        );

      renderRwsChart(
        location,
        parameter,
        timeseries
      );

    } catch (err) {

      const el =
        document.getElementById(
          `${location}-${parameter}-latest`
        );

      if (el) {

        el.innerHTML = `
          <span class="metric-label">
            ${rwsParameterLabels[parameter]}
          </span>

          <strong class="metric-value small">
            Error
          </strong>

          <div class="metric-unit">
            ${err.message}
          </div>
        `;
      }
    }
  }
}


// ==========================================
// AUTO REFRESH
// ==========================================

let currentRwsLocation = null;

function startRwsAutoRefresh(location) {

  currentRwsLocation = location;

  loadRwsStationDashboard(location);

  if (window.rwsRefreshInterval) {
    clearInterval(window.rwsRefreshInterval);
  }

  window.rwsRefreshInterval =
    setInterval(() => {

      if (currentRwsLocation) {

        loadRwsStationDashboard(
          currentRwsLocation
        );
      }

    }, 300000); // 5 min
}

// Initial RIWA dashboard loading
startRwsAutoRefresh("hagestein_boven");
loadRwsStationDashboard("nieuwegein_lekkanaal");
loadRwsStationDashboard("nieuwegein_doorslag");


// // ==========================================
// // ToDrinQ UI - final unified version
// // ==========================================

// const ENDPOINTS = {
//   coagulation: "/predict/coagulation",
//   coagulationLive: "/predict/coagulation/live",
//   ct: "/predict/ct",
//   bromate: "/predict/bromate",
//   coliform: "/predict/coliform",

//   sourceOverview: "/source/overview",
//   sourceLatest: "/source/sose-9/latest",

//   treatmentOverview: "/treatment/overview",
//   treatmentCoagLatest: "/treatment/coagulation/latest",
//   treatmentRLLatest: "/treatment/coagulation/rl/latest",
//   treatmentCT: "/treatment/ozonation/ct",
//   treatmentBromate: "/treatment/ozonation/bromate",
//   treatmentColiform: "/treatment/ozonation/coliform",
//   treatmentBactoSense: "/treatment/hard-sensors/bactosense-4/latest",
//   rwsLatest: "/source/hard-sensors/rws/latest",
//   rwsTimeseries: "/source/hard-sensors/rws/timeseries",


//   distributionOverview: "/distribution/overview",
//   distributionLatest: "/distribution/sose-11/latest",

//   riskOverview: "/risk/overview",
//   riskSourceSose9: "/risk/source/sose-9/current",
//   riskCoagulation: "/risk/coagulation",
//   riskRL5: "/risk/treatment/rl-5/current",
//   riskCT: "/risk/ct",
//   riskBromate: "/risk/bromate",
//   riskColiform: "/risk/coliform",
//   riskOzonation: "/risk/ozonation/current",
//   riskDistributionSose11: "/risk/distribution/sose-11/current",
//   riskTreatmentCurrent: "/risk/treatment/current",
//   riskSystemCurrent: "/risk/system/current"
// };

// const breadcrumbs = document.getElementById("breadcrumbs");

// const screenTitles = {
//   "screen-home": "Home",
//   "screen-source": "Source Module – SoSe #9",
//   "screen-treatment": "Treatment Module",
//   "screen-treatment-overview": "Treatment Overview",
//   "screen-hard-placeholder": "Hard Sensor Monitoring",
//   "screen-soft-select": "Soft Sensor Platform Models",
//   "screen-coagulation": "SoSe #8 – Coagulation-Flocculation Turbidity Estimation",
//   "screen-rl5": "RL #5 – Optimal FeCl₃ Dosage",
//   "screen-ozonation-select": "Ozonation Models",
//   "screen-ct": "SoSe #10 – CT Prediction",
//   "screen-bromate": "SoSe #10.1 – Bromate Formation",
//   "screen-coliform": "SoSe #10.2 – Coliform Removal",
//   "screen-ozonation-dashboard": "Ozonation Dashboard",
//   "screen-hard-sensors": "BactoSense #4",
//   "screen-distribution": "Distribution Module – SoSe #11",
//   "screen-risk": "Risk Module",
//   "screen-risk-overview": "Risk Overview",
//   "screen-risk-source": "SoSe #9 Source Risk",
//   "screen-risk-coagulation": "SoSe #8 Coagulation Risk",
//   "screen-risk-rl5": "RL #5 Dosage Risk",
//   "screen-risk-ozonation": "Combined Ozonation Risk",
//   "screen-risk-distribution": "SoSe #11 Distribution Risk",
//   "screen-risk-treatment": "Treatment Current Risk",
//   "screen-risk-system": "Source-to-Tap System Risk"
// };

// const state = {
//   coagulation: {
//     lastInput: null,
//     lastPrediction: null,
//     lastRisk: null
//   },
//   rl5: {
//     lastInput: null,
//     lastRisk: null
//   },
//   ozonation: {
//     ctInput: null,
//     ctPrediction: null,
//     bromateInput: null,
//     bromatePrediction: null,
//     coliformInput: null,
//     coliformPrediction: null,
//     combinedRisk: null
//   }
// };

// function showScreen(id) {
//   document.querySelectorAll(".screen").forEach((screen) => {
//     screen.classList.remove("active");
//   });

//   const target = document.getElementById(id);
//   if (target) {
//     target.classList.add("active");
//     updateBreadcrumbs(id);
//     window.scrollTo({ top: 0, behavior: "smooth" });
//   }
// }

// function updateBreadcrumbs(id) {
//   const label = screenTitles[id] || "Platform";
//   breadcrumbs.innerHTML = `
//     <button type="button" data-nav="screen-home">Home</button>
//     <span>›</span>
//     <span>${label}</span>
//   `;
// }

// document.addEventListener("click", (e) => {
//   const navEl = e.target.closest("[data-nav]");
//   if (navEl) {
//     e.preventDefault();
//     showScreen(navEl.dataset.nav);
//   }
// });

// updateBreadcrumbs("screen-home");

// // ------------------------------
// // Helpers
// // ------------------------------
// function formDataToObject(form) {
//   const out = {};
//   new FormData(form).forEach((value, key) => {
//     if (value === "") {
//       out[key] = value;
//       return;
//     }
//     const n = Number(value);
//     out[key] = Number.isNaN(n) ? value : n;
//   });
//   return out;
// }

// function formDataToNestedObject(form) {
//   const out = {};
//   new FormData(form).forEach((value, key) => {
//     const parts = key.split(".");
//     let ref = out;

//     for (let i = 0; i < parts.length - 1; i++) {
//       if (!ref[parts[i]]) ref[parts[i]] = {};
//       ref = ref[parts[i]];
//     }

//     const n = Number(value);
//     ref[parts[parts.length - 1]] = Number.isNaN(n) ? value : n;
//   });
//   return out;
// }

// function normalizeBooleanStrings(obj) {
//   for (const key of Object.keys(obj)) {
//     if (typeof obj[key] === "object" && obj[key] !== null) {
//       normalizeBooleanStrings(obj[key]);
//     } else if (obj[key] === "true") {
//       obj[key] = true;
//     } else if (obj[key] === "false") {
//       obj[key] = false;
//     }
//   }
//   return obj;
// }

// async function getJSON(url) {
//   const r = await fetch(url);
//   if (!r.ok) {
//     const text = await r.text();
//     throw new Error(`${r.status} ${text}`);
//   }
//   return r.json();
// }

// async function postJSON(url, payload) {
//   const r = await fetch(url, {
//     method: "POST",
//     headers: { "Content-Type": "application/json" },
//     body: JSON.stringify(payload)
//   });

//   if (!r.ok) {
//     const text = await r.text();
//     throw new Error(`${r.status} ${text}`);
//   }

//   return r.json();
// }

// function renderJSON(id, data) {
//   const el = document.getElementById(id);
//   if (!el) return;
//   el.textContent = JSON.stringify(data, null, 2);
// }

// function setText(id, value, digits = 2) {
//   const el = document.getElementById(id);
//   if (!el) return;

//   if (value === null || value === undefined || Number.isNaN(value)) {
//     el.textContent = "–";
//     return;
//   }

//   if (typeof value === "number") {
//     el.textContent = value.toFixed(digits);
//   } else {
//     el.textContent = value;
//   }
// }

// function setHtml(id, html) {
//   const el = document.getElementById(id);
//   if (!el) return;
//   el.innerHTML = html;
// }

// function setValue(id, value) {
//   const el = document.getElementById(id);
//   if (!el) return;
//   el.value = value ?? "";
// }

// function setBadge(id, text, level = "info") {
//   const el = document.getElementById(id);
//   if (!el) return;
//   el.textContent = text;
//   el.classList.remove("info", "low", "moderate", "high");
//   el.classList.add(level);
// }

// function extractNumber(value) {
//   if (Array.isArray(value)) {
//     if (!value.length) return null;
//     return extractNumber(value[0]);
//   }
//   if (typeof value === "number") return value;
//   if (typeof value === "string") {
//     const n = Number(value);
//     return Number.isNaN(n) ? null : n;
//   }
//   return null;
// }

// function classifyPrediction(value, low, high) {
//   if (value === null || value === undefined || Number.isNaN(value)) return "–";
//   if (value <= low) return "Low";
//   if (value <= high) return "Moderate";
//   return "High";
// }

// function classifyInverse(value, moderateMin, highMin) {
//   if (value === null || value === undefined || Number.isNaN(value)) return "–";
//   if (value >= highMin) return "High";
//   if (value >= moderateMin) return "Moderate";
//   return "Low";
// }

// function levelFromText(text) {
//   if (text === "Low") return "low";
//   if (text === "Moderate") return "moderate";
//   if (text === "High" || text === "Major") return "high";
//   return "info";
// }

// function pickPrediction(data, keys = []) {
//   for (const key of keys) {
//     if (key in data) {
//       const value = extractNumber(data[key]);
//       if (value !== null) return value;
//     }
//   }

//   if ("prediction" in data) return extractNumber(data.prediction);
//   return null;
// }

// function escapeHtml(value) {
//   return String(value ?? "")
//     .replaceAll("&", "&amp;")
//     .replaceAll("<", "&lt;")
//     .replaceAll(">", "&gt;");
// }

// function renderList(items) {
//   if (!items || !items.length) return "<li>–</li>";
//   return items.map(item => `<li>${escapeHtml(item)}</li>`).join("");
// }

// function riskBadgeClass(level) {
//   const text = String(level || "").toLowerCase();
//   if (text === "low") return "low";
//   if (text === "moderate") return "moderate";
//   if (text === "high" || text === "major") return "high";
//   return "info";
// }

// function renderRichRisk(id, data) {
//   const el = document.getElementById(id);
//   if (!el) return;

//   if (!data || data.error) {
//     el.innerHTML = `<pre class="json-box">${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
//     return;
//   }

//   const overall = data.overall_risk || {};
//   const likelihood = data.likelihood || {};
//   const severity = data.severity || {};
//   const consequence = data.consequence || {};
//   const vulnerable = data.vulnerable_groups || {};

//   const componentsHtml = data.components
//     ? `<details class="risk-details-block">
//          <summary>Show component details</summary>
//          <pre class="json-box">${escapeHtml(JSON.stringify(data.components, null, 2))}</pre>
//        </details>`
//     : "";

//   const graphHtml = data.graph_payload
//     ? `<details class="risk-details-block">
//          <summary>Show graph / decision-tree payload</summary>
//          <pre class="json-box">${escapeHtml(JSON.stringify(data.graph_payload, null, 2))}</pre>
//        </details>`
//     : "";

//   el.innerHTML = `
//     <div class="risk-rich-card">
//       <div class="status-row">
//         <span class="badge ${riskBadgeClass(overall.class)}">Overall risk: ${escapeHtml(overall.class || "–")}</span>
//         <span class="badge info">Module: ${escapeHtml(data.module || "–")}</span>
//         ${data.submodule ? `<span class="badge info">Scope: ${escapeHtml(data.submodule)}</span>` : ""}
//       </div>

//       <div class="metric-grid">
//         <div class="metric">
//           <span class="metric-label">Sensor / model</span>
//           <strong class="metric-value small">${escapeHtml(data.sensor || data.sensor_or_model || "–")}</strong>
//         </div>
//         <div class="metric">
//           <span class="metric-label">Prediction</span>
//           <strong class="metric-value small">${escapeHtml(data.prediction ?? "–")}</strong>
//         </div>
//         <div class="metric">
//           <span class="metric-label">Threshold</span>
//           <strong class="metric-value small">${escapeHtml(data.threshold ?? "–")}</strong>
//         </div>
//       </div>

//       ${data.hazard_id ? `<div class="info-box"><strong>Hazard:</strong> ${escapeHtml(data.hazard_id)}<br>${escapeHtml(data.hazard_description || "–")}</div>` : ""}
//       ${data.dominant_hazard ? `<div class="info-box"><strong>Dominant hazard:</strong><br>${escapeHtml(data.dominant_hazard)}</div>` : ""}

//       <div class="metric-grid">
//         <div class="metric">
//           <span class="metric-label">Likelihood</span>
//           <strong class="metric-value small">${escapeHtml(likelihood.class || "–")}</strong>
//           <div class="metric-unit">Score: ${escapeHtml(likelihood.score ?? "–")} | Proxy: ${escapeHtml(likelihood.probability_proxy ?? "–")}</div>
//         </div>
//         <div class="metric">
//           <span class="metric-label">Severity</span>
//           <strong class="metric-value small">${escapeHtml(severity.class || "–")}</strong>
//           <div class="metric-unit">Score: ${escapeHtml(severity.score ?? "–")} | Deviation: ${escapeHtml(severity.deviation_ratio ?? "–")}</div>
//         </div>
//         <div class="metric">
//           <span class="metric-label">Consequence</span>
//           <strong class="metric-value small">${escapeHtml(consequence.class || "–")}</strong>
//           <div class="metric-unit">Score: ${escapeHtml(consequence.score ?? "–")}</div>
//         </div>
//       </div>

//       ${data.operator_message ? `<div class="info-box"><strong>Operator message:</strong><br>${escapeHtml(data.operator_message)}</div>` : ""}
//       ${data.reviewer_summary ? `<div class="info-box"><strong>Reviewer summary:</strong><br>${escapeHtml(data.reviewer_summary)}</div>` : ""}
//       ${data.recommended_action ? `<div class="info-box"><strong>Recommended action:</strong><br>${escapeHtml(data.recommended_action)}</div>` : ""}

//       <div class="two-col">
//         <div class="panel">
//           <h4>Short-term actions</h4>
//           <ul class="result-list">${renderList(data.short_term_actions)}</ul>
//         </div>
//         <div class="panel">
//           <h4>Long-term actions</h4>
//           <ul class="result-list">${renderList(data.long_term_actions)}</ul>
//         </div>
//       </div>

//       ${vulnerable.note ? `<div class="info-box"><strong>Vulnerable groups:</strong><br>${escapeHtml(vulnerable.note)}</div>` : ""}
//       ${componentsHtml}
//       ${graphHtml}
//     </div>
//   `;
// }

// // ------------------------------
// // Coagulation-specific helpers
// // ------------------------------
// function getCoagulationOperationalThreshold(rawTurbidity) {
//   const raw = extractNumber(rawTurbidity);

//   if (raw === null) {
//     return {
//       threshold: null,
//       basis: "No raw-water turbidity available"
//     };
//   }

//   if (raw <= 10) {
//     return {
//       threshold: 1.0,
//       basis: "Operational target based on low raw-water turbidity conditions"
//     };
//   }

//   if (raw <= 20) {
//     return {
//       threshold: 2.0,
//       basis: "Operational target based on moderate raw-water turbidity conditions"
//     };
//   }

//   return {
//     threshold: 2.0,
//     basis: "Conservative operational review target for higher raw-water turbidity"
//   };
// }

// function calculateRemovalEfficiency(rawTurbidity, predictedOutlet) {
//   const raw = extractNumber(rawTurbidity);
//   const pred = extractNumber(predictedOutlet);

//   if (raw === null || pred === null || raw <= 0) return null;

//   return ((raw - pred) / raw) * 100;
// }

// function updateCoagulationOperationalSummary(input, prediction) {
//   const raw = extractNumber(input?.ftu_raw_water);
//   const pred = extractNumber(prediction);

//   const targetInfo = getCoagulationOperationalThreshold(raw);
//   const efficiency = calculateRemovalEfficiency(raw, pred);

//   setText("coagulation-threshold", targetInfo.threshold, 2);
//   setText("coagulation-efficiency", efficiency, 1);

//   const thresholdBasis = document.getElementById("coagulation-threshold-basis");
//   if (thresholdBasis) thresholdBasis.textContent = targetInfo.basis;

//   return targetInfo;
// }

// function populateCoagulationRiskForms(payload) {
//   const mapping = {
//     risk_coag_ftu_raw_water: payload.ftu_raw_water,
//     risk_coag_fecl3_concentration: payload.fecl3_concentration,
//     risk_coag_temperature_raw_water: payload.temperature_raw_water,
//     risk_coag_ph_raw_water: payload.ph_raw_water,
//     risk_coag_after_dredging: payload.after_dredging,
//     risk_coag_lane: payload.lane,
//     risk_coag_year: payload.year
//   };

//   Object.entries(mapping).forEach(([id, value]) => {
//     const el = document.getElementById(id);
//     if (el && value !== undefined && value !== null) {
//       el.value = value;
//     }
//   });

//   const treatmentSelectors = {
//     'input[name="coagulation.ftu_raw_water"]': payload.ftu_raw_water,
//     'input[name="coagulation.fecl3_concentration"]': payload.fecl3_concentration,
//     'input[name="coagulation.temperature_raw_water"]': payload.temperature_raw_water,
//     'input[name="coagulation.ph_raw_water"]': payload.ph_raw_water,
//     'input[name="coagulation.after_dredging"]': payload.after_dredging,
//     'input[name="coagulation.lane"]': payload.lane,
//     'input[name="coagulation.year"]': payload.year,
//     'input[name="treatment.coagulation.ftu_raw_water"]': payload.ftu_raw_water,
//     'input[name="treatment.coagulation.fecl3_concentration"]': payload.fecl3_concentration,
//     'input[name="treatment.coagulation.temperature_raw_water"]': payload.temperature_raw_water,
//     'input[name="treatment.coagulation.ph_raw_water"]': payload.ph_raw_water,
//     'input[name="treatment.coagulation.after_dredging"]': payload.after_dredging,
//     'input[name="treatment.coagulation.lane"]': payload.lane,
//     'input[name="treatment.coagulation.year"]': payload.year
//   };

//   Object.entries(treatmentSelectors).forEach(([selector, value]) => {
//     const el = document.querySelector(selector);
//     if (el && value !== undefined && value !== null) {
//       el.value = value;
//     }
//   });
// }

// async function runAutomaticCoagulationRisk(payload) {
//   try {
//     populateCoagulationRiskForms(payload);
//     const data = await postJSON(ENDPOINTS.riskCoagulation, payload);

//     state.coagulation.lastRisk = data;

//     renderRichRisk("coagulation-risk-output", data);
//     renderRichRisk("risk-coagulation-output", data);

//     const riskClass = data?.overall_risk?.class || "–";
//     setBadge("coagulation-risk-badge", `Risk: ${riskClass}`, riskBadgeClass(riskClass));
//   } catch (err) {
//     renderJSON("coagulation-risk-output", { error: err.message });
//     renderJSON("risk-coagulation-output", { error: err.message });
//     setBadge("coagulation-risk-badge", "Risk: error", "high");
//   }
// }

// // ------------------------------
// // RL helpers
// // ------------------------------
// function syncRL5DisplayFromInputs() {
//   const current = Number(document.getElementById("rl5_current_fecl3_dose")?.value);
//   const recommended = Number(document.getElementById("rl5_recommended_fecl3_dose")?.value);
//   const confidence = Number(document.getElementById("rl5_confidence")?.value);

//   setText("rl5-current-dose-display", current, 2);
//   setText("rl5-recommended-dose-display", recommended, 2);
//   setText("rl5-confidence-display", confidence, 2);
// }

// function populateRL5RiskForms(payload) {
//   setValue("risk_rl_current_fecl3_dose", payload.current_fecl3_dose);
//   setValue("risk_rl_recommended_fecl3_dose", payload.recommended_fecl3_dose);
//   setValue("risk_rl_output_turbidity", payload.output_turbidity);
//   setValue("risk_rl_confidence", payload.confidence);

//   const treatmentSelectors = {
//     'input[name="rl.current_fecl3_dose"]': payload.current_fecl3_dose,
//     'input[name="rl.recommended_fecl3_dose"]': payload.recommended_fecl3_dose,
//     'input[name="rl.output_turbidity"]': payload.output_turbidity,
//     'input[name="rl.confidence"]': payload.confidence,
//     'input[name="treatment.rl.current_fecl3_dose"]': payload.current_fecl3_dose,
//     'input[name="treatment.rl.recommended_fecl3_dose"]': payload.recommended_fecl3_dose,
//     'input[name="treatment.rl.output_turbidity"]': payload.output_turbidity,
//     'input[name="treatment.rl.confidence"]': payload.confidence
//   };

//   Object.entries(treatmentSelectors).forEach(([selector, value]) => {
//     const el = document.querySelector(selector);
//     if (el && value !== undefined && value !== null) {
//       el.value = value;
//     }
//   });
// }

// function getRL5PayloadFromInputs() {
//   return {
//     current_fecl3_dose: Number(document.getElementById("rl5_current_fecl3_dose")?.value),
//     recommended_fecl3_dose: Number(document.getElementById("rl5_recommended_fecl3_dose")?.value),
//     output_turbidity: Number(document.getElementById("rl5_output_turbidity")?.value),
//     confidence: Number(document.getElementById("rl5_confidence")?.value)
//   };
// }

// async function runAutomaticRL5Risk(payload) {
//   try {
//     populateRL5RiskForms(payload);
//     const data = await postJSON(ENDPOINTS.riskRL5, payload);

//     state.rl5.lastInput = payload;
//     state.rl5.lastRisk = data;

//     renderRichRisk("rl5-risk-output", data);
//     renderRichRisk("risk-rl5-output", data);

//     const riskClass = data?.overall_risk?.class || "–";
//     setBadge("rl5-risk-badge", `Risk: ${riskClass}`, riskBadgeClass(riskClass));
//   } catch (err) {
//     renderJSON("rl5-risk-output", { error: err.message });
//     renderJSON("risk-rl5-output", { error: err.message });
//     setBadge("rl5-risk-badge", "Risk: error", "high");
//   }
// }

// // ------------------------------
// // Ozonation helpers
// // ------------------------------
// function populateOzonationRiskForms() {
//   const ct = state.ozonation.ctInput;
//   const bromate = state.ozonation.bromateInput;
//   const coliform = state.ozonation.coliformInput;

//   if (ct) {
//     const ctMap = {
//       'input[name="ct.Chamber"]': ct.Chamber,
//       'input[name="ct.WaterTemperature"]': ct.WaterTemperature,
//       'input[name="ct.RFTurbidity"]': ct.RFTurbidity,
//       'input[name="ct.FlowRate"]': ct.FlowRate,
//       'input[name="ct.Ozonedosage"]': ct.Ozonedosage,
//       'input[name="ozonation.ct.Chamber"]': ct.Chamber,
//       'input[name="ozonation.ct.WaterTemperature"]': ct.WaterTemperature,
//       'input[name="ozonation.ct.RFTurbidity"]': ct.RFTurbidity,
//       'input[name="ozonation.ct.FlowRate"]': ct.FlowRate,
//       'input[name="ozonation.ct.Ozonedosage"]': ct.Ozonedosage,
//       'input[name="treatment.ozonation.ct.Chamber"]': ct.Chamber,
//       'input[name="treatment.ozonation.ct.WaterTemperature"]': ct.WaterTemperature,
//       'input[name="treatment.ozonation.ct.RFTurbidity"]': ct.RFTurbidity,
//       'input[name="treatment.ozonation.ct.FlowRate"]': ct.FlowRate,
//       'input[name="treatment.ozonation.ct.Ozonedosage"]': ct.Ozonedosage
//     };

//     Object.entries(ctMap).forEach(([selector, value]) => {
//       const el = document.querySelector(selector);
//       if (el) el.value = value ?? "";
//     });
//   }

//   if (bromate) {
//     const brMap = {
//       'input[name="bromate.month"]': bromate.month,
//       'input[name="bromate.Chamber"]': bromate.Chamber,
//       'input[name="bromate.WaterTemperature"]': bromate.WaterTemperature,
//       'input[name="bromate.RFTurbidity"]': bromate.RFTurbidity,
//       'input[name="bromate.FlowRate"]': bromate.FlowRate,
//       'input[name="bromate.Ozonedosage"]': bromate.Ozonedosage,
//       'input[name="bromate.Residencetime"]': bromate.Residencetime,
//       'input[name="bromate.WaterTemperature_1"]': bromate.WaterTemperature_1,
//       'input[name="bromate.RFturbidity_1"]': bromate.RFturbidity_1,
//       'input[name="bromate.FlowRate_1"]': bromate.FlowRate_1,
//       'input[name="bromate.Ozonedosage_1"]': bromate.Ozonedosage_1,
//       'input[name="bromate.CT_All"]': bromate.CT_All,

//       'input[name="ozonation.bromate.month"]': bromate.month,
//       'input[name="ozonation.bromate.Chamber"]': bromate.Chamber,
//       'input[name="ozonation.bromate.WaterTemperature"]': bromate.WaterTemperature,
//       'input[name="ozonation.bromate.RFTurbidity"]': bromate.RFTurbidity,
//       'input[name="ozonation.bromate.FlowRate"]': bromate.FlowRate,
//       'input[name="ozonation.bromate.Ozonedosage"]': bromate.Ozonedosage,
//       'input[name="ozonation.bromate.Residencetime"]': bromate.Residencetime,
//       'input[name="ozonation.bromate.WaterTemperature_1"]': bromate.WaterTemperature_1,
//       'input[name="ozonation.bromate.RFturbidity_1"]': bromate.RFturbidity_1,
//       'input[name="ozonation.bromate.FlowRate_1"]': bromate.FlowRate_1,
//       'input[name="ozonation.bromate.Ozonedosage_1"]': bromate.Ozonedosage_1,
//       'input[name="ozonation.bromate.CT_All"]': bromate.CT_All,

//       'input[name="treatment.ozonation.bromate.month"]': bromate.month,
//       'input[name="treatment.ozonation.bromate.Chamber"]': bromate.Chamber,
//       'input[name="treatment.ozonation.bromate.WaterTemperature"]': bromate.WaterTemperature,
//       'input[name="treatment.ozonation.bromate.RFTurbidity"]': bromate.RFTurbidity,
//       'input[name="treatment.ozonation.bromate.FlowRate"]': bromate.FlowRate,
//       'input[name="treatment.ozonation.bromate.Ozonedosage"]': bromate.Ozonedosage,
//       'input[name="treatment.ozonation.bromate.Residencetime"]': bromate.Residencetime,
//       'input[name="treatment.ozonation.bromate.WaterTemperature_1"]': bromate.WaterTemperature_1,
//       'input[name="treatment.ozonation.bromate.RFturbidity_1"]': bromate.RFturbidity_1,
//       'input[name="treatment.ozonation.bromate.FlowRate_1"]': bromate.FlowRate_1,
//       'input[name="treatment.ozonation.bromate.Ozonedosage_1"]': bromate.Ozonedosage_1,
//       'input[name="treatment.ozonation.bromate.CT_All"]': bromate.CT_All
//     };

//     Object.entries(brMap).forEach(([selector, value]) => {
//       const el = document.querySelector(selector);
//       if (el) el.value = value ?? "";
//     });
//   }

//   if (coliform) {
//     const colMap = {
//       'input[name="coliform.Chamber"]': coliform.Chamber,
//       'input[name="coliform.WaterTemperature"]': coliform.WaterTemperature,
//       'input[name="coliform.RFTurbidity"]': coliform.RFTurbidity,
//       'input[name="coliform.FlowRate"]': coliform.FlowRate,
//       'input[name="coliform.Ozonedosage"]': coliform.Ozonedosage,
//       'input[name="coliform.RFturbidity_1"]': coliform.RFturbidity_1,
//       'input[name="coliform.CT_All"]': coliform.CT_All,

//       'input[name="ozonation.coliform.Chamber"]': coliform.Chamber,
//       'input[name="ozonation.coliform.WaterTemperature"]': coliform.WaterTemperature,
//       'input[name="ozonation.coliform.RFTurbidity"]': coliform.RFTurbidity,
//       'input[name="ozonation.coliform.FlowRate"]': coliform.FlowRate,
//       'input[name="ozonation.coliform.Ozonedosage"]': coliform.Ozonedosage,
//       'input[name="ozonation.coliform.RFturbidity_1"]': coliform.RFturbidity_1,
//       'input[name="ozonation.coliform.CT_All"]': coliform.CT_All,

//       'input[name="treatment.ozonation.coliform.Chamber"]': coliform.Chamber,
//       'input[name="treatment.ozonation.coliform.WaterTemperature"]': coliform.WaterTemperature,
//       'input[name="treatment.ozonation.coliform.RFTurbidity"]': coliform.RFTurbidity,
//       'input[name="treatment.ozonation.coliform.FlowRate"]': coliform.FlowRate,
//       'input[name="treatment.ozonation.coliform.Ozonedosage"]': coliform.Ozonedosage,
//       'input[name="treatment.ozonation.coliform.RFturbidity_1"]': coliform.RFturbidity_1,
//       'input[name="treatment.ozonation.coliform.CT_All"]': coliform.CT_All
//     };

//     Object.entries(colMap).forEach(([selector, value]) => {
//       const el = document.querySelector(selector);
//       if (el) el.value = value ?? "";
//     });
//   }
// }

// async function runAutomaticOzonationRisk() {
//   if (!state.ozonation.ctInput || !state.ozonation.bromateInput || !state.ozonation.coliformInput) {
//     return;
//   }

//   try {
//     populateOzonationRiskForms();

//     const payload = {
//       ct: state.ozonation.ctInput,
//       bromate: state.ozonation.bromateInput,
//       coliform: state.ozonation.coliformInput,
//       yopi_sensitive: true
//     };

//     const data = await postJSON(ENDPOINTS.riskOzonation, payload);
//     state.ozonation.combinedRisk = data;

//     renderRichRisk("ozonation-risk-output", data);
//     renderRichRisk("risk-ozonation-output", data);

//     const riskClass = data?.overall_risk?.class || "–";
//     setBadge("ozonation-risk-badge", `Risk: ${riskClass}`, riskBadgeClass(riskClass));
//   } catch (err) {
//     renderJSON("ozonation-risk-output", { error: err.message });
//     renderJSON("risk-ozonation-output", { error: err.message });
//     setBadge("ozonation-risk-badge", "Risk: error", "high");
//   }
// }

// // ------------------------------
// // Coagulation chart helpers
// // ------------------------------
// let coagulationLiveInterval = null;
// let coagulationHistoryLabels = [];
// let coagulationRawHistory = [];
// let coagulationHistoryValues = [];
// let coagulationThresholdHistory = [];

// function makeLineChart(canvasId, label) {
//   const canvas = document.getElementById(canvasId);
//   if (!canvas) return null;

//   return new Chart(canvas.getContext("2d"), {
//     type: "line",
//     data: {
//       labels: [],
//       datasets: [{
//         label,
//         data: [],
//         tension: 0.35,
//         fill: true,
//         borderWidth: 3,
//         pointRadius: 4
//       }]
//     },
//     options: {
//       responsive: true,
//       maintainAspectRatio: false
//     }
//   });
// }

// function makeBarChart(canvasId, label) {
//   const canvas = document.getElementById(canvasId);
//   if (!canvas) return null;

//   return new Chart(canvas.getContext("2d"), {
//     type: "bar",
//     data: {
//       labels: [label],
//       datasets: [{
//         label,
//         data: [0],
//         borderWidth: 1,
//         borderRadius: 10
//       }]
//     },
//     options: {
//       responsive: true,
//       maintainAspectRatio: false
//     }
//   });
// }

// function makeDoughnutChart(canvasId) {
//   const canvas = document.getElementById(canvasId);
//   if (!canvas) return null;

//   return new Chart(canvas.getContext("2d"), {
//     type: "doughnut",
//     data: {
//       labels: ["CT", "Bromate", "Coliform"],
//       datasets: [{
//         data: [0, 0, 0],
//         borderWidth: 1
//       }]
//     },
//     options: {
//       responsive: true,
//       maintainAspectRatio: false,
//       cutout: "68%"
//     }
//   });
// }

// const charts = {
//   coagulation: makeLineChart("chart-coagulation", "Coagulation prediction"),
//   ct: makeBarChart("chart-ct", "CT"),
//   bromate: makeBarChart("chart-bromate", "Bromate"),
//   coliform: makeBarChart("chart-coliform", "Coliform"),
//   ozonationSummary: makeDoughnutChart("chart-ozonation-summary")
// };

// function ensureCoagulationChartDatasets() {
//   if (!charts.coagulation) return;

//   const datasets = charts.coagulation.data.datasets;
//   if (datasets.length >= 3) return;

//   charts.coagulation.data.datasets = [
//     {
//       label: "Raw water turbidity",
//       data: [],
//       tension: 0.35,
//       fill: false,
//       borderWidth: 3,
//       pointRadius: 4
//     },
//     {
//       label: "Predicted outlet turbidity",
//       data: [],
//       tension: 0.35,
//       fill: true,
//       borderWidth: 3,
//       pointRadius: 4
//     },
//     {
//       label: "Operational target",
//       data: [],
//       tension: 0,
//       fill: false,
//       borderWidth: 2,
//       pointRadius: 0,
//       borderDash: [6, 4]
//     }
//   ];
// }

// function updateCoagulationChartSingle(label, raw, pred, threshold) {
//   if (!charts.coagulation) return;
//   ensureCoagulationChartDatasets();

//   charts.coagulation.data.labels = [label];
//   charts.coagulation.data.datasets[0].data = [raw ?? 0];
//   charts.coagulation.data.datasets[1].data = [pred ?? 0];
//   charts.coagulation.data.datasets[2].data = [threshold ?? 0];
//   charts.coagulation.update();
// }

// function updateCoagulationChartHistory(label, raw, pred, threshold) {
//   if (!charts.coagulation) return;
//   ensureCoagulationChartDatasets();

//   coagulationHistoryLabels.push(label);
//   coagulationRawHistory.push(raw ?? 0);
//   coagulationHistoryValues.push(pred ?? 0);
//   coagulationThresholdHistory.push(threshold ?? 0);

//   if (coagulationHistoryLabels.length > 12) {
//     coagulationHistoryLabels.shift();
//     coagulationRawHistory.shift();
//     coagulationHistoryValues.shift();
//     coagulationThresholdHistory.shift();
//   }

//   charts.coagulation.data.labels = coagulationHistoryLabels;
//   charts.coagulation.data.datasets[0].data = coagulationRawHistory;
//   charts.coagulation.data.datasets[1].data = coagulationHistoryValues;
//   charts.coagulation.data.datasets[2].data = coagulationThresholdHistory;
//   charts.coagulation.update();
// }

// ensureCoagulationChartDatasets();

// // ------------------------------
// // Static load buttons
// // ------------------------------
// document.getElementById("btn-source-overview")?.addEventListener("click", async () => {
//   try {
//     renderJSON("source-overview", await getJSON(ENDPOINTS.sourceOverview));
//   } catch (err) {
//     renderJSON("source-overview", { error: err.message });
//   }
// });

// document.getElementById("btn-source-latest")?.addEventListener("click", async () => {
//   try {
//     renderJSON("source-latest", await getJSON(ENDPOINTS.sourceLatest));
//   } catch (err) {
//     renderJSON("source-latest", { error: err.message });
//   }
// });

// document.getElementById("btn-treatment-overview")?.addEventListener("click", async () => {
//   try {
//     renderJSON("treatment-overview", await getJSON(ENDPOINTS.treatmentOverview));
//   } catch (err) {
//     renderJSON("treatment-overview", { error: err.message });
//   }
// });

// document.getElementById("btn-treatment-coag-latest")?.addEventListener("click", async () => {
//   try {
//     renderJSON("treatment-coag-latest", await getJSON(ENDPOINTS.treatmentCoagLatest));
//   } catch (err) {
//     renderJSON("treatment-coag-latest", { error: err.message });
//   }
// });

// document.getElementById("btn-rl5-latest")?.addEventListener("click", async () => {
//   try {
//     const data = await getJSON(ENDPOINTS.treatmentRLLatest);
//     renderJSON("rl5-latest", data);

//     const currentDose = extractNumber(data.current_fecl3_dose ?? data.current_dose);
//     const recommendedDose = extractNumber(data.recommended_fecl3_dose ?? data.recommended_dose);
//     const outputTurbidity = extractNumber(data.output_turbidity ?? data.predicted_output_turbidity);
//     const confidence = extractNumber(data.confidence);

//     if (currentDose !== null) setValue("rl5_current_fecl3_dose", currentDose);
//     if (recommendedDose !== null) setValue("rl5_recommended_fecl3_dose", recommendedDose);
//     if (outputTurbidity !== null) setValue("rl5_output_turbidity", outputTurbidity);
//     if (confidence !== null) setValue("rl5_confidence", confidence);

//     syncRL5DisplayFromInputs();

//     const payload = getRL5PayloadFromInputs();
//     if (
//       !Number.isNaN(payload.current_fecl3_dose) &&
//       !Number.isNaN(payload.recommended_fecl3_dose) &&
//       !Number.isNaN(payload.output_turbidity) &&
//       !Number.isNaN(payload.confidence)
//     ) {
//       await runAutomaticRL5Risk(payload);
//     }
//   } catch (err) {
//     renderJSON("rl5-latest", { error: err.message });
//   }
// });

// document.getElementById("btn-bactosense-latest")?.addEventListener("click", async () => {
//   try {
//     renderJSON("bactosense-latest", await getJSON(ENDPOINTS.treatmentBactoSense));
//   } catch (err) {
//     renderJSON("bactosense-latest", { error: err.message });
//   }
// });

// document.getElementById("btn-distribution-overview")?.addEventListener("click", async () => {
//   try {
//     renderJSON("distribution-overview", await getJSON(ENDPOINTS.distributionOverview));
//   } catch (err) {
//     renderJSON("distribution-overview", { error: err.message });
//   }
// });

// document.getElementById("btn-distribution-latest")?.addEventListener("click", async () => {
//   try {
//     renderJSON("distribution-latest", await getJSON(ENDPOINTS.distributionLatest));
//   } catch (err) {
//     renderJSON("distribution-latest", { error: err.message });
//   }
// });

// document.getElementById("btn-risk-overview")?.addEventListener("click", async () => {
//   try {
//     renderJSON("risk-overview", await getJSON(ENDPOINTS.riskOverview));
//   } catch (err) {
//     renderJSON("risk-overview", { error: err.message });
//   }
// });

// // ------------------------------
// // Demo prefills
// // ------------------------------
// document.getElementById("btn-coagulation-demo")?.addEventListener("click", () => {
//   setValue("coag_ftu_raw_water", 6.2);
//   setValue("coag_fecl3_concentration", 14.5);
//   setValue("coag_temperature_raw_water", 12.0);
//   setValue("coag_ph_raw_water", 7.4);
//   setValue("coag_after_dredging", 45);
//   setValue("coag_lane", 2);
//   setValue("coag_year", 2025);
// });

// document.getElementById("btn-rl5-demo")?.addEventListener("click", async () => {
//   const payload = {
//     current_fecl3_dose: 14.5,
//     recommended_fecl3_dose: 16.0,
//     output_turbidity: 5.4,
//     confidence: 0.75
//   };

//   setValue("rl5_current_fecl3_dose", payload.current_fecl3_dose);
//   setValue("rl5_recommended_fecl3_dose", payload.recommended_fecl3_dose);
//   setValue("rl5_output_turbidity", payload.output_turbidity);
//   setValue("rl5_confidence", payload.confidence);

//   syncRL5DisplayFromInputs();
//   await runAutomaticRL5Risk(payload);
// });

// document.getElementById("btn-ct-demo")?.addEventListener("click", () => {
//   setValue("ct_Chamber", 2);
//   setValue("ct_WaterTemperature", 11.5);
//   setValue("ct_RFTurbidity", 3.5);
//   setValue("ct_FlowRate", 1200);
//   setValue("ct_Ozonedosage", 1.8);
// });

// document.getElementById("btn-bromate-demo")?.addEventListener("click", () => {
//   setValue("br_month", 4);
//   setValue("br_Chamber", 2);
//   setValue("br_WaterTemperature", 11.5);
//   setValue("br_RFTurbidity", 3.5);
//   setValue("br_FlowRate", 1200);
//   setValue("br_Ozonedosage", 1.8);
//   setValue("br_Residencetime", 8.4);
//   setValue("br_WaterTemperature_1", 11.2);
//   setValue("br_RFturbidity_1", 3.3);
//   setValue("br_FlowRate_1", 1180);
//   setValue("br_Ozonedosage_1", 1.75);
//   setValue("br_CT_All", 0.55);
// });

// document.getElementById("btn-coliform-demo")?.addEventListener("click", () => {
//   setValue("col_Chamber", 2);
//   setValue("col_WaterTemperature", 11.5);
//   setValue("col_RFTurbidity", 3.5);
//   setValue("col_FlowRate", 1200);
//   setValue("col_Ozonedosage", 1.8);
//   setValue("col_RFturbidity_1", 3.3);
//   setValue("col_CT_All", 0.55);
// });

// // ------------------------------
// // RL display sync
// // ------------------------------
// ["rl5_current_fecl3_dose", "rl5_recommended_fecl3_dose", "rl5_confidence", "rl5_output_turbidity"].forEach((id) => {
//   document.getElementById(id)?.addEventListener("input", async () => {
//     syncRL5DisplayFromInputs();

//     const payload = getRL5PayloadFromInputs();
//     if (
//       !Number.isNaN(payload.current_fecl3_dose) &&
//       !Number.isNaN(payload.recommended_fecl3_dose) &&
//       !Number.isNaN(payload.output_turbidity) &&
//       !Number.isNaN(payload.confidence)
//     ) {
//       await runAutomaticRL5Risk(payload);
//     }
//   });
// });

// syncRL5DisplayFromInputs();

// // ------------------------------
// // Ozonation dashboard state
// // ------------------------------
// const latestOzonation = {
//   ct: null,
//   bromate: null,
//   coliform: null
// };

// function refreshOzonationDashboard() {
//   setText("dash-ct", latestOzonation.ct, 3);
//   setText("dash-bromate", latestOzonation.bromate, 3);
//   setText("dash-coliform", latestOzonation.coliform, 3);

//   const list = document.getElementById("dash-list");
//   if (list) {
//     const items = [];
//     if (latestOzonation.ct !== null) items.push("<li>CT prediction has been generated successfully.</li>");
//     if (latestOzonation.bromate !== null) items.push("<li>Bromate prediction has been generated successfully.</li>");
//     if (latestOzonation.coliform !== null) items.push("<li>Coliform prediction has been generated successfully.</li>");
//     if (!items.length) items.push("<li>No ozonation model has been run yet.</li>");
//     list.innerHTML = items.join("");
//   }

//   if (charts.ozonationSummary) {
//     charts.ozonationSummary.data.datasets[0].data = [
//       latestOzonation.ct ?? 0,
//       latestOzonation.bromate ?? 0,
//       latestOzonation.coliform ?? 0
//     ];
//     charts.ozonationSummary.update();
//   }
// }

// refreshOzonationDashboard();

// // ------------------------------
// // Coagulation manual/live
// // ------------------------------
// function stopCoagulationLiveMode() {
//   if (coagulationLiveInterval) {
//     clearInterval(coagulationLiveInterval);
//     coagulationLiveInterval = null;
//   }
//   setBadge("coagulation-mode-badge", "Mode: manual", "info");
// }

// document.getElementById("form-coagulation")?.addEventListener("submit", async (e) => {
//   e.preventDefault();

//   try {
//     const payload = formDataToObject(e.target);
//     const data = await postJSON(ENDPOINTS.coagulation, payload);

//     const pred = pickPrediction(data, ["prediction"]);
//     state.coagulation.lastInput = payload;
//     state.coagulation.lastPrediction = pred;

//     setText("coagulation-prediction", pred, 3);

//     const targetInfo = updateCoagulationOperationalSummary(payload, pred);
//     const status = classifyPrediction(pred, targetInfo.threshold ?? 1, (targetInfo.threshold ?? 1) + 1);

//     setText("coagulation-status", status, 0);
//     setBadge("coagulation-badge", `Status: ${status}`, levelFromText(status));
//     setBadge("coagulation-mode-badge", "Mode: manual", "info");
//     const lastUpdateEl = document.getElementById("coagulation-last-update");
//     if (lastUpdateEl) lastUpdateEl.textContent = "manual";

//     setText("live-ftu", payload.ftu_raw_water, 2);
//     setText("live-fecl3", payload.fecl3_concentration, 2);
//     setText("live-temp", payload.temperature_raw_water, 2);
//     setText("live-ph", payload.ph_raw_water, 2);
//     setText("live-dredging", payload.after_dredging, 0);
//     setText("live-lane", payload.lane, 0);
//     setText("live-year", payload.year, 0);

//     updateCoagulationChartSingle(
//       "Manual run",
//       extractNumber(payload.ftu_raw_water),
//       pred,
//       targetInfo.threshold
//     );

//     await runAutomaticCoagulationRisk(payload);
//   } catch (err) {
//     alert("Coagulation request failed: " + err.message);
//   }
// });

// async function updateLiveCoagulationOnce() {
//   try {
//     const data = await getJSON(ENDPOINTS.coagulationLive);
//     const pred = pickPrediction(data, ["prediction"]);
//     const input = data.input_data || {};
//     const timestamp = data.timestamp || "–";

//     state.coagulation.lastInput = input;
//     state.coagulation.lastPrediction = pred;

//     setText("coagulation-prediction", pred, 3);

//     const targetInfo = updateCoagulationOperationalSummary(input, pred);
//     const status = classifyPrediction(pred, targetInfo.threshold ?? 1, (targetInfo.threshold ?? 1) + 1);

//     setText("coagulation-status", status, 0);
//     setBadge("coagulation-badge", `Status: ${status}`, levelFromText(status));
//     setBadge("coagulation-mode-badge", "Mode: live", "info");
//     const lastUpdateEl = document.getElementById("coagulation-last-update");
//     if (lastUpdateEl) lastUpdateEl.textContent = timestamp;

//     setText("live-ftu", input.ftu_raw_water, 2);
//     setText("live-fecl3", input.fecl3_concentration, 2);
//     setText("live-temp", input.temperature_raw_water, 2);
//     setText("live-ph", input.ph_raw_water, 2);
//     setText("live-dredging", input.after_dredging, 0);
//     setText("live-lane", input.lane, 0);
//     setText("live-year", input.year, 0);

//     setValue("coag_ftu_raw_water", input.ftu_raw_water);
//     setValue("coag_fecl3_concentration", input.fecl3_concentration);
//     setValue("coag_temperature_raw_water", input.temperature_raw_water);
//     setValue("coag_ph_raw_water", input.ph_raw_water);
//     setValue("coag_after_dredging", input.after_dredging);
//     setValue("coag_lane", input.lane);
//     setValue("coag_year", input.year);

//     let shortLabel = timestamp;
//     try {
//       shortLabel = new Date(timestamp).toLocaleTimeString([], {
//         hour: "2-digit",
//         minute: "2-digit",
//         second: "2-digit"
//       });
//     } catch (_) {}

//     updateCoagulationChartHistory(
//       shortLabel,
//       extractNumber(input.ftu_raw_water),
//       pred,
//       targetInfo.threshold
//     );

//     await runAutomaticCoagulationRisk(input);
//   } catch (err) {
//     console.error(err);
//     setBadge("coagulation-badge", "Status: live error", "high");
//     setBadge("coagulation-risk-badge", "Risk: error", "high");
//   }
// }

// document.getElementById("btn-coagulation-live-start")?.addEventListener("click", async () => {
//   stopCoagulationLiveMode();
//   coagulationHistoryLabels = [];
//   coagulationRawHistory = [];
//   coagulationHistoryValues = [];
//   coagulationThresholdHistory = [];
//   await updateLiveCoagulationOnce();
//   coagulationLiveInterval = setInterval(updateLiveCoagulationOnce, 5000);
// });

// document.getElementById("btn-coagulation-live-stop")?.addEventListener("click", () => {
//   stopCoagulationLiveMode();
// });

// // ------------------------------
// // Ozonation forms
// // ------------------------------
// document.getElementById("form-ct")?.addEventListener("submit", async (e) => {
//   e.preventDefault();
//   try {
//     const payload = formDataToObject(e.target);

//     let data;
//     try {
//       data = await postJSON(ENDPOINTS.treatmentCT, payload);
//     } catch (_) {
//       data = await postJSON(ENDPOINTS.ct, payload);
//     }

//     const pred = pickPrediction(data, ["ct_prediction", "prediction"]);
//     state.ozonation.ctInput = payload;
//     state.ozonation.ctPrediction = pred;

//     setText("ct-prediction", pred, 3);

//     const status = classifyPrediction(pred, 0.3, 0.7);
//     setText("ct-status", status, 0);

//     if (charts.ct) {
//       charts.ct.data.datasets[0].data = [pred ?? 0];
//       charts.ct.update();
//     }

//     latestOzonation.ct = pred;
//     refreshOzonationDashboard();

//     await runAutomaticOzonationRisk();
//   } catch (err) {
//     alert("CT request failed: " + err.message);
//   }
// });

// document.getElementById("form-bromate")?.addEventListener("submit", async (e) => {
//   e.preventDefault();
//   try {
//     const payload = formDataToObject(e.target);

//     let data;
//     try {
//       data = await postJSON(ENDPOINTS.treatmentBromate, payload);
//     } catch (_) {
//       data = await postJSON(ENDPOINTS.bromate, payload);
//     }

//     const pred = pickPrediction(data, ["bromate_prediction", "prediction"]);
//     state.ozonation.bromateInput = payload;
//     state.ozonation.bromatePrediction = pred;

//     setText("bromate-prediction", pred, 3);

//     const status = classifyPrediction(pred, 3, 8);
//     setText("bromate-status", status, 0);

//     if (charts.bromate) {
//       charts.bromate.data.datasets[0].data = [pred ?? 0];
//       charts.bromate.update();
//     }

//     latestOzonation.bromate = pred;
//     refreshOzonationDashboard();

//     await runAutomaticOzonationRisk();
//   } catch (err) {
//     alert("Bromate request failed: " + err.message);
//   }
// });

// document.getElementById("form-coliform")?.addEventListener("submit", async (e) => {
//   e.preventDefault();
//   try {
//     const payload = formDataToObject(e.target);

//     let data;
//     try {
//       data = await postJSON(ENDPOINTS.treatmentColiform, payload);
//     } catch (_) {
//       data = await postJSON(ENDPOINTS.coliform, payload);
//     }

//     const pred = pickPrediction(data, ["coliform_prediction", "prediction"]);
//     state.ozonation.coliformInput = payload;
//     state.ozonation.coliformPrediction = pred;

//     setText("coliform-prediction", pred, 3);

//     const status = classifyInverse(pred, 1.5, 2.5);
//     setText("coliform-status", status, 0);

//     if (charts.coliform) {
//       charts.coliform.data.datasets[0].data = [pred ?? 0];
//       charts.coliform.update();
//     }

//     latestOzonation.coliform = pred;
//     refreshOzonationDashboard();

//     await runAutomaticOzonationRisk();
//   } catch (err) {
//     alert("Coliform request failed: " + err.message);
//   }
// });

// // ------------------------------
// // Risk forms - manual screens still work
// // ------------------------------
// document.getElementById("form-risk-source")?.addEventListener("submit", async (e) => {
//   e.preventDefault();
//   try {
//     const payload = normalizeBooleanStrings(formDataToObject(e.target));
//     const data = await postJSON(ENDPOINTS.riskSourceSose9, payload);
//     renderRichRisk("risk-source-output", data);
//   } catch (err) {
//     renderJSON("risk-source-output", { error: err.message });
//   }
// });

// document.getElementById("form-risk-coagulation")?.addEventListener("submit", async (e) => {
//   e.preventDefault();
//   try {
//     const payload = formDataToObject(e.target);
//     const data = await postJSON(ENDPOINTS.riskCoagulation, payload);
//     state.coagulation.lastRisk = data;
//     renderRichRisk("risk-coagulation-output", data);
//   } catch (err) {
//     renderJSON("risk-coagulation-output", { error: err.message });
//   }
// });

// document.getElementById("form-risk-rl5")?.addEventListener("submit", async (e) => {
//   e.preventDefault();
//   try {
//     const payload = normalizeBooleanStrings(formDataToObject(e.target));
//     const data = await postJSON(ENDPOINTS.riskRL5, payload);
//     state.rl5.lastRisk = data;
//     renderRichRisk("risk-rl5-output", data);
//   } catch (err) {
//     renderJSON("risk-rl5-output", { error: err.message });
//   }
// });

// document.getElementById("form-risk-ozonation")?.addEventListener("submit", async (e) => {
//   e.preventDefault();
//   try {
//     const payload = normalizeBooleanStrings(formDataToNestedObject(e.target));
//     const data = await postJSON(ENDPOINTS.riskOzonation, payload);
//     state.ozonation.combinedRisk = data;
//     renderRichRisk("risk-ozonation-output", data);
//   } catch (err) {
//     renderJSON("risk-ozonation-output", { error: err.message });
//   }
// });

// document.getElementById("form-risk-distribution")?.addEventListener("submit", async (e) => {
//   e.preventDefault();
//   try {
//     const payload = normalizeBooleanStrings(formDataToObject(e.target));
//     const data = await postJSON(ENDPOINTS.riskDistributionSose11, payload);
//     renderRichRisk("risk-distribution-output", data);
//   } catch (err) {
//     renderJSON("risk-distribution-output", { error: err.message });
//   }
// });

// document.getElementById("form-risk-treatment")?.addEventListener("submit", async (e) => {
//   e.preventDefault();
//   try {
//     const payload = normalizeBooleanStrings(formDataToNestedObject(e.target));
//     const data = await postJSON(ENDPOINTS.riskTreatmentCurrent, payload);
//     renderRichRisk("risk-treatment-output", data);
//   } catch (err) {
//     renderJSON("risk-treatment-output", { error: err.message });
//   }
// });

// document.getElementById("form-risk-system")?.addEventListener("submit", async (e) => {
//   e.preventDefault();
//   try {
//     const payload = normalizeBooleanStrings(formDataToNestedObject(e.target));
//     const data = await postJSON(ENDPOINTS.riskSystemCurrent, payload);
//     renderRichRisk("risk-system-output", data);
//   } catch (err) {
//     renderJSON("risk-system-output", { error: err.message });
//   }
// });

// // ==========================================
// // RWS HARD SENSORS
// // ==========================================
// // ==========================================
// // RWS HARD SENSORS + TIMESERIES
// // ==========================================

// const rwsCharts = {};

// const rwsParameters = [
//   "water_temperature",
//   "water_level",
//   "discharge"
// ];

// const rwsParameterLabels = {
//   water_temperature: "Water temperature",
//   water_level: "Water level",
//   discharge: "Discharge"
// };


// // ==========================================
// // LOAD LATEST VALUE
// // ==========================================

// async function loadRwsLatest(location, parameter) {

//   const url =
//     `${ENDPOINTS.rwsLatest}?location=${location}&parameter=${parameter}`;

//   return getJSON(url);
// }


// // ==========================================
// // LOAD TIMESERIES
// // ==========================================

// async function loadRwsTimeseries(
//   location,
//   parameter,
//   daysBack = 2
// ) {

//   const url =
//     `${ENDPOINTS.rwsTimeseries}?location=${location}&parameter=${parameter}&days_back=${daysBack}`;

//   return getJSON(url);
// }


// // ==========================================
// // RENDER LATEST
// // ==========================================

// function renderRwsLatest(
//   location,
//   parameter,
//   data
// ) {

//   const el =
//     document.getElementById(
//       `${location}-${parameter}-latest`
//     );

//   if (!el) return;

//   el.innerHTML = `
//     <span class="metric-label">
//       ${rwsParameterLabels[parameter]}
//     </span>

//     <strong class="metric-value">
//       ${data.latest_value ?? "–"}
//     </strong>

//     <div class="metric-unit">
//       ${data.unit ?? ""}
//     </div>

//     <div class="metric-unit">
//       Updated:
//       ${data.timestamp ?? "–"}
//     </div>
//   `;
// }


// // ==========================================
// // RENDER CHART
// // ==========================================

// function renderRwsChart(
//   location,
//   parameter,
//   data
// ) {

//   const canvasId =
//     `chart-${location}-${parameter}`;

//   const canvas =
//     document.getElementById(canvasId);

//   if (!canvas) return;

//   const labels =
//     data.timeseries.map(item => {

//       const d = new Date(item.timestamp);

//       return d.toLocaleString([], {
//         day: "2-digit",
//         month: "2-digit",
//         hour: "2-digit",
//         minute: "2-digit"
//       });
//     });

//   const values =
//     data.timeseries.map(item => item.value);

//   if (rwsCharts[canvasId]) {
//     rwsCharts[canvasId].destroy();
//   }

//   rwsCharts[canvasId] =
//     new Chart(canvas.getContext("2d"), {

//       type: "line",

//       data: {
//         labels,

//         datasets: [{
//           label:
//             `${data.label} (${data.unit})`,

//           data: values,

//           tension: 0.3,
//           fill: false,
//           borderWidth: 2,
//           pointRadius: 0
//         }]
//       },

//       options: {
//         responsive: true,
//         maintainAspectRatio: false,

//         interaction: {
//           mode: "index",
//           intersect: false
//         },

//         plugins: {
//           legend: {
//             display: true
//           }
//         },

//         scales: {
//           x: {
//             ticks: {
//               maxTicksLimit: 8
//             }
//           }
//         }
//       }
//     });
// }


// // ==========================================
// // LOAD WHOLE STATION DASHBOARD
// // ==========================================

// async function loadRwsStationDashboard(
//   location
// ) {

//   for (const parameter of rwsParameters) {

//     try {

//       // latest
//       const latest =
//         await loadRwsLatest(
//           location,
//           parameter
//         );

//       renderRwsLatest(
//         location,
//         parameter,
//         latest
//       );

//       // timeseries
//       const timeseries =
//         await loadRwsTimeseries(
//           location,
//           parameter,
//           2
//         );

//       renderRwsChart(
//         location,
//         parameter,
//         timeseries
//       );

//     } catch (err) {

//       const el =
//         document.getElementById(
//           `${location}-${parameter}-latest`
//         );

//       if (el) {

//         el.innerHTML = `
//           <span class="metric-label">
//             ${rwsParameterLabels[parameter]}
//           </span>

//           <strong class="metric-value small">
//             Error
//           </strong>

//           <div class="metric-unit">
//             ${err.message}
//           </div>
//         `;
//       }
//     }
//   }
// }


// // ==========================================
// // AUTO REFRESH
// // ==========================================

// let currentRwsLocation = null;

// function startRwsAutoRefresh(location) {

//   currentRwsLocation = location;

//   loadRwsStationDashboard(location);

//   if (window.rwsRefreshInterval) {
//     clearInterval(window.rwsRefreshInterval);
//   }

//   window.rwsRefreshInterval =
//     setInterval(() => {

//       if (currentRwsLocation) {

//         loadRwsStationDashboard(
//           currentRwsLocation
//         );
//       }

//     }, 300000); // 5 min
// }
