export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
const WS_BASE = API_BASE.replace("http://", "ws://").replace("https://", "wss://");
const TOKEN_KEY = "juno_auth_token";

export function getAuthToken() {
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setAuthToken(token) {
  if (token) {
    window.localStorage.setItem(TOKEN_KEY, token);
  } else {
    window.localStorage.removeItem(TOKEN_KEY);
  }
}

function authHeaders(extra = {}) {
  const token = getAuthToken();
  return {
    ...extra,
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  };
}

async function parseJsonResponse(response) {
  if (!response.ok) {
    let detail = `API error: ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      // Keep default message.
    }
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

export async function getJson(path) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: authHeaders()
  });
  return parseJsonResponse(response);
}

export async function postJson(path, data = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: authHeaders({
      "Content-Type": "application/json"
    }),
    body: JSON.stringify(data)
  });

  return parseJsonResponse(response);
}

export async function deleteJson(path) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "DELETE",
    headers: authHeaders()
  });

  return parseJsonResponse(response);
}

export async function putJson(path, data = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: authHeaders({
      "Content-Type": "application/json"
    }),
    body: JSON.stringify(data)
  });

  return parseJsonResponse(response);
}

export function statusSocket() {
  return new WebSocket(`${WS_BASE}/ws/status`);
}

export function cameraStreamUrl() {
  return `${API_BASE}/api/vision/camera/stream`;
}
