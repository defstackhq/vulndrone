const API_URL = "http://localhost:8000";

let session = {
  token: localStorage.getItem("fleet_token") || null,
  role: localStorage.getItem("fleet_role") || null,
};

let pollHandles = [];

function authHeaders() {
  return session.token ? { Authorization: `Bearer ${session.token}` } : {};
}

function showDashboard() {
  document.getElementById("login-view").classList.add("hidden");
  document.getElementById("dashboard-view").classList.remove("hidden");
  updateRoleBadge();
  loadStatus();
  loadTelemetry();
  pollHandles.push(setInterval(loadStatus, 3000));
  pollHandles.push(setInterval(loadTelemetry, 2000));
  loadOpsTools();
}

function showLogin() {
  document.getElementById("dashboard-view").classList.add("hidden");
  document.getElementById("login-view").classList.remove("hidden");
  pollHandles.forEach(clearInterval);
  pollHandles = [];
}

function updateRoleBadge() {
  const badge = document.getElementById("role-badge");
  if (!badge) return;
  badge.innerText = session.role ? `role: ${session.role}` : "not signed in";
  badge.className = session.role === "superadmin" ? "pill pill-red" : "pill pill-teal";
}

function setSession(token, role) {
  session.token = token;
  session.role = role || null;
  if (token) {
    localStorage.setItem("fleet_token", token);
  } else {
    localStorage.removeItem("fleet_token");
  }
  if (role) {
    localStorage.setItem("fleet_role", role);
  } else {
    localStorage.removeItem("fleet_role");
  }
}

function loadOpsTools() {
  if (document.getElementById("ops-tools-script")) return;
  const script = document.createElement("script");
  script.src = "ops-tools.js";
  script.id = "ops-tools-script";
  document.body.appendChild(script);
}

async function doLogin() {
  const username = document.getElementById("login-user").value;
  const password = document.getElementById("login-pass").value;
  const errorBox = document.getElementById("login-error");
  errorBox.innerText = "";

  try {
    const res = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (!res.ok) {
      errorBox.innerText = data.detail || "sign in failed";
      return;
    }
    setSession(data.token, data.role);
    showDashboard();
  } catch (err) {
    errorBox.innerText = "companion api unreachable";
  }
}

function doLogout() {
  setSession(null, null);
  showLogin();
}

async function loadStatus() {
  try {
    const res = await fetch(`${API_URL}/status`, { headers: authHeaders() });
    const data = await res.json();
    document.getElementById("status").innerText = JSON.stringify(data, null, 2);

    const badge = document.getElementById("conn-badge");
    if (data.connected) {
      badge.innerText = "sitl connected";
      badge.className = "pill pill-teal";
    } else {
      badge.innerText = "sitl not connected";
      badge.className = "pill pill-muted";
    }
  } catch (err) {
    document.getElementById("status").innerText = "companion api unreachable";
  }
}

async function loadTelemetry() {
  try {
    const res = await fetch(`${API_URL}/telemetry`, { headers: authHeaders() });
    const data = await res.json();
    document.getElementById("telemetry").innerText = JSON.stringify(data, null, 2);
  } catch (err) {
    document.getElementById("telemetry").innerText = "companion api unreachable";
  }
}

async function sendArm(value) {
  const res = await fetch(`${API_URL}/command/arm`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ value }),
  });
  const data = await res.json();
  document.getElementById("command-result").innerText = JSON.stringify(data, null, 2);
}

async function sendTakeoff() {
  const altitude = parseFloat(document.getElementById("altitude-input").value || "10");
  const res = await fetch(`${API_URL}/command/takeoff`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ altitude }),
  });
  const data = await res.json();
  document.getElementById("command-result").innerText = JSON.stringify(data, null, 2);
}

async function loadMyMissions() {
  const res = await fetch(`${API_URL}/missions`, { headers: authHeaders() });
  const data = await res.json();
  document.getElementById("my-missions").innerText = JSON.stringify(data, null, 2);
}

async function loadMissionById() {
  const missionId = document.getElementById("mission-id-input").value || "1";
  const res = await fetch(`${API_URL}/missions/${missionId}`, { headers: authHeaders() });
  const data = await res.json();
  document.getElementById("mission-lookup").innerText = JSON.stringify(data, null, 2);
}

async function sendWebhookExport() {
  const webhookUrl = document.getElementById("webhook-input").value;
  const res = await fetch(`${API_URL}/integrations/export-telemetry`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ webhook_url: webhookUrl }),
  });
  const data = await res.json();
  document.getElementById("webhook-result").innerText = JSON.stringify(data, null, 2);
}

async function getStreamUrl() {
  const res = await fetch(`${API_URL}/video/stream-url`, { headers: authHeaders() });
  const data = await res.json();
  document.getElementById("stream-result").innerText = JSON.stringify(data, null, 2);
}

async function loadNotice() {
  try {
    const res = await fetch(`${API_URL}/public/notice`);
    const data = await res.json();
    document.getElementById("notice-text").innerText = data.message;
  } catch (err) {
    document.getElementById("notice-text").innerText = "notice unavailable";
  }
}

document.getElementById("login-btn").addEventListener("click", doLogin);
document.getElementById("logout-btn").addEventListener("click", doLogout);
document.getElementById("arm-btn").addEventListener("click", () => sendArm(true));
document.getElementById("disarm-btn").addEventListener("click", () => sendArm(false));
document.getElementById("takeoff-btn").addEventListener("click", sendTakeoff);
document.getElementById("my-missions-btn").addEventListener("click", loadMyMissions);
document.getElementById("mission-lookup-btn").addEventListener("click", loadMissionById);
document.getElementById("webhook-btn").addEventListener("click", sendWebhookExport);
document.getElementById("stream-btn").addEventListener("click", getStreamUrl);

loadNotice();

if (session.token) {
  showDashboard();
}
