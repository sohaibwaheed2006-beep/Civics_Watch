/**
 * Bidirectional geocoding against OpenStreetMap's Nominatim service.
 *
 * - `reverseGeocode(lat, lng)` turns coordinates into a human-readable
 *   address so the map pin can auto-fill the "Street Address" field.
 * - `forwardGeocode(address)` turns a typed address into coordinates so
 *   the pin can jump to the matching spot.
 *
 * Nominatim is free, keyless and already consistent with the OSM tiles
 * used by the location picker. Its usage policy limits browser callers to
 * roughly one request per second per user, which the UI respects by
 * debouncing address input before calling.
 *
 * Every network, HTTP and JSON failure is swallowed and reported as
 * `null`, so a geocoding outage never breaks report submission.
 */

const NOMINATIM_BASE = 'https://nominatim.openstreetmap.org';

export interface GeocodedCoords {
  lat: number;
  lng: number;
}

async function fetchJson<T>(url: string, signal?: AbortSignal): Promise<T | null> {
  try {
    const res = await fetch(url, {
      headers: { Accept: 'application/json' },
      signal,
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

interface NominatimReverseResponse {
  display_name?: string;
}

interface NominatimSearchResult {
  lat: string;
  lon: string;
}

export const geocodingService = {
  async reverseGeocode(
    lat: number,
    lng: number,
    signal?: AbortSignal
  ): Promise<string | null> {
    const url = `${NOMINATIM_BASE}/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1`;
    const data = await fetchJson<NominatimReverseResponse>(url, signal);
    return data?.display_name ?? null;
  },

  async forwardGeocode(
    address: string,
    signal?: AbortSignal
  ): Promise<GeocodedCoords | null> {
    const query = address.trim();
    if (query.length < 3) return null;
    const url = `${NOMINATIM_BASE}/search?format=json&q=${encodeURIComponent(
      query
    )}&limit=1`;
    const data = await fetchJson<NominatimSearchResult[]>(url, signal);
    if (!Array.isArray(data) || data.length === 0) return null;
    const parsedLat = parseFloat(data[0].lat);
    const parsedLng = parseFloat(data[0].lon);
    if (Number.isNaN(parsedLat) || Number.isNaN(parsedLng)) return null;
    return {
      lat: Number(parsedLat.toFixed(5)),
      lng: Number(parsedLng.toFixed(5)),
    };
  },
};
