export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
const WS_BASE = API_BASE.replace("http://", "ws://").replace("https://", "wss://");

export async function getJson(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

export async function postJson(path, data = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

export async function deleteJson(path) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "DELETE"
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

export function statusSocket() {
  return new WebSocket(`${WS_BASE}/ws/status`);
}

export function cameraStreamUrl() {
  return `${API_BASE}/api/vision/camera/stream`;
}
