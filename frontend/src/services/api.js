/**
 * Asphr API Service Layer
 * All backend requests are centralized here.
 * To switch environments, update VITE_API_URL in .env
 */

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

// ─── Hazards ────────────────────────────────────────────────────────────────

/**
 * Fetch hazard segments within a map viewport bounding box.
 * @param {object} bounds - { minLat, minLon, maxLat, maxLon }
 * @returns {Promise<{ hazards: Array }>}
 */
export async function fetchHazards({ minLat, minLon, maxLat, maxLon }) {
  const params = new URLSearchParams({
    min_lat: minLat,
    min_lon: minLon,
    max_lat: maxLat,
    max_lon: maxLon,
  });
  return request(`/api/v1/routes/hazards?${params}`);
}

// ─── Geocoding ───────────────────────────────────────────────────────────────

/**
 * Forward geocode a text query to coordinates.
 * @param {string} query
 * @returns {Promise<{ query: string, longitude: number, latitude: number }>}
 */
export async function forwardGeocode(query) {
  const params = new URLSearchParams({ query });
  return request(`/api/v1/geocode/forward?${params}`);
}

/**
 * Reverse geocode coordinates to an address.
 * @param {number} lat
 * @param {number} lon
 * @returns {Promise<object>}
 */
export async function reverseGeocode(lat, lon) {
  const params = new URLSearchParams({ lat, lon });
  return request(`/api/v1/geocode/reverse?${params}`);
}

// ─── Routes ──────────────────────────────────────────────────────────────────

/**
 * Compute a route between two coordinates.
 * @param {object} payload
 * @param {object} payload.origin       - { lat, lon }
 * @param {object} payload.destination  - { lat, lon }
 * @param {string} payload.route_type   - 'fastest'|'safest'|'straightest'|'popular'
 * @param {string} payload.vehicle_type - 'bike'|'car'|'truck'|'supercar'
 * @param {boolean} payload.avoid_tolls
 * @returns {Promise<{
 *   route_id: string,
 *   geometry: { type: string, coordinates: Array },
 *   distance_km: number,
 *   duration_min: number,
 *   hazard_score_avg: number,
 *   weather_alerts: Array<string>,
 *   instructions: Array<object>
 * }>}
 */
export async function computeRoute({
  origin,
  destination,
  route_type = 'fastest',
  vehicle_type = 'car',
  avoid_tolls = false,
}) {
  return request('/api/v1/routes/compute', {
    method: 'POST',
    body: JSON.stringify({ origin, destination, route_type, vehicle_type, avoid_tolls }),
  });
}

// ─── Health ──────────────────────────────────────────────────────────────────

export async function checkHealth() {
  return request('/health');
}
