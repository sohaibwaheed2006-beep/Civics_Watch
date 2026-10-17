import React from 'react';
import { MapContainer, TileLayer, Marker } from 'react-leaflet';
import L from 'leaflet';
import { ReportPriority, ReportStatus } from '@/types/report';
import { DEFAULT_MAP_CONFIG } from '@/lib/constants';

export interface ReportLocationMapProps {
  latitude: number;
  longitude: number;
  status?: ReportStatus;
  priority?: ReportPriority;
  /** Tailwind height class for the map box. */
  heightClassName?: string;
}

// Single read-only pin, colour-matched to the report's status/priority so the
// admin sees the issue location at a glance (not just raw coordinates).
function createPinIcon(status?: ReportStatus, priority?: ReportPriority) {
  let bgColor = 'bg-teal-600';
  let ringColor = 'ring-teal-100';

  if (status === 'resolved') {
    bgColor = 'bg-emerald-600';
    ringColor = 'ring-emerald-100';
  } else if (status === 'in_progress') {
    bgColor = 'bg-blue-600';
    ringColor = 'ring-blue-100';
  } else if (status === 'rejected') {
    bgColor = 'bg-slate-500';
    ringColor = 'ring-slate-100';
  } else if (priority === 'urgent') {
    bgColor = 'bg-rose-600';
    ringColor = 'ring-rose-100';
  } else if (status === 'under_review') {
    bgColor = 'bg-amber-600';
    ringColor = 'ring-amber-100';
  }

  return L.divIcon({
    className: 'custom-report-pin',
    html: `<div class="flex items-center justify-center -translate-x-1/2 -translate-y-full">
            <div class="h-9 w-9 rounded-full ${bgColor} text-white shadow-lg flex items-center justify-center ring-4 ${ringColor} border border-white">
              <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
          </div>`,
    iconSize: [36, 36],
    iconAnchor: [18, 36],
  });
}

export const ReportLocationMap: React.FC<ReportLocationMapProps> = ({
  latitude,
  longitude,
  status,
  priority,
  heightClassName = 'h-48',
}) => {
  if (
    typeof latitude !== 'number' ||
    typeof longitude !== 'number' ||
    Number.isNaN(latitude) ||
    Number.isNaN(longitude)
  ) {
    return (
      <div
        className={`${heightClassName} w-full rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-center text-xs text-slate-400`}
      >
        No coordinates recorded for this report.
      </div>
    );
  }

  return (
    <div
      className={`relative ${heightClassName} w-full rounded-xl border border-slate-200 overflow-hidden shadow-inner`}
    >
      <MapContainer
        center={[latitude, longitude]}
        zoom={Math.max(DEFAULT_MAP_CONFIG.zoom, 15)}
        scrollWheelZoom={false}
        dragging={true}
        doubleClickZoom={false}
        attributionControl={false}
        className="h-full w-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Marker
          position={[latitude, longitude]}
          icon={createPinIcon(status, priority)}
        />
      </MapContainer>
    </div>
  );
};
