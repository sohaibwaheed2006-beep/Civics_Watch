import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/hooks/use-auth';
import { useQuery } from '@tanstack/react-query';
import { assignmentService } from '@/services/assignment-service';
import { StatusBadge } from '@/components/data-display/status-badge';
import { PriorityBadge } from '@/components/data-display/priority-badge';
import { Pagination } from '@/components/data-display/pagination';
import { CardSkeleton, TableSkeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { ErrorPanel } from '@/components/ui/error-panel';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { formatCategory, formatDate } from '@/lib/formatters';
import { MapPin, Navigation, ArrowRight, LayoutGrid, List } from 'lucide-react';
import { ReportPriority, ReportStatus } from '@/types/report';

export const WorkerAssignmentsPage: React.FC = () => {
  const { user } = useAuth();

  const [status, setStatus] = useState<ReportStatus | 'all'>('all');
  const [priority, setPriority] = useState<ReportPriority | 'all'>('all');
  const [page, setPage] = useState(1);
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['worker-assignments-list', user?.id, status, priority, page],
    queryFn: () =>
      user
        ? assignmentService.getWorkerAssignments(user.id, {
            status,
            priority,
            page,
            limit: 9,
          })
        : Promise.reject(),
    enabled: Boolean(user?.id),
  });

  const assignments = data?.data || [];
  const totalPages = data?.totalPages || 1;
  const totalItems = data?.total || 0;

  return (
    <div className="space-y-6">
      <Breadcrumbs
        items={[
          { label: 'Worker Portal', href: '/worker/dashboard' },
          { label: 'Assigned Work Orders' },
        ]}
      />

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Assigned Work Orders
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Review your dispatch assignments, execute on-site work, and submit resolution reports.
          </p>
        </div>

        {/* View toggle */}
        <div className="flex items-center gap-1 border border-slate-200 rounded-lg p-0.5 bg-slate-50">
          <button
            onClick={() => setViewMode('grid')}
            className={`p-1.5 rounded-md text-xs font-medium transition-colors ${
              viewMode === 'grid'
                ? 'bg-white shadow-sm text-slate-900 font-semibold'
                : 'text-slate-500 hover:text-slate-800'
            }`}
            title="Grid View"
          >
            <LayoutGrid className="h-4 w-4" />
          </button>
          <button
            onClick={() => setViewMode('table')}
            className={`p-1.5 rounded-md text-xs font-medium transition-colors ${
              viewMode === 'table'
                ? 'bg-white shadow-sm text-slate-900 font-semibold'
                : 'text-slate-500 hover:text-slate-800'
            }`}
            title="Table View"
          >
            <List className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Filter toolbar */}
      <div className="bg-white rounded-xl border border-slate-200 p-3 shadow-sm flex flex-wrap items-center gap-2">
        <select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value as any);
            setPage(1);
          }}
          className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-700 font-medium focus:ring-1 focus:ring-teal-500"
        >
          <option value="all">All Statuses</option>
          <option value="assigned">Dispatched (Assigned)</option>
          <option value="in_progress">In Progress</option>
          <option value="resolved">Resolved</option>
        </select>

        <select
          value={priority}
          onChange={(e) => {
            setPriority(e.target.value as any);
            setPage(1);
          }}
          className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-700 font-medium focus:ring-1 focus:ring-teal-500"
        >
          <option value="all">All Priorities</option>
          <option value="urgent">Urgent</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      {/* Content Rendering */}
      {isLoading ? (
        viewMode === 'grid' ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>
        ) : (
          <TableSkeleton rows={6} />
        )
      ) : isError ? (
        <ErrorPanel onRetry={refetch} message="Unable to load work orders." />
      ) : assignments.length === 0 ? (
        <EmptyState
          title="No work orders found"
          description="You do not have any tasks matching the selected filters."
        />
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {assignments.map((assignment) => (
            <Card
              key={assignment.id}
              hoverEffect
              className="flex flex-col justify-between border-slate-200/90 hover:border-amber-400"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <StatusBadge status={assignment.report.status} size="sm" />
                  <PriorityBadge priority={assignment.report.priority} size="sm" />
                </div>

                <h3 className="text-sm font-semibold text-slate-900 line-clamp-1">
                  {assignment.report.title}
                </h3>

                <p className="text-xs text-slate-600 mt-1 line-clamp-2">
                  {assignment.report.description}
                </p>

                <div className="mt-3 space-y-1.5 text-xs text-slate-500 border-t border-slate-100 pt-2.5">
                  <div className="flex items-center gap-1.5">
                    <MapPin className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                    <span className="truncate">{assignment.report.address}</span>
                  </div>
                  <div className="flex items-center justify-between text-[11px]">
                    <span>{formatCategory(assignment.report.category)}</span>
                    <span>Assigned {formatDate(assignment.assignedAt)}</span>
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                <a
                  href={`https://www.google.com/maps/dir/?api=1&destination=${assignment.report.latitude},${assignment.report.longitude}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-slate-900"
                >
                  <Navigation className="h-3.5 w-3.5 text-teal-600" />
                  <span>Navigate</span>
                </a>

                <Link to={`/worker/assignments/${assignment.report.id}`}>
                  <Button size="sm" rightIcon={<ArrowRight className="h-3.5 w-3.5" />}>
                    Open Order
                  </Button>
                </Link>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Task Details</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Priority</th>
                  <th className="py-3 px-4">Assigned On</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {assignments.map((assignment) => (
                  <tr key={assignment.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4 max-w-sm">
                      <p className="font-semibold text-slate-900 truncate">
                        {assignment.report.title}
                      </p>
                      <p className="text-[11px] text-slate-500 truncate">
                        {assignment.report.address}
                      </p>
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span className="font-medium text-slate-800">
                        {formatCategory(assignment.report.category)}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <StatusBadge status={assignment.report.status} size="sm" />
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <PriorityBadge priority={assignment.report.priority} size="sm" />
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap text-slate-500">
                      {formatDate(assignment.assignedAt)}
                    </td>

                    <td className="py-3.5 px-4 text-right whitespace-nowrap space-x-2">
                      <a
                        href={`https://www.google.com/maps/dir/?api=1&destination=${assignment.report.latitude},${assignment.report.longitude}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 font-medium text-slate-600 hover:text-slate-900"
                      >
                        <Navigation className="h-3.5 w-3.5 text-teal-600" />
                        <span>Map</span>
                      </a>

                      <Link
                        to={`/worker/assignments/${assignment.report.id}`}
                        className="inline-flex items-center gap-1 font-semibold text-teal-600 hover:text-teal-800"
                      >
                        <span>Open</span>
                        <ArrowRight className="h-3 w-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pagination */}
      <Pagination
        currentPage={page}
        totalPages={totalPages}
        totalItems={totalItems}
        pageSize={9}
        onPageChange={setPage}
      />
    </div>
  );
};
