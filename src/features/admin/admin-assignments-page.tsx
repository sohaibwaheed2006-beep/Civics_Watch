import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { reportService } from '@/services/report-service';
import { userService } from '@/services/user-service';
import { StatusBadge } from '@/components/data-display/status-badge';
import { PriorityBadge } from '@/components/data-display/priority-badge';
import { TableSkeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { ErrorPanel } from '@/components/ui/error-panel';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { formatDateTime } from '@/lib/formatters';
import { ArrowRight } from 'lucide-react';
import { Avatar } from '@/components/ui/avatar';
import { getCategoryCoverImage, handleImageFallback } from '@/lib/category-images';

export const AdminAssignmentsPage: React.FC = () => {
  const [statusFilter, setStatusFilter] = useState<'all' | 'assigned' | 'in_progress' | 'resolved'>('all');

  // Load all assigned reports
  const { data: reportsData, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin-assignments', statusFilter],
    queryFn: () =>
      reportService.getReports({
        status: statusFilter === 'all' ? undefined : (statusFilter as any),
        limit: 50,
      }),
  });

  // Load workers
  const { data: workersData } = useQuery({
    queryKey: ['workers-count'],
    queryFn: () => userService.getUsers({ role: 'worker', limit: 50 }),
  });

  const reports = (reportsData?.data || []).filter((r) => Boolean(r.assignedWorkerId));
  const workers = workersData?.data || [];

  return (
    <div className="space-y-6">
      <Breadcrumbs
        items={[
          { label: 'Admin Portal', href: '/admin/dashboard' },
          { label: 'Crew Dispatch & Assignments' },
        ]}
      />

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Field Technician Work Orders
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Monitor active work orders, worker assignments, SLA deadlines, and resolution progress.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as any)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-700 font-medium focus:ring-1 focus:ring-teal-500"
          >
            <option value="all">All Assignment States</option>
            <option value="assigned">Dispatched (Assigned)</option>
            <option value="in_progress">Active Work (In Progress)</option>
            <option value="resolved">Completed (Resolved)</option>
          </select>
        </div>
      </div>

      {/* Technicians Workload Summary Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        {workers.slice(0, 4).map((worker) => {
          const workerAssigned = reports.filter((r) => r.assignedWorkerId === worker.id);
          const activeCount = workerAssigned.filter((r) => r.status !== 'resolved').length;

          return (
            <div
              key={worker.id}
              className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs space-y-2"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Avatar
                    alt={worker.fullName}
                    fallback={worker.fullName}
                    role="worker"
                    size="sm"
                  />
                  <div>
                    <p className="text-xs font-semibold text-slate-900">{worker.fullName}</p>
                    <p className="text-[10px] text-slate-500">{worker.departmentName}</p>
                  </div>
                </div>
              </div>
              <div className="pt-1 flex items-center justify-between text-xs border-t border-slate-100">
                <span className="text-slate-500">Active Tasks:</span>
                <span className="font-bold text-teal-700">{activeCount} orders</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Assignments Table */}
      {isLoading ? (
        <TableSkeleton rows={6} />
      ) : isError ? (
        <ErrorPanel onRetry={refetch} message="Failed to load assignment orders." />
      ) : reports.length === 0 ? (
        <EmptyState
          title="No assignments found"
          description="There are currently no assigned reports matching your filter criteria."
        />
      ) : (
        <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Assigned Worker</th>
                  <th className="py-3 px-4">Issue Details</th>
                  <th className="py-3 px-4">Department</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Priority</th>
                  <th className="py-3 px-4">SLA Deadline</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {reports.map((report) => {
                  const thumbUrl =
                    report.photos && report.photos.length > 0
                      ? report.photos[0].url
                      : getCategoryCoverImage(report.category);

                  return (
                    <tr key={report.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <div className="flex items-center gap-2.5">
                          <Avatar
                            alt={report.assignedWorkerName || 'Technician'}
                            fallback={report.assignedWorkerName || 'T'}
                            role="worker"
                            size="sm"
                          />
                          <div>
                            <p className="font-semibold text-slate-900">{report.assignedWorkerName || 'Unassigned'}</p>
                          </div>
                        </div>
                      </td>

                      <td className="py-3.5 px-4 max-w-xs">
                        <div className="flex items-center gap-2.5">
                          <img
                            src={thumbUrl}
                            alt=""
                            onError={(e) => {
                              const target = e.currentTarget as HTMLImageElement;
                              const fallback = getCategoryCoverImage(report.category);
                              if (target.src !== fallback) {
                                target.src = fallback;
                              } else {
                                handleImageFallback(e, report.category);
                              }
                            }}
                            className="h-8 w-10 rounded-md object-cover shrink-0 border border-slate-200"
                          />
                          <div className="min-w-0">
                            <p className="font-semibold text-slate-900 truncate">{report.title}</p>
                            <p className="text-[11px] text-slate-500 truncate">{report.address}</p>
                          </div>
                        </div>
                      </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span className="font-medium text-slate-800">
                        {report.departmentName || '—'}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <StatusBadge status={report.status} size="sm" />
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <PriorityBadge priority={report.priority} size="sm" />
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      {report.deadline ? (
                        <span className="font-medium text-amber-700">
                          {formatDateTime(report.deadline)}
                        </span>
                      ) : (
                        <span className="text-slate-400">Standard 48h</span>
                      )}
                    </td>

                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <Link
                        to={`/admin/reports/${report.id}`}
                        className="inline-flex items-center gap-1 font-semibold text-teal-600 hover:text-teal-800"
                      >
                        <span>Manage</span>
                        <ArrowRight className="h-3 w-3" />
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
