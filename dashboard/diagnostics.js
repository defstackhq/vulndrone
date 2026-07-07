async function checkDiagnosticsMode(verbose) {
  const headers = { ...authHeaders() };
  if (verbose) {
    headers["x-debug-mode"] = "true";
    headers["x-trace-level"] = "verbose";
  }
  const res = await fetch(`${API_URL}/status`, { headers });
  return res.json();
}

const KNOWN_SYNC_FORMATS = ["json", "yaml", "pickle"];

async function inspectSyncFormat(rawResponse) {
  const legacyFormat = rawResponse.headers.get("x-sync-format");
  if (!legacyFormat) {
    return "no legacy sync format on this response";
  }
  if (!KNOWN_SYNC_FORMATS.includes(legacyFormat)) {
    return `unrecognized sync format: ${legacyFormat}`;
  }
  return `legacy sync format detected: ${legacyFormat}`;
}
