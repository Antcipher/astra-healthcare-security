"use strict";

const elements = {
  status: document.querySelector("#status-banner"),
  service: document.querySelector("#service-status"),
  devices: document.querySelector("#device-count"),
  openAlerts: document.querySelector("#open-alert-count"),
  events: document.querySelector("#event-count"),
  telemetryRows: document.querySelector("#telemetry-rows"),
  alertList: document.querySelector("#alert-list"),
  simulateButton: document.querySelector("#simulate-button"),
};

function setStatus(message, kind = "info") {
  elements.status.textContent = message;
  elements.status.className = `status-banner status-${kind}`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[character]);
}

function formatTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Unknown time" : date.toLocaleString();
}

async function requestJson(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { Accept: "application/json", ...options.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

function renderTelemetry(items) {
  elements.telemetryRows.replaceChildren();
  if (items.length === 0) {
    elements.telemetryRows.innerHTML =
      '<tr><td class="empty-state" colspan="4">No telemetry recorded.</td></tr>';
    return;
  }

  for (const item of items) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${escapeHtml(formatTime(item.observed_at))}</td>
      <td><span class="device-name">${escapeHtml(item.device_id)}</span></td>
      <td>${escapeHtml(item.value)} ${escapeHtml(item.unit)}</td>
      <td>${escapeHtml(item.source_network)}</td>
    `;
    elements.telemetryRows.append(row);
  }
}

function renderAlerts(items) {
  elements.alertList.replaceChildren();
  if (items.length === 0) {
    elements.alertList.innerHTML =
      '<p class="empty-state">No rule findings in the current event history.</p>';
    return;
  }

  for (const alert of items) {
    const card = document.createElement("article");
    card.className = `alert-card severity-${escapeHtml(alert.severity)}`;
    const reviewButton = alert.status === "open"
      ? `<button class="button button-small" type="button"
           data-acknowledge="${escapeHtml(alert.id)}">Acknowledge</button>`
      : '<span class="acknowledged-label">Acknowledged</span>';
    card.innerHTML = `
      <div class="alert-topline">
        <span class="severity-label">${escapeHtml(alert.severity)}</span>
        <time datetime="${escapeHtml(alert.created_at)}">${escapeHtml(formatTime(alert.created_at))}</time>
      </div>
      <h3>${escapeHtml(alert.title)}</h3>
      <p>${escapeHtml(alert.description)}</p>
      <p class="recommendation"><strong>Suggested review:</strong>
        ${escapeHtml(alert.recommended_action)}</p>
      <div class="alert-actions">${reviewButton}</div>
    `;
    elements.alertList.append(card);
  }
}

async function refreshDashboard() {
  try {
    const [health, telemetry, alerts] = await Promise.all([
      requestJson("/api/health"),
      requestJson("/api/telemetry?limit=50"),
      requestJson("/api/alerts?limit=50"),
    ]);
    const openCount = alerts.items.filter((item) => item.status === "open").length;
    const devices = new Set(telemetry.items.map((item) => item.device_id));

    elements.service.textContent = health.status === "ok" ? "Online" : "Unavailable";
    elements.devices.textContent = String(devices.size);
    elements.openAlerts.textContent = String(openCount);
    elements.events.textContent = String(telemetry.items.length);
    renderTelemetry(telemetry.items);
    renderAlerts(alerts.items);
    setStatus("Local demo service connected. All displayed records are synthetic.", "success");
  } catch (error) {
    elements.service.textContent = "Unavailable";
    setStatus(`Could not load the dashboard: ${error.message}`, "error");
  }
}

elements.simulateButton.addEventListener("click", async () => {
  elements.simulateButton.disabled = true;
  setStatus("Submitting one fixed synthetic anomaly to the local API…");
  try {
    await requestJson("/api/simulate/anomaly", { method: "POST" });
    setStatus("Synthetic anomaly recorded. Review the resulting advisory alerts.", "success");
    await refreshDashboard();
  } catch (error) {
    setStatus(`Anomaly simulation failed: ${error.message}`, "error");
  } finally {
    elements.simulateButton.disabled = false;
  }
});

elements.alertList.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-acknowledge]");
  if (!button) return;

  button.disabled = true;
  try {
    await requestJson(
      `/api/alerts/${encodeURIComponent(button.dataset.acknowledge)}/acknowledge`,
      { method: "POST" },
    );
    setStatus("Alert acknowledgement recorded.", "success");
    await refreshDashboard();
  } catch (error) {
    button.disabled = false;
    setStatus(`Could not acknowledge the alert: ${error.message}`, "error");
  }
});

refreshDashboard();
