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
  treatmentCT: "/treatment/ozonation/ct",
  treatmentBromate: "/treatment/ozonation/bromate",
  treatmentColiform: "/treatment/ozonation/coliform",
  treatmentBactoSense: "/treatment/hard-sensors/bactosense-4/latest",

  distributionOverview: "/distribution/overview",
  distributionLatest: "/distribution/sose-11/latest",

  riskOverview: "/risk/overview",
  riskSourceSose9: "/risk/source/sose-9/current",
  riskCoagulation: "/risk/coagulation",
  riskRL4: "/risk/treatment/rl-4/current",
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
  "screen-risk-rl4": "RL #4 Dosage Risk",
  "screen-risk-ozonation": "Combined Ozonation Risk",
  "screen-risk-distribution": "SoSe #11 Distribution Risk",
  "screen-risk-treatment": "Treatment Current Risk",
  "screen-risk-system": "Source-to-Tap System Risk"
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
// Charts
// ------------------------------
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
  document.getElementById("coag_ftu_raw_water").value = 6.2;
  document.getElementById("coag_fecl3_concentration").value = 14.5;
  document.getElementById("coag_temperature_raw_water").value = 12.0;
  document.getElementById("coag_ph_raw_water").value = 7.4;
  document.getElementById("coag_after_dredging").value = 45;
  document.getElementById("coag_lane").value = 2;
  document.getElementById("coag_year").value = 2025;
});

document.getElementById("btn-ct-demo")?.addEventListener("click", () => {
  document.getElementById("ct_Chamber").value = 2;
  document.getElementById("ct_WaterTemperature").value = 11.5;
  document.getElementById("ct_RFTurbidity").value = 3.5;
  document.getElementById("ct_FlowRate").value = 1200;
  document.getElementById("ct_Ozonedosage").value = 1.8;
});

document.getElementById("btn-bromate-demo")?.addEventListener("click", () => {
  document.getElementById("br_month").value = 4;
  document.getElementById("br_Chamber").value = 2;
  document.getElementById("br_WaterTemperature").value = 11.5;
  document.getElementById("br_RFTurbidity").value = 3.5;
  document.getElementById("br_FlowRate").value = 1200;
  document.getElementById("br_Ozonedosage").value = 1.8;
  document.getElementById("br_Residencetime").value = 8.4;
  document.getElementById("br_WaterTemperature_1").value = 11.2;
  document.getElementById("br_RFturbidity_1").value = 3.3;
  document.getElementById("br_FlowRate_1").value = 1180;
  document.getElementById("br_Ozonedosage_1").value = 1.75;
  document.getElementById("br_CT_All").value = 0.55;
});

document.getElementById("btn-coliform-demo")?.addEventListener("click", () => {
  document.getElementById("col_Chamber").value = 2;
  document.getElementById("col_WaterTemperature").value = 11.5;
  document.getElementById("col_RFTurbidity").value = 3.5;
  document.getElementById("col_FlowRate").value = 1200;
  document.getElementById("col_Ozonedosage").value = 1.8;
  document.getElementById("col_RFturbidity_1").value = 3.3;
  document.getElementById("col_CT_All").value = 0.55;
});

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
let coagulationLiveInterval = null;
let coagulationHistoryLabels = [];
let coagulationHistoryValues = [];

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
    setText("coagulation-prediction", pred, 3);

    const status = classifyPrediction(pred, 2, 5);
    setText("coagulation-status", status, 0);
    setBadge("coagulation-badge", `Status: ${status}`, levelFromText(status));
    setBadge("coagulation-mode-badge", "Mode: manual", "info");
    document.getElementById("coagulation-last-update").textContent = "manual";

    document.getElementById("live-ftu").textContent = payload.ftu_raw_water;
    document.getElementById("live-fecl3").textContent = payload.fecl3_concentration;
    document.getElementById("live-temp").textContent = payload.temperature_raw_water;
    document.getElementById("live-ph").textContent = payload.ph_raw_water;
    document.getElementById("live-dredging").textContent = payload.after_dredging;
    document.getElementById("live-lane").textContent = payload.lane;
    document.getElementById("live-year").textContent = payload.year;

    if (charts.coagulation) {
      charts.coagulation.data.labels = ["Manual run"];
      charts.coagulation.data.datasets[0].data = [pred ?? 0];
      charts.coagulation.update();
    }
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

    setText("coagulation-prediction", pred, 3);

    const status = classifyPrediction(pred, 2, 5);
    setText("coagulation-status", status, 0);
    setBadge("coagulation-badge", `Status: ${status}`, levelFromText(status));
    setBadge("coagulation-mode-badge", "Mode: live", "info");
    document.getElementById("coagulation-last-update").textContent = timestamp;

    document.getElementById("live-ftu").textContent = input.ftu_raw_water ?? "–";
    document.getElementById("live-fecl3").textContent = input.fecl3_concentration ?? "–";
    document.getElementById("live-temp").textContent = input.temperature_raw_water ?? "–";
    document.getElementById("live-ph").textContent = input.ph_raw_water ?? "–";
    document.getElementById("live-dredging").textContent = input.after_dredging ?? "–";
    document.getElementById("live-lane").textContent = input.lane ?? "–";
    document.getElementById("live-year").textContent = input.year ?? "–";

    const ftu = document.getElementById("coag_ftu_raw_water");
    const fecl3 = document.getElementById("coag_fecl3_concentration");
    const temp = document.getElementById("coag_temperature_raw_water");
    const ph = document.getElementById("coag_ph_raw_water");
    const dredging = document.getElementById("coag_after_dredging");
    const lane = document.getElementById("coag_lane");
    const year = document.getElementById("coag_year");

    if (ftu) ftu.value = input.ftu_raw_water ?? "";
    if (fecl3) fecl3.value = input.fecl3_concentration ?? "";
    if (temp) temp.value = input.temperature_raw_water ?? "";
    if (ph) ph.value = input.ph_raw_water ?? "";
    if (dredging) dredging.value = input.after_dredging ?? "";
    if (lane && input.lane !== undefined) lane.value = input.lane;
    if (year) year.value = input.year ?? "";

    let shortLabel = timestamp;
    try {
      shortLabel = new Date(timestamp).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
      });
    } catch (_) {}

    coagulationHistoryLabels.push(shortLabel);
    coagulationHistoryValues.push(pred);

    if (coagulationHistoryLabels.length > 12) {
      coagulationHistoryLabels.shift();
      coagulationHistoryValues.shift();
    }

    if (charts.coagulation) {
      charts.coagulation.data.labels = coagulationHistoryLabels;
      charts.coagulation.data.datasets[0].data = coagulationHistoryValues;
      charts.coagulation.update();
    }
  } catch (err) {
    console.error(err);
    setBadge("coagulation-badge", "Status: live error", "high");
  }
}

document.getElementById("btn-coagulation-live-start")?.addEventListener("click", async () => {
  stopCoagulationLiveMode();
  coagulationHistoryLabels = [];
  coagulationHistoryValues = [];
  await updateLiveCoagulationOnce();
  coagulationLiveInterval = setInterval(updateLiveCoagulationOnce, 5000);
});

document.getElementById("btn-coagulation-live-stop")?.addEventListener("click", () => {
  stopCoagulationLiveMode();
});

// ------------------------------
// Treatment ozonation forms
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
    setText("ct-prediction", pred, 3);

    const status = classifyPrediction(pred, 0.3, 0.7);
    setText("ct-status", status, 0);

    if (charts.ct) {
      charts.ct.data.datasets[0].data = [pred ?? 0];
      charts.ct.update();
    }

    latestOzonation.ct = pred;
    refreshOzonationDashboard();
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
    setText("bromate-prediction", pred, 3);

    const status = classifyPrediction(pred, 3, 8);
    setText("bromate-status", status, 0);

    if (charts.bromate) {
      charts.bromate.data.datasets[0].data = [pred ?? 0];
      charts.bromate.update();
    }

    latestOzonation.bromate = pred;
    refreshOzonationDashboard();
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
    setText("coliform-prediction", pred, 3);

    const status = classifyInverse(pred, 1.5, 2.5);
    setText("coliform-status", status, 0);

    if (charts.coliform) {
      charts.coliform.data.datasets[0].data = [pred ?? 0];
      charts.coliform.update();
    }

    latestOzonation.coliform = pred;
    refreshOzonationDashboard();
  } catch (err) {
    alert("Coliform request failed: " + err.message);
  }
});

// ------------------------------
// Risk forms
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
    renderRichRisk("risk-coagulation-output", data);
  } catch (err) {
    renderJSON("risk-coagulation-output", { error: err.message });
  }
});

document.getElementById("form-risk-rl4")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = normalizeBooleanStrings(formDataToObject(e.target));
    const data = await postJSON(ENDPOINTS.riskRL4, payload);
    renderRichRisk("risk-rl4-output", data);
  } catch (err) {
    renderJSON("risk-rl4-output", { error: err.message });
  }
});

document.getElementById("form-risk-ozonation")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = normalizeBooleanStrings(formDataToNestedObject(e.target));
    const data = await postJSON(ENDPOINTS.riskOzonation, payload);
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
// const ENDPOINTS = {
//   sourceOverview: "/source/overview",
//   sourceLatest: "/source/sose-1/latest",

//   treatmentOverview: "/treatment/overview",
//   treatmentCoagLatest: "/treatment/coagulation/latest",
//   treatmentCT: "/treatment/ozonation/ct",
//   treatmentBromate: "/treatment/ozonation/bromate",
//   treatmentColiform: "/treatment/ozonation/coliform",
//   treatmentBactoSense: "/treatment/hard-sensors/bactosense-4/latest",

//   distributionOverview: "/distribution/overview",
//   distributionLatest: "/distribution/sose-4/latest",

//   riskOverview: "/risk/overview",
//   riskCoagulation: "/risk/coagulation",
//   riskOzonation: "/risk/ozonation/current"
// };

// const breadcrumbs = document.getElementById("breadcrumbs");

// const screenTitles = {
//   "screen-home": "Home",
//   "screen-source": "Source Module",
//   "screen-treatment": "Treatment Module",
//   "screen-treatment-overview": "Treatment Overview",
//   "screen-coagulation": "Coagulation Prediction",
//   "screen-ozonation": "Ozonation Models",
//   "screen-ct": "CT Prediction",
//   "screen-bromate": "Bromate Prediction",
//   "screen-coliform": "Coliform Prediction",
//   "screen-ozonation-dashboard": "Ozonation Dashboard",
//   "screen-hard-sensors": "Hard Sensor Placeholder",
//   "screen-distribution": "Distribution Module",
//   "screen-risk": "Risk Module",
//   "screen-risk-overview": "Risk Overview",
//   "screen-risk-coagulation": "Coagulation Risk",
//   "screen-risk-ozonation": "Combined Ozonation Risk"
// };

// function showScreen(id) {
//   document.querySelectorAll(".screen").forEach((screen) => {
//     screen.classList.remove("active");
//   });
//   const target = document.getElementById(id);
//   if (target) target.classList.add("active");
//   updateBreadcrumbs(id);
//   window.scrollTo({ top: 0, behavior: "smooth" });
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
//   if (text === "High") return "high";
//   return "info";
// }

// // ------------------------------
// // Charts
// // ------------------------------
// function makeLineChart(canvasId, label, labels, data) {
//   const ctx = document.getElementById(canvasId).getContext("2d");
//   return new Chart(ctx, {
//     type: "line",
//     data: {
//       labels,
//       datasets: [{
//         label,
//         data,
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
//   const ctx = document.getElementById(canvasId).getContext("2d");
//   return new Chart(ctx, {
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
//   const ctx = document.getElementById(canvasId).getContext("2d");
//   return new Chart(ctx, {
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
//   coagulation: makeLineChart("chart-coagulation", "Coagulation prediction", [], []),
//   ct: makeBarChart("chart-ct", "CT"),
//   bromate: makeBarChart("chart-bromate", "Bromate"),
//   coliform: makeBarChart("chart-coliform", "Coliform"),
//   ozonationSummary: makeDoughnutChart("chart-ozonation-summary")
// };

// // ------------------------------
// // Static load buttons
// // ------------------------------
// document.getElementById("btn-source-overview")?.addEventListener("click", async () => {
//   try { renderJSON("source-overview", await getJSON(ENDPOINTS.sourceOverview)); }
//   catch (err) { renderJSON("source-overview", { error: err.message }); }
// });

// document.getElementById("btn-source-latest")?.addEventListener("click", async () => {
//   try { renderJSON("source-latest", await getJSON(ENDPOINTS.sourceLatest)); }
//   catch (err) { renderJSON("source-latest", { error: err.message }); }
// });

// document.getElementById("btn-treatment-overview")?.addEventListener("click", async () => {
//   try { renderJSON("treatment-overview", await getJSON(ENDPOINTS.treatmentOverview)); }
//   catch (err) { renderJSON("treatment-overview", { error: err.message }); }
// });

// document.getElementById("btn-treatment-coag-latest")?.addEventListener("click", async () => {
//   try { renderJSON("treatment-coag-latest", await getJSON(ENDPOINTS.treatmentCoagLatest)); }
//   catch (err) { renderJSON("treatment-coag-latest", { error: err.message }); }
// });

// document.getElementById("btn-bactosense-latest")?.addEventListener("click", async () => {
//   try { renderJSON("bactosense-latest", await getJSON(ENDPOINTS.treatmentBactoSense)); }
//   catch (err) { renderJSON("bactosense-latest", { error: err.message }); }
// });

// document.getElementById("btn-distribution-overview")?.addEventListener("click", async () => {
//   try { renderJSON("distribution-overview", await getJSON(ENDPOINTS.distributionOverview)); }
//   catch (err) { renderJSON("distribution-overview", { error: err.message }); }
// });

// document.getElementById("btn-distribution-latest")?.addEventListener("click", async () => {
//   try { renderJSON("distribution-latest", await getJSON(ENDPOINTS.distributionLatest)); }
//   catch (err) { renderJSON("distribution-latest", { error: err.message }); }
// });

// document.getElementById("btn-risk-overview")?.addEventListener("click", async () => {
//   try { renderJSON("risk-overview", await getJSON(ENDPOINTS.riskOverview)); }
//   catch (err) { renderJSON("risk-overview", { error: err.message }); }
// });

// // ------------------------------
// // Demo prefills
// // ------------------------------
// document.getElementById("btn-coagulation-demo")?.addEventListener("click", () => {
//   document.getElementById("coag_ftu_raw_water").value = 6.2;
//   document.getElementById("coag_fecl3_concentration").value = 14.5;
//   document.getElementById("coag_temperature_raw_water").value = 12.0;
//   document.getElementById("coag_ph_raw_water").value = 7.4;
//   document.getElementById("coag_after_dredging").value = 45;
//   document.getElementById("coag_lane").value = 2;
//   document.getElementById("coag_year").value = 2025;
// });

// document.getElementById("btn-ct-demo")?.addEventListener("click", () => {
//   document.getElementById("ct_Chamber").value = 2;
//   document.getElementById("ct_WaterTemperature").value = 11.5;
//   document.getElementById("ct_RFTurbidity").value = 3.5;
//   document.getElementById("ct_FlowRate").value = 1200;
//   document.getElementById("ct_Ozonedosage").value = 1.8;
// });

// document.getElementById("btn-bromate-demo")?.addEventListener("click", () => {
//   document.getElementById("br_month").value = 4;
//   document.getElementById("br_Chamber").value = 2;
//   document.getElementById("br_WaterTemperature").value = 11.5;
//   document.getElementById("br_RFTurbidity").value = 3.5;
//   document.getElementById("br_FlowRate").value = 1200;
//   document.getElementById("br_Ozonedosage").value = 1.8;
//   document.getElementById("br_Residencetime").value = 8.4;
//   document.getElementById("br_WaterTemperature_1").value = 11.2;
//   document.getElementById("br_RFturbidity_1").value = 3.3;
//   document.getElementById("br_FlowRate_1").value = 1180;
//   document.getElementById("br_Ozonedosage_1").value = 1.75;
//   document.getElementById("br_CT_All").value = 0.55;
// });

// document.getElementById("btn-coliform-demo")?.addEventListener("click", () => {
//   document.getElementById("col_Chamber").value = 2;
//   document.getElementById("col_WaterTemperature").value = 11.5;
//   document.getElementById("col_RFTurbidity").value = 3.5;
//   document.getElementById("col_FlowRate").value = 1200;
//   document.getElementById("col_Ozonedosage").value = 1.8;
//   document.getElementById("col_RFturbidity_1").value = 3.3;
//   document.getElementById("col_CT_All").value = 0.55;
// });

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
//   const items = [];

//   if (latestOzonation.ct !== null) items.push("<li>CT prediction has been generated successfully.</li>");
//   if (latestOzonation.bromate !== null) items.push("<li>Bromate prediction has been generated successfully.</li>");
//   if (latestOzonation.coliform !== null) items.push("<li>Coliform prediction has been generated successfully.</li>");
//   if (!items.length) items.push("<li>No ozonation model has been run yet.</li>");

//   list.innerHTML = items.join("");
//   charts.ozonationSummary.data.datasets[0].data = [
//     latestOzonation.ct ?? 0,
//     latestOzonation.bromate ?? 0,
//     latestOzonation.coliform ?? 0
//   ];
//   charts.ozonationSummary.update();
// }

// refreshOzonationDashboard();

// // ------------------------------
// // Coagulation manual/live
// // ------------------------------
// let coagulationLiveInterval = null;
// let coagulationHistoryLabels = [];
// let coagulationHistoryValues = [];

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
//     const data = await postJSON("/predict/coagulation", payload);

//     const pred = extractNumber(data.prediction);
//     setText("coagulation-prediction", pred, 3);

//     const status = classifyPrediction(pred, 2, 5);
//     setText("coagulation-status", status, 0);
//     setBadge("coagulation-badge", `Status: ${status}`, levelFromText(status));
//     setBadge("coagulation-mode-badge", "Mode: manual", "info");
//     document.getElementById("coagulation-last-update").textContent = "manual";

//     document.getElementById("live-ftu").textContent = payload.ftu_raw_water;
//     document.getElementById("live-fecl3").textContent = payload.fecl3_concentration;
//     document.getElementById("live-temp").textContent = payload.temperature_raw_water;
//     document.getElementById("live-ph").textContent = payload.ph_raw_water;
//     document.getElementById("live-dredging").textContent = payload.after_dredging;
//     document.getElementById("live-lane").textContent = payload.lane;
//     document.getElementById("live-year").textContent = payload.year;

//     charts.coagulation.data.labels = ["Manual run"];
//     charts.coagulation.data.datasets[0].data = [pred ?? 0];
//     charts.coagulation.update();
//   } catch (err) {
//     alert("Coagulation request failed: " + err.message);
//   }
// });

// async function updateLiveCoagulationOnce() {
//   try {
//     const data = await getJSON("/predict/coagulation/live");
//     const pred = extractNumber(data.prediction);
//     const input = data.input_data || {};
//     const timestamp = data.timestamp || "–";

//     setText("coagulation-prediction", pred, 3);

//     const status = classifyPrediction(pred, 2, 5);
//     setText("coagulation-status", status, 0);
//     setBadge("coagulation-badge", `Status: ${status}`, levelFromText(status));
//     setBadge("coagulation-mode-badge", "Mode: live", "info");
//     document.getElementById("coagulation-last-update").textContent = timestamp;

//     document.getElementById("live-ftu").textContent = input.ftu_raw_water ?? "–";
//     document.getElementById("live-fecl3").textContent = input.fecl3_concentration ?? "–";
//     document.getElementById("live-temp").textContent = input.temperature_raw_water ?? "–";
//     document.getElementById("live-ph").textContent = input.ph_raw_water ?? "–";
//     document.getElementById("live-dredging").textContent = input.after_dredging ?? "–";
//     document.getElementById("live-lane").textContent = input.lane ?? "–";
//     document.getElementById("live-year").textContent = input.year ?? "–";

//     let shortLabel = timestamp;
//     try {
//       shortLabel = new Date(timestamp).toLocaleTimeString([], {
//         hour: "2-digit",
//         minute: "2-digit",
//         second: "2-digit"
//       });
//     } catch (_) {}

//     coagulationHistoryLabels.push(shortLabel);
//     coagulationHistoryValues.push(pred);

//     if (coagulationHistoryLabels.length > 12) {
//       coagulationHistoryLabels.shift();
//       coagulationHistoryValues.shift();
//     }

//     charts.coagulation.data.labels = coagulationHistoryLabels;
//     charts.coagulation.data.datasets[0].data = coagulationHistoryValues;
//     charts.coagulation.update();
//   } catch (err) {
//     setBadge("coagulation-badge", "Status: live error", "high");
//   }
// }

// document.getElementById("btn-coagulation-live-start")?.addEventListener("click", async () => {
//   stopCoagulationLiveMode();
//   coagulationHistoryLabels = [];
//   coagulationHistoryValues = [];
//   await updateLiveCoagulationOnce();
//   coagulationLiveInterval = setInterval(updateLiveCoagulationOnce, 5000);
// });

// document.getElementById("btn-coagulation-live-stop")?.addEventListener("click", () => {
//   stopCoagulationLiveMode();
// });

// // ------------------------------
// // Treatment ozonation forms
// // ------------------------------
// document.getElementById("form-ct")?.addEventListener("submit", async (e) => {
//   e.preventDefault();
//   try {
//     const payload = formDataToObject(e.target);
//     const data = await postJSON(ENDPOINTS.treatmentCT, payload);

//     const pred = extractNumber(data.prediction);
//     setText("ct-prediction", pred, 3);

//     const status = classifyPrediction(pred, 0.3, 0.7);
//     setText("ct-status", status, 0);

//     charts.ct.data.datasets[0].data = [pred ?? 0];
//     charts.ct.update();

//     latestOzonation.ct = pred;
//     refreshOzonationDashboard();
//   } catch (err) {
//     alert("CT request failed: " + err.message);
//   }
// });

// document.getElementById("form-bromate")?.addEventListener("submit", async (e) => {
//   e.preventDefault();
//   try {
//     const payload = formDataToObject(e.target);
//     const data = await postJSON(ENDPOINTS.treatmentBromate, payload);

//     const pred = extractNumber(data.prediction);
//     setText("bromate-prediction", pred, 3);

//     const status = classifyPrediction(pred, 3, 8);
//     setText("bromate-status", status, 0);

//     charts.bromate.data.datasets[0].data = [pred ?? 0];
//     charts.bromate.update();

//     latestOzonation.bromate = pred;
//     refreshOzonationDashboard();
//   } catch (err) {
//     alert("Bromate request failed: " + err.message);
//   }
// });

// document.getElementById("form-coliform")?.addEventListener("submit", async (e) => {
//   e.preventDefault();
//   try {
//     const payload = formDataToObject(e.target);
//     const data = await postJSON(ENDPOINTS.treatmentColiform, payload);

//     const pred = extractNumber(data.prediction);
//     setText("coliform-prediction", pred, 3);

//     const status = classifyInverse(pred, 1.5, 2.5);
//     setText("coliform-status", status, 0);

//     charts.coliform.data.datasets[0].data = [pred ?? 0];
//     charts.coliform.update();

//     latestOzonation.coliform = pred;
//     refreshOzonationDashboard();
//   } catch (err) {
//     alert("Coliform request failed: " + err.message);
//   }
// });

// // ------------------------------
// // Risk forms
// // ------------------------------
// document.getElementById("form-risk-coagulation")?.addEventListener("submit", async (e) => {
//   e.preventDefault();
//   try {
//     const payload = formDataToObject(e.target);
//     const data = await postJSON(ENDPOINTS.riskCoagulation, payload);
//     renderJSON("risk-coagulation-output", data);
//   } catch (err) {
//     renderJSON("risk-coagulation-output", { error: err.message });
//   }
// });

// document.getElementById("form-risk-ozonation")?.addEventListener("submit", async (e) => {
//   e.preventDefault();
//   try {
//     const payload = formDataToNestedObject(e.target);
//     const data = await postJSON(ENDPOINTS.riskOzonation, payload);
//     renderJSON("risk-ozonation-output", data);
//   } catch (err) {
//     renderJSON("risk-ozonation-output", { error: err.message });
//   }
// });