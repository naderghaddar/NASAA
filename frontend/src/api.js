// frontend/src/api.js
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function predict({ lat, lon, target_date, kc, soil_buffer }) {
  const res = await fetch(`${API_BASE}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lat, lon, target_date, kc, soil_buffer })
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(`API error: ${res.status} ${t}`);
  }
  return res.json();
}
