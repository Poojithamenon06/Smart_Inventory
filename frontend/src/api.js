const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
export const getToken = () => localStorage.getItem("token");
export const setToken = (t) => (t ? localStorage.setItem("token", t) : localStorage.removeItem("token"));

export async function api(path, { method = "GET", json, form } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let body;
  if (json) { headers["Content-Type"] = "application/json"; body = JSON.stringify(json); }
  if (form) body = new URLSearchParams(form);
  let res;
  try { res = await fetch(BASE + path, { method, headers, body }); }
  catch { throw new Error("Cannot reach the server. Is the backend running?"); }
  if (res.status === 401 && token) {
    setToken(null);
    window.dispatchEvent(new Event("logout"));
    throw new Error("Session expired, please log in again.");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Please check what you entered.");
  return data;
}
