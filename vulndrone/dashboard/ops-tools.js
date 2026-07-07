async function loadFlightLog() {
  const filename = document.getElementById("log-input").value || "flight_2026_06_01.log";
  const res = await fetch(`${API_URL}/logs/${filename}`, { headers: authHeaders() });
  const data = await res.json();
  document.getElementById("log-view").innerText = JSON.stringify(data, null, 2);
}

async function uploadFirmware() {
  const fileInput = document.getElementById("firmware-input");
  if (!fileInput.files.length) {
    document.getElementById("firmware-result").innerText = "choose a file first";
    return;
  }
  const form = new FormData();
  form.append("file", fileInput.files[0]);
  const res = await fetch(`${API_URL}/firmware/upload`, {
    method: "POST",
    headers: { ...authHeaders() },
    body: form,
  });
  const data = await res.json();
  document.getElementById("firmware-result").innerText = JSON.stringify(data, null, 2);
}

async function listFirmware() {
  const res = await fetch(`${API_URL}/firmware/list`, { headers: authHeaders() });
  const data = await res.json();
  document.getElementById("firmware-list").innerText = JSON.stringify(data, null, 2);
}

async function resetFleet() {
  const res = await fetch(`${API_URL}/admin/reset-fleet`, {
    method: "POST",
    headers: { ...authHeaders() },
  });
  const data = await res.json();
  document.getElementById("admin-result").innerText = JSON.stringify(data, null, 2);
}

document.getElementById("log-btn").addEventListener("click", loadFlightLog);
document.getElementById("firmware-upload-btn").addEventListener("click", uploadFirmware);
document.getElementById("firmware-list-btn").addEventListener("click", listFirmware);
document.getElementById("admin-reset-btn").addEventListener("click", resetFleet);

function loadModule(src) {
  if (document.getElementById(src)) return;
  const script = document.createElement("script");
  script.src = src;
  script.id = src;
  document.body.appendChild(script);
}

loadModule("diagnostics.js");
