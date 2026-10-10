import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, useMapEvents, useMap } from 'react-leaflet';
import L from 'leaflet';
import { DEFAULT_MAP_CONFIG } from '@/lib/constants';
import { Button } from '@/components/ui/button';
import { Navigation, MapPin, AlertCircle } from 'lucide-react';

export interface LocationPickerProps {
  latitude?: number;
  longitude?: number;
  onChange: (lat: number, lng: number) => void;
  error?: string;
}

// Custom Leaflet DivIcon for modern pin
const pinIcon = L.divIcon({
  className: 'custom-map-pin',
  html: `<div class="flex items-center justify-center -translate-x-1/2 -translate-y-full">
          <div class="h-9 w-9 rounded-full bg-teal-600 text-white shadow-lg flex items-center justify-center ring-4 ring-white border border-teal-700 animate-bounce">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
        </div>`,
  iconSize: [36, 36],
  iconAnchor: [18, 36],
});

// Map click handler sub-component
const MapEventsHandler: React.FC<{
  onSelect: (lat: number, lng: number) => void;
}> = ({ onSelect }) => {
  useMapEvents({
    click(e) {
      onSelect(Number(e.latlng.lat.toFixed(5)), Number(e.latlng.lng.toFixed(5)));
    },
  });
  return null;
};

// Map recentering controller
const ChangeView: React.FC<{ center: [number, number]; zoom?: number }> = ({ center, zoom }) => {
  const map = useMap();
  useEffect(() => {
    map.setView(center, zoom || map.getZoom());
  }, [center, zoom, map]);
  return null;
};

export const LocationPicker: React.FC<LocationPickerProps> = ({
  latitude,
  longitude,
  onChange,
  error,
}) => {
  const [isLocating, setIsLocating] = useState(false);
  const [geoError, setGeoError] = useState<string | null>(null);

  const currentLat = latitude ?? DEFAULT_MAP_CONFIG.lat;
  const currentLng = longitude ?? DEFAULT_MAP_CONFIG.lng;
  const hasSelectedPosition = latitude !== undefined && longitude !== undefined;

  const handleGetCurrentLocation = () => {
    if (!navigator.geolocation) {
      setGeoError('Geolocation is not supported by your browser.');
      return;
    }

    setIsLocating(true);
    setGeoError(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setIsLocating(false);
        const lat = Number(position.coords.latitude.toFixed(5));
        const lng = Number(position.coords.longitude.toFixed(5));
        onChange(lat, lng);
      },
      (err) => {
        setIsLocating(false);
        switch (err.code) {
          case err.PERMISSION_DENIED:
            setGeoError('Location permission denied. Please click on the map to set location manually.');
            break;
          case err.POSITION_UNAVAILABLE:
            setGeoError('GPS position unavailable. Please choose your location directly on the map.');
            break;
          case err.TIMEOUT:
            setGeoError('GPS location request timed out. Please click on the map.');
            break;
          default:
            setGeoError('Unable to detect location. Please click on the map.');
        }
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="block text-sm font-medium text-slate-700">
          Incident Location Coordinates <span className="text-rose-500">*</span>
        </label>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleGetCurrentLocation}
          isLoading={isLocating}
          leftIcon={<Navigation className="h-3.5 w-3.5 text-teal-600" />}
          className="text-xs h-8"
        >
          Use My GPS Location
        </Button>
      </div>

      <p className="text-xs text-slate-500">
        Click anywhere on the map or drag the pin to designate the exact problem spot.
      </p>

      {geoError && (
        <div className="flex items-center gap-2 p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-800">
          <AlertCircle className="h-4 w-4 shrink-0 text-amber-600" />
          <span>{geoError}</span>
        </div>
      )}

      {/* Map box */}
      <div className="relative h-64 sm:h-72 w-full rounded-xl border border-slate-300 overflow-hidden shadow-inner">
        <MapContainer
          center={[currentLat, currentLng]}
          zoom={DEFAULT_MAP_CONFIG.zoom}
          scrollWheelZoom={false}
          className="h-full w-full"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MapEventsHandler onSelect={onChange} />
          <ChangeView center={[currentLat, currentLng]} />

          {hasSelectedPosition && (
            <Marker
              position={[currentLat, currentLng]}
              icon={pinIcon}
              draggable={true}
              eventHandlers={{
                dragend: (e) => {
                  const marker = e.target;
                  const position = marker.getLatLng();
                  onChange(
                    Number(position.lat.toFixed(5)),
                    Number(position.lng.toFixed(5))
                  );
                },
              }}
            />
          )}
        </MapContainer>
      </div>

      {/* Coordinate Display */}
      <div className="flex items-center justify-between bg-slate-50 border border-slate-200 px-3 py-2 rounded-lg text-xs">
        <div className="flex items-center gap-1.5 text-slate-600">
          <MapPin className="h-3.5 w-3.5 text-teal-600" />
          <span>Selected Coordinates:</span>
          {hasSelectedPosition ? (
            <span className="font-semibold text-slate-800">
              {currentLat.toFixed(5)}, {currentLng.toFixed(5)}
            </span>
          ) : (
            <span className="italic text-slate-400">None selected (click map)</span>
          )}
        </div>
      </div>

      {error && <p className="text-xs text-rose-600 font-medium">{error}</p>}
    </div>
  );
};
