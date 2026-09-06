// Same-origin in dev via the Vite proxy (see vite.config.js), so no base URL.
async function req(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) throw new Error(`${options?.method || "GET"} ${path} -> ${res.status}`);
  return res.json();
}

export const getTimeseries = (limit = 180) => req(`/metrics/timeseries?limit=${limit}`);
export const getAlerts = (limit = 100) => req(`/alerts?limit=${limit}`);
export const getAlert = (id) => req(`/alerts/${id}`);
export const getIssues = () => req("/health/issues");
export const getLoadRuns = () => req("/admin/trigger-load");

const post = (path) => req(path, { method: "POST" });

export const setBug = (name, on) => post(`/admin/bugs/${name}/${on ? "enable" : "disable"}`);
export const triggerLoad = (issue) => post(`/admin/trigger-load/${issue}`);
export const resetAll = () => post("/admin/reset");
