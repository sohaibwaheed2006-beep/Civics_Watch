import React, { useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { Report, ReportCategory, ReportPriority, ReportStatus } from '@/types/report';
import { DEFAULT_MAP_CONFIG } from '@/lib/constants';
import { StatusBadge } from '@/components/data-display/status-badge';
import { PriorityBadge } from '@/components/data-display/priority-badge';
import { formatCategory, formatDate } from '@/lib/formatters';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';
import { Navigation, Filter, MapPin, X, ArrowRight } from 'lucide-react';
import { Card } from '@/components/ui/card';

export interface IssueMapProps {
  reports: Report[];
  baseDetailRoute: string; // e.g. '/citizen/reports' or '/admin/reports'
  isLoading?: boolean;
}

// Marker icon generator according to status
function createStatusIcon(status: ReportStatus, priority: ReportPriority) {
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
    className: 'custom-issue-marker',
    html: `<div class="flex items-center justify-center -translate-x-1/2 -translate-y-full">
            <div class="h-8 w-8 rounded-full ${bgColor} text-white shadow-md flex items-center justify-center ring-4 ${ringColor} border border-white">
              <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
          </div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32],
  });
}

const LocateUserControl: React.FC = () => {
  const map = useMap();
  const [locating, setLocating] = useState(false);

  const locate = () => {
    if (!navigator.geolocation) return;
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false);
        map.flyTo([pos.coords.latitude, pos.coords.longitude], 15);
      },
      () => setLocating(false)
    );
  };

  return (
    <div className="leaflet-top leaflet-right" style={{ marginTop: '12px', marginRight: '12px' }}>
      <div className="leaflet-control">
        <Button
          variant="outline"
          size="sm"
          onClick={locate}
          isLoading={locating}
          className="bg-white/95 backdrop-blur shadow-md border-slate-200 text-xs text-slate-700"
          leftIcon={<Navigation className="h-3.5 w-3.5 text-teal-600" />}
        >
          My Location
        </Button>
      </div>
    </div>
  );
};

export const IssueMap: React.FC<IssueMapProps> = ({ reports, baseDetailRoute }) => {
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [statusFilter, setStatusFilter] = useState<ReportStatus | 'all'>('all');
  const [categoryFilter, setCategoryFilter] = useState<ReportCategory | 'all'>('all');
  const [priorityFilter, setPriorityFilter] = useState<ReportPriority | 'all'>('all');

  const filteredReports = reports.filter((r) => {
    if (statusFilter !== 'all' && r.status !== statusFilter) return false;
    if (categoryFilter !== 'all' && r.category !== categoryFilter) return false;
    if (priorityFilter !== 'all' && r.priority !== priorityFilter) return false;
    return true;
  });

  return (
    <div className="relative h-[calc(100vh-12rem)] min-h-[500px] w-full rounded-2xl border border-slate-200 overflow-hidden shadow-sm flex flex-col">
      {/* Top filter toolbar */}
      <div className="bg-white/95 backdrop-blur-md border-b border-slate-200 px-4 py-3 z-20 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-700">
          <Filter className="h-4 w-4 text-teal-600" />
          <span>Map Filters</span>
          <span className="ml-1 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
            {filteredReports.length} issues visible
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as any)}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-teal-500"
          >
            <option value="all">All Statuses</option>
            <option value="submitted">Submitted</option>
            <option value="under_review">Under Review</option>
            <option value="assigned">Assigned</option>
            <option value="in_progress">In Progress</option>
            <option value="resolved">Resolved</option>
          </select>

          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value as any)}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-teal-500"
          >
            <option value="all">All Categories</option>
            <option value="road_damage">Road Damage</option>
            <option value="streetlight">Streetlight</option>
            <option value="garbage_waste">Garbage & Waste</option>
            <option value="water_leak">Water Leak</option>
            <option value="drainage">Drainage</option>
            <option value="public_property">Public Property</option>
          </select>

          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value as any)}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-teal-500"
          >
            <option value="all">All Priorities</option>
            <option value="urgent">Urgent</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          {(statusFilter !== 'all' || categoryFilter !== 'all' || priorityFilter !== 'all') && (
            <button
              onClick={() => {
                setStatusFilter('all');
                setCategoryFilter('all');
                setPriorityFilter('all');
              }}
              className="text-xs text-slate-500 hover:text-slate-800 underline ml-1"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Main Map */}
      <div className="relative flex-1 w-full">
        <MapContainer
          center={[DEFAULT_MAP_CONFIG.lat, DEFAULT_MAP_CONFIG.lng]}
          zoom={DEFAULT_MAP_CONFIG.zoom}
          className="h-full w-full"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <LocateUserControl />

          {filteredReports.map((report) => (
            <Marker
              key={report.id}
              position={[report.latitude, report.longitude]}
              icon={createStatusIcon(report.status, report.priority)}
              eventHandlers={{
                click: () => setSelectedReport(report),
              }}
            >
              <Popup>
                <div className="p-3 max-w-[260px] space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <StatusBadge status={report.status} size="sm" />
                    <PriorityBadge priority={report.priority} size="sm" />
                  </div>
                  <h4 className="text-xs font-semibold text-slate-900 leading-snug">
                    {report.title}
                  </h4>
                  <p className="text-[11px] text-slate-500 truncate">{report.address}</p>
                  <Link
                    to={`${baseDetailRoute}/${report.id}`}
                    className="inline-flex items-center gap-1 text-xs font-medium text-teal-600 hover:text-teal-700 pt-1"
                  >
                    <span>View full report</span>
                    <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>

        {/* Selected Report Floating Card / Side Drawer */}
        {selectedReport && (
          <div className="absolute top-4 left-4 z-20 max-w-sm w-full animate-in fade-in slide-in-from-left-4">
            <Card className="shadow-xl border-slate-200/90 bg-white/95 backdrop-blur p-4 relative">
              <button
                onClick={() => setSelectedReport(null)}
                className="absolute top-3 right-3 text-slate-400 hover:text-slate-600 p-1 rounded-lg"
                aria-label="Close details"
              >
                <X className="h-4 w-4" />
              </button>

              <div className="flex items-center gap-2 mb-2 pr-6">
                <StatusBadge status={selectedReport.status} size="sm" />
                <PriorityBadge priority={selectedReport.priority} size="sm" />
              </div>

              <h4 className="text-sm font-semibold text-slate-900 line-clamp-2">
                {selectedReport.title}
              </h4>

              <p className="text-xs text-slate-600 mt-1 line-clamp-2">
                {selectedReport.description}
              </p>

              <div className="mt-3 space-y-1.5 text-xs text-slate-500 border-t border-slate-100 pt-2.5">
                <div className="flex items-center gap-1.5">
                  <MapPin className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                  <span className="truncate">{selectedReport.address || 'GPS Coordinate Pin'}</span>
                </div>
                <div className="flex items-center justify-between text-[11px]">
                  <span>Category: {formatCategory(selectedReport.category)}</span>
                  <span>{formatDate(selectedReport.createdAt)}</span>
                </div>
              </div>

              {selectedReport.photos && selectedReport.photos.length > 0 && (
                <div className="mt-3 aspect-video rounded-lg overflow-hidden border border-slate-100">
                  <img
                    src={selectedReport.photos[0].url}
                    alt={selectedReport.title}
                    className="h-full w-full object-cover"
                  />
                </div>
              )}

              <div className="mt-3 pt-2 flex items-center justify-end">
                <Link to={`${baseDetailRoute}/${selectedReport.id}`}>
                  <Button size="sm" rightIcon={<ArrowRight className="h-3.5 w-3.5" />}>
                    Open Details
                  </Button>
                </Link>
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
};
