import React from 'react';
import { ReportCategory, ReportPriority, ReportStatus } from '@/types/report';
import { Search, RotateCcw, LayoutGrid, List } from 'lucide-react';
import { Button } from '@/components/ui/button';

export interface ReportFiltersProps {
  search: string;
  onSearchChange: (search: string) => void;
  status: ReportStatus | 'all';
  onStatusChange: (status: ReportStatus | 'all') => void;
  category: ReportCategory | 'all';
  onCategoryChange: (category: ReportCategory | 'all') => void;
  priority: ReportPriority | 'all';
  onPriorityChange: (priority: ReportPriority | 'all') => void;
  viewMode?: 'grid' | 'table';
  onViewModeChange?: (mode: 'grid' | 'table') => void;
  onReset: () => void;
}

export const ReportFilters: React.FC<ReportFiltersProps> = ({
  search,
  onSearchChange,
  status,
  onStatusChange,
  category,
  onCategoryChange,
  priority,
  onPriorityChange,
  viewMode = 'grid',
  onViewModeChange,
  onReset,
}) => {
  const hasActiveFilters =
    Boolean(search) || status !== 'all' || category !== 'all' || priority !== 'all';

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 p-4 shadow-sm space-y-3">
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        {/* Search Input */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search by title, description, address, or ID..."
            className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border border-slate-300 bg-white placeholder-slate-400 focus:outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 transition-colors"
          />
        </div>

        {/* View mode toggle */}
        {onViewModeChange && (
          <div className="flex items-center gap-1 border border-slate-200 rounded-lg p-0.5 bg-slate-50 shrink-0 self-end md:self-auto">
            <button
              onClick={() => onViewModeChange('grid')}
              className={`p-1.5 rounded-md text-xs font-medium transition-colors ${
                viewMode === 'grid'
                  ? 'bg-white shadow-sm text-slate-900 font-semibold'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
              title="Grid View"
              aria-label="Grid View"
            >
              <LayoutGrid className="h-4 w-4" />
            </button>
            <button
              onClick={() => onViewModeChange('table')}
              className={`p-1.5 rounded-md text-xs font-medium transition-colors ${
                viewMode === 'table'
                  ? 'bg-white shadow-sm text-slate-900 font-semibold'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
              title="Table View"
              aria-label="Table View"
            >
              <List className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>

      {/* Select Filters Row */}
      <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-slate-100">
        <select
          value={status}
          onChange={(e) => onStatusChange(e.target.value as any)}
          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-teal-500 font-medium"
        >
          <option value="all">All Statuses</option>
          <option value="submitted">Submitted</option>
          <option value="under_review">Under Review</option>
          <option value="assigned">Assigned</option>
          <option value="in_progress">In Progress</option>
          <option value="resolved">Resolved</option>
          <option value="rejected">Rejected</option>
        </select>

        <select
          value={category}
          onChange={(e) => onCategoryChange(e.target.value as any)}
          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-teal-500 font-medium"
        >
          <option value="all">All Categories</option>
          <option value="road_damage">Road Damage</option>
          <option value="streetlight">Streetlight</option>
          <option value="garbage_waste">Garbage & Waste</option>
          <option value="water_leak">Water Leak</option>
          <option value="drainage">Drainage</option>
          <option value="public_property">Public Property</option>
          <option value="other">Other</option>
        </select>

        <select
          value={priority}
          onChange={(e) => onPriorityChange(e.target.value as any)}
          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-teal-500 font-medium"
        >
          <option value="all">All Priorities</option>
          <option value="urgent">Urgent</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>

        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onReset}
            className="text-xs text-slate-500 hover:text-slate-800 h-8"
            leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
          >
            Clear Filters
          </Button>
        )}
      </div>
    </div>
  );
};
