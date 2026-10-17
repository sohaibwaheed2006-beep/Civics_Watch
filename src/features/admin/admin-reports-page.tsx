import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { reportService } from '@/services/report-service';
import { departmentService } from '@/services/department-service';
import { ReportFilters } from '@/components/reports/report-filters';
import { StatusBadge } from '@/components/data-display/status-badge';
import { PriorityBadge } from '@/components/data-display/priority-badge';
import { Pagination } from '@/components/data-display/pagination';
import { TableSkeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { ErrorPanel } from '@/components/ui/error-panel';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { formatCategory, formatDate } from '@/lib/formatters';
import { useDebounce } from '@/hooks/use-debounce';
import { ArrowRight, ArrowUpDown } from 'lucide-react';
import { ReportCategory, ReportPriority, ReportStatus } from '@/types/report';

export const AdminReportsPage: React.FC = () => {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<ReportStatus | 'all'>('all');
  const [category, setCategory] = useState<ReportCategory | 'all'>('all');
  const [priority, setPriority] = useState<ReportPriority | 'all'>('all');
  const [departmentId, setDepartmentId] = useState<string | 'all'>('all');
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState<'priority' | 'createdAt'>('priority');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const debouncedSearch = useDebounce(search, 300);

  // Load departments for filter
  const { data: departments = [] } = useQuery({
    queryKey: ['departments-list'],
    queryFn: () => departmentService.getDepartments(),
  });

  // Load reports
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: [
      'admin-reports-list',
      debouncedSearch,
      status,
      category,
      priority,
      departmentId,
      page,
      sortBy,
      sortOrder,
    ],
    queryFn: () =>
      reportService.getReports({
        search: debouncedSearch,
        status,
        category,
        priority,
        departmentId,
        page,
        limit: 10,
        sortBy,
        sortOrder,
      }),
  });

  const reports = data?.data || [];
  const totalPages = data?.totalPages || 1;
  const totalItems = data?.total || 0;

  const handleResetFilters = () => {
    setSearch('');
    setStatus('all');
    setCategory('all');
    setPriority('all');
    setDepartmentId('all');
    setPage(1);
  };

  return (
    <div className="space-y-6">
      <Breadcrumbs
        items={[
          { label: 'Admin Portal', href: '/admin/dashboard' },
          { label: 'Report Management' },
        ]}
      />

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Municipal Report Management
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Triage, assign, update, and audit all neighborhood issues. Sorted by AI-ranked priority
            (urgent → low) with submission dates for context.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={departmentId}
            onChange={(e) => {
              setDepartmentId(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-700 font-medium focus:ring-1 focus:ring-teal-500"
          >
            <option value="all">All Departments</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <ReportFilters
        search={search}
        onSearchChange={(val) => {
          setSearch(val);
          setPage(1);
        }}
        status={status}
        onStatusChange={(val) => {
          setStatus(val);
          setPage(1);
        }}
        category={category}
        onCategoryChange={(val) => {
          setCategory(val);
          setPage(1);
        }}
        priority={priority}
        onPriorityChange={(val) => {
          setPriority(val);
          setPage(1);
        }}
        onReset={handleResetFilters}
      />

      {/* Table view */}
      {isLoading ? (
        <TableSkeleton rows={8} />
      ) : isError ? (
        <ErrorPanel onRetry={refetch} message="Failed to load incident reports." />
      ) : reports.length === 0 ? (
        <EmptyState
          title="No reports match current filters"
          description="Adjust your search query or clear the filter parameters to view more records."
          actionText="Reset Filters"
          onAction={handleResetFilters}
        />
      ) : (
        <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">ID & Title</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Status</th>
                  <th
                    className="py-3 px-4 cursor-pointer hover:text-slate-700"
                    onClick={() => {
                      if (sortBy === 'priority') {
                        setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'));
                      } else {
                        setSortBy('priority');
                        setSortOrder('desc');
                      }
                    }}
                    title="AI-ranked priority. Click to toggle order."
                  >
                    <div className="flex items-center gap-1">
                      <span>AI Priority</span>
                      <ArrowUpDown className="h-3 w-3" />
                      {sortBy === 'priority' && (
                        <span className="text-[9px] font-bold text-teal-600">
                          {sortOrder === 'desc' ? 'HIGH→LOW' : 'LOW→HIGH'}
                        </span>
                      )}
                    </div>
                  </th>
                  <th className="py-3 px-4">Department & Worker</th>
                  <th
                    className="py-3 px-4 cursor-pointer hover:text-slate-700"
                    onClick={() => {
                      if (sortBy === 'createdAt') {
                        setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'));
                      } else {
                        setSortBy('createdAt');
                        setSortOrder('desc');
                      }
                    }}
                  >
                    <div className="flex items-center gap-1">
                      <span>Submitted</span>
                      <ArrowUpDown className="h-3 w-3" />
                      {sortBy === 'createdAt' && (
                        <span className="text-[9px] font-bold text-teal-600">
                          {sortOrder === 'desc' ? 'NEW→OLD' : 'OLD→NEW'}
                        </span>
                      )}
                    </div>
                  </th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {reports.map((report) => (
                  <tr key={report.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4 max-w-xs">
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-semibold">
                          #{report.id}
                        </span>
                        <p className="font-semibold text-slate-900 truncate">{report.title}</p>
                      </div>
                      <p className="text-[11px] text-slate-500 truncate mt-0.5">
                        {report.address || `${report.latitude.toFixed(4)}, ${report.longitude.toFixed(4)}`}
                      </p>
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span className="font-medium text-slate-800">
                        {formatCategory(report.category)}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <StatusBadge status={report.status} size="sm" />
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <PriorityBadge priority={report.priority} size="sm" />
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <p className="font-medium text-slate-800">
                        {report.departmentName || '—'}
                      </p>
                      <p className="text-[11px] text-slate-500">
                        {report.assignedWorkerName ? report.assignedWorkerName : 'Unassigned'}
                      </p>
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap text-slate-500">
                      {formatDate(report.createdAt)}
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
        pageSize={10}
        onPageChange={setPage}
      />
    </div>
  );
};
