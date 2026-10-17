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
import { getCategoryCoverImage, handleImageFallback } from '@/lib/category-images';

export interface IssueMapProps {
  reports: Report[];
  baseDetailRoute: string; // e.g. '/citizen/reports' or '/admin/reports'
  isLoading?: boolean;
  // When set (the field-worker map), markers assigned to this worker are shown
  // larger, ringed and badged so the worker can pick their jobs out of the
  // whole community at a glance.
  highlightWorkerId?: string;
}

// Marker icon generator according to status. `assigned` draws the
// "this one is yours" treatment on the worker map.
function createStatusIcon(status: ReportStatus, priority: ReportPriority, assigned = false) {
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

  const size = assigned ? 'h-10 w-10' : 'h-8 w-8';
  const ring = assigned ? 'ring-4 ring-indigo-300' : `ring-4 ${ringColor}`;
  const assignedBadge = assigned
    ? `<span class="absolute -top-1.5 -right-1.5 h-4 w-4 rounded-full bg-indigo-600 text-white border-2 border-white flex items-center justify-center">
         <svg class="h-2.5 w-2.5" fill="currentColor" viewBox="0 0 20 20">
           <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.286 3.957a1 1 0 00.95.69h4.162c.969 0 1.371 1.24.588 1.81l-3.367 2.446a1 1 0 00-.364 1.118l1.286 3.957c.3.921-.755 1.688-1.54 1.118l-3.366-2.446a1 1 0 00-1.176 0l-3.366 2.446c-.784.57-1.838-.197-1.539-1.118l1.286-3.957a1 1 0 00-.364-1.118L2.98 9.384c-.783-.57-.38-1.81.588-1.81h4.162a1 1 0 00.95-.69l1.286-3.957z"/>
         </svg>
       </span>`
    : '';

  return L.divIcon({
    className: 'custom-issue-marker',
    html: `<div class="flex items-center justify-center -translate-x-1/2 -translate-y-full">
            <div class="relative ${size} rounded-full ${bgColor} text-white shadow-md flex items-center justify-center ${ring} border border-white">
              <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              ${assignedBadge}
            </div>
          </div>`,
    iconSize: assigned ? [40, 40] : [32, 32],
    iconAnchor: assigned ? [20, 40] : [16, 32],
    popupAnchor: [0, assigned ? -40 : -32],
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

export const IssueMap: React.FC<IssueMapProps> = ({ reports, baseDetailRoute, highlightWorkerId }) => {
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [statusFilter, setStatusFilter] = useState<ReportStatus | 'all'>('all');
  const [categoryFilter, setCategoryFilter] = useState<ReportCategory | 'all'>('all');
  const [priorityFilter, setPriorityFilter] = useState<ReportPriority | 'all'>('all');
  const [onlyMine, setOnlyMine] = useState(false);

  const isAssignedToMe = (r: Report) =>
    Boolean(highlightWorkerId) && r.assignedWorkerId === highlightWorkerId;

  const assignedCount = highlightWorkerId ? reports.filter(isAssignedToMe).length : 0;

  const filteredReports = reports.filter((r) => {
    if (onlyMine && !isAssignedToMe(r)) return false;
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
          {highlightWorkerId && (
            <button
              type="button"
              onClick={() => setOnlyMine((v) => !v)}
              className={`ml-1 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold border transition-colors ${
                onlyMine
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-indigo-50 text-indigo-700 border-indigo-200 hover:bg-indigo-100'
              }`}
              title="Show only the reports assigned to you"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-current" />
              {onlyMine ? 'Showing my jobs' : `My assignments (${assignedCount})`}
            </button>
          )}
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
              icon={createStatusIcon(report.status, report.priority, isAssignedToMe(report))}
              eventHandlers={{
                click: () => setSelectedReport(report),
              }}
            >
              <Popup>
                <div className="p-1 max-w-[240px] space-y-2">
                  <div className="relative h-28 w-full rounded-lg overflow-hidden bg-slate-100">
                    <img
                      src={report.photos?.[0]?.url || getCategoryCoverImage(report.category)}
                      alt={report.title}
                      onError={(e) => {
                        (e.currentTarget as HTMLImageElement).src = getCategoryCoverImage(report.category);
                      }}
                      className="h-full w-full object-cover"
                    />
                    <div className="absolute top-2 left-2 flex gap-1">
                      <StatusBadge status={report.status} size="sm" />
                    </div>
                  </div>
                  <div className="px-1 space-y-1">
                    {isAssignedToMe(report) && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2 py-0.5 text-[10px] font-semibold text-indigo-700 border border-indigo-200">
                        <span className="h-1.5 w-1.5 rounded-full bg-indigo-600" />
                        Assigned to you
                      </span>
                    )}
                    <h4 className="text-xs font-bold text-slate-900 leading-snug">
                      {report.title}
                    </h4>
                    <p className="text-[11px] text-slate-500 truncate">{report.address}</p>
                    <Link
                      to={`${baseDetailRoute}/${report.id}`}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-teal-600 hover:text-teal-700 pt-1"
                    >
                      <span>View full report</span>
                      <ArrowRight className="h-3 w-3" />
                    </Link>
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>

        {/* Selected Report Floating Card / Side Drawer */}
        {selectedReport && (
          <div className="absolute top-4 left-4 z-20 max-w-sm w-full animate-in fade-in slide-in-from-left-4">
            <Card className="shadow-2xl border-slate-200/90 bg-white/95 backdrop-blur p-4 relative overflow-hidden">
              <button
                onClick={() => setSelectedReport(null)}
                className="absolute top-3 right-3 z-10 text-slate-400 hover:text-slate-600 bg-white/80 backdrop-blur p-1 rounded-full shadow-sm"
                aria-label="Close details"
              >
                <X className="h-4 w-4" />
              </button>

              <div className="relative aspect-video rounded-xl overflow-hidden border border-slate-200 bg-slate-100 mb-3 shadow-inner">
                <img
                  src={selectedReport.photos?.[0]?.url || getCategoryCoverImage(selectedReport.category)}
                  alt={selectedReport.title}
                  onError={(e) => {
                    const target = e.currentTarget as HTMLImageElement;
                    const catCover = getCategoryCoverImage(selectedReport.category);
                    if (target.src !== catCover) {
                      target.src = catCover;
                    } else {
                      handleImageFallback(e, selectedReport.category);
                    }
                  }}
                  className="h-full w-full object-cover"
                />
                <div className="absolute top-2.5 left-2.5 flex items-center gap-1.5">
                  <StatusBadge status={selectedReport.status} size="sm" />
                  <PriorityBadge priority={selectedReport.priority} size="sm" />
                </div>
                {selectedReport.photos && selectedReport.photos.length > 1 && (
                  <span className="absolute bottom-2 right-2 bg-slate-900/80 backdrop-blur text-white text-[10px] font-medium px-2 py-0.5 rounded-full">
                    +{selectedReport.photos.length} photos
                  </span>
                )}
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
