import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/hooks/use-auth';
import { useQuery } from '@tanstack/react-query';
import { reportService } from '@/services/report-service';
import { ReportFilters } from '@/components/reports/report-filters';
import { ReportCard } from '@/components/reports/report-card';
import { StatusBadge } from '@/components/data-display/status-badge';
import { PriorityBadge } from '@/components/data-display/priority-badge';
import { Pagination } from '@/components/data-display/pagination';
import { CardSkeleton, TableSkeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { ErrorPanel } from '@/components/ui/error-panel';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { Button } from '@/components/ui/button';
import { formatCategory, formatDate } from '@/lib/formatters';
import { useDebounce } from '@/hooks/use-debounce';
import { PlusCircle, ArrowRight } from 'lucide-react';
import { ReportCategory, ReportPriority, ReportStatus } from '@/types/report';

export const CitizenReportsPage: React.FC = () => {
  const { user } = useAuth();

  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<ReportStatus | 'all'>('all');
  const [category, setCategory] = useState<ReportCategory | 'all'>('all');
  const [priority, setPriority] = useState<ReportPriority | 'all'>('all');
  const [page, setPage] = useState(1);
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

  const debouncedSearch = useDebounce(search, 300);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: [
      'citizen-reports-list',
      user?.id,
      debouncedSearch,
      status,
      category,
      priority,
      page,
    ],
    queryFn: () =>
      reportService.getReports({
        citizenId: user?.id,
        search: debouncedSearch,
        status,
        category,
        priority,
        page,
        limit: 8,
      }),
    enabled: Boolean(user?.id),
  });

  const reports = data?.data || [];
  const totalPages = data?.totalPages || 1;
  const totalItems = data?.total || 0;

  const handleResetFilters = () => {
    setSearch('');
    setStatus('all');
    setCategory('all');
    setPriority('all');
    setPage(1);
  };

  return (
    <div className="space-y-6">
      <Breadcrumbs
        items={[
          { label: 'Citizen Portal', href: '/citizen/dashboard' },
          { label: 'My Reports' },
        ]}
      />

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">My Reports</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Track real-time progress and resolutions for all neighborhood issues you've reported.
          </p>
        </div>
        <Link to="/citizen/reports/new">
          <Button leftIcon={<PlusCircle className="h-4 w-4" />}>
            Report an Issue
          </Button>
        </Link>
      </div>

      {/* Filters Toolbar */}
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
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        onReset={handleResetFilters}
      />

      {/* Content Rendering */}
      {isLoading ? (
        viewMode === 'grid' ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <CardSkeleton key={i} />
            ))}
          </div>
        ) : (
          <TableSkeleton rows={5} />
        )
      ) : isError ? (
        <ErrorPanel onRetry={refetch} message="Unable to load your report history." />
      ) : reports.length === 0 ? (
        <EmptyState
          title="No reports match your filters"
          description="Try adjusting your status or category filters, or file a new neighborhood issue."
          actionText={search || status !== 'all' ? 'Reset Filters' : 'Submit a Report'}
          onAction={search || status !== 'all' ? handleResetFilters : () => (window.location.href = '/citizen/reports/new')}
        />
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {reports.map((report) => (
            <ReportCard
              key={report.id}
              report={report}
              detailUrl={`/citizen/reports/${report.id}`}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Title & Location</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Priority</th>
                  <th className="py-3 px-4">Reported Date</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {reports.map((report) => (
                  <tr key={report.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4 max-w-xs">
                      <p className="font-semibold text-slate-900 truncate">{report.title}</p>
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
                    <td className="py-3.5 px-4 whitespace-nowrap text-slate-500">
                      {formatDate(report.createdAt)}
                    </td>
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <Link
                        to={`/citizen/reports/${report.id}`}
                        className="inline-flex items-center gap-1 font-semibold text-teal-600 hover:text-teal-800"
                      >
                        <span>Details</span>
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
        pageSize={8}
        onPageChange={setPage}
      />
    </div>
  );
};
