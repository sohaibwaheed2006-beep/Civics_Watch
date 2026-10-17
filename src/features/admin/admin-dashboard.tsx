import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { analyticsService } from '@/services/analytics-service';
import { reportService } from '@/services/report-service';
import { bonusService } from '@/services/bonus-service';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { StatusBadge } from '@/components/data-display/status-badge';
import { PriorityBadge } from '@/components/data-display/priority-badge';
import { CardSkeleton, TableSkeleton } from '@/components/ui/skeleton';
import { ErrorPanel } from '@/components/ui/error-panel';
import { formatCategory, formatDate, formatRelativeTime } from '@/lib/formatters';
import {
  FileText,
  Clock,
  Wrench,
  CheckCircle2,
  AlertOctagon,
  Building,
  ArrowRight,
  ClipboardList,
  Calendar,
  Trophy,
  Star,
} from 'lucide-react';

export const AdminDashboard: React.FC = () => {
  // Fetch analytics summary
  const {
    data: analytics,
    isLoading: isAnalyticsLoading,
    isError: isAnalyticsError,
    refetch: refetchAnalytics,
  } = useQuery({
    queryKey: ['admin-analytics-overview'],
    queryFn: () => analyticsService.getAnalyticsSummary(),
  });

  // Fetch urgent/open reports needing attention
  const {
    data: priorityReportsData,
    isLoading: isReportsLoading,
  } = useQuery({
    queryKey: ['admin-priority-reports'],
    queryFn: () => reportService.getReports({ limit: 5, sortBy: 'priority', sortOrder: 'desc' }),
  });

  const priorityReports = priorityReportsData?.data || [];

  // Live worker-of-the-month leaderboard for the ongoing month.
  const { data: leaderboard = [] } = useQuery({
    queryKey: ['bonus-leaderboard'],
    queryFn: () => bonusService.leaderboard(),
  });

  // Most recent completed award.
  const { data: recentBonuses = [] } = useQuery({
    queryKey: ['bonus-history'],
    queryFn: () => bonusService.listRecent(3),
  });
  const latestBonus = recentBonuses[0];

  return (
    <div className="space-y-6">
      {/* Top Header & Quick Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Operations & Governance Dashboard
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Real-time municipal performance, incoming citizen reports, and field operations.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Link to="/admin/reports">
            <Button size="sm" leftIcon={<FileText className="h-4 w-4" />}>
              Review Reports
            </Button>
          </Link>
          <Link to="/admin/assignments">
            <Button variant="outline" size="sm" leftIcon={<ClipboardList className="h-4 w-4" />}>
              Dispatch Crews
            </Button>
          </Link>
          <Link to="/admin/departments">
            <Button variant="outline" size="sm" leftIcon={<Building className="h-4 w-4" />}>
              Departments
            </Button>
          </Link>
        </div>
      </div>

      {/* KPI Overview Cards */}
      {isAnalyticsLoading ? (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : isAnalyticsError || !analytics ? (
        <ErrorPanel onRetry={refetchAnalytics} message="Could not load analytics metrics." />
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <Card className="border-slate-200/90">
            <CardContent className="pt-0 flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-slate-500">Total Reports</p>
                <h3 className="text-2xl font-bold text-slate-900 mt-1">{analytics.totalReports}</h3>
              </div>
              <div className="h-10 w-10 rounded-xl bg-slate-100 text-slate-600 flex items-center justify-center">
                <FileText className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200/90">
            <CardContent className="pt-0 flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-amber-700">Open / Review</p>
                <h3 className="text-2xl font-bold text-amber-900 mt-1">{analytics.openReports}</h3>
              </div>
              <div className="h-10 w-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
                <Clock className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200/90">
            <CardContent className="pt-0 flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-blue-700">In Progress</p>
                <h3 className="text-2xl font-bold text-blue-900 mt-1">{analytics.inProgressReports}</h3>
              </div>
              <div className="h-10 w-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                <Wrench className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200/90">
            <CardContent className="pt-0 flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-emerald-700">Resolved</p>
                <h3 className="text-2xl font-bold text-emerald-900 mt-1">{analytics.resolvedReports}</h3>
              </div>
              <div className="h-10 w-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <CheckCircle2 className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200/90">
            <CardContent className="pt-0 flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-rose-700">Overdue SLA</p>
                <h3 className="text-2xl font-bold text-rose-900 mt-1">{analytics.overdueReports}</h3>
              </div>
              <div className="h-10 w-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
                <AlertOctagon className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Worker of the month: live leaderboard + most recent award. */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 border-amber-200/70 bg-gradient-to-br from-amber-50/70 to-white shadow-sm">
          <CardHeader className="flex-row items-center justify-between gap-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Trophy className="h-4 w-4 text-amber-500" />
              <span>Worker of the Month - Live Leaderboard</span>
            </CardTitle>
            <span className="text-[11px] text-slate-500">
              Rating 50% Â· Speed 30% Â· Volume 20%
            </span>
          </CardHeader>
          <CardContent className="space-y-2">
            {leaderboard.length === 0 ? (
              <p className="text-xs text-slate-500">
                No resolved reports in the current month yet. The leaderboard
                fills in as workers close tickets this month.
              </p>
            ) : (
              <div className="divide-y divide-slate-100">
                {leaderboard.slice(0, 5).map((row, idx) => (
                  <div
                    key={row.workerId}
                    className="flex items-center justify-between gap-3 py-2"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span
                        className={`inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold ${
                          idx === 0
                            ? 'bg-amber-500 text-white'
                            : idx === 1
                              ? 'bg-slate-400 text-white'
                              : idx === 2
                                ? 'bg-amber-800 text-white'
                                : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {idx + 1}
                      </span>
                      <span className="text-sm font-semibold text-slate-900 truncate">
                        {row.workerName}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-[11px] text-slate-600 shrink-0">
                      <span className="flex items-center gap-1">
                        <Star className="h-3 w-3 text-amber-500 fill-amber-400" />
                        {row.averageRating ? row.averageRating.toFixed(2) : 'â€“'}
                      </span>
                      <span>{row.resolvedCount} resolved</span>
                      <span>{Math.round(row.onTimeRate * 100)}% on-time</span>
                      <span className="font-mono font-semibold text-teal-700">
                        {row.totalScore.toFixed(2)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-slate-200/90 shadow-sm">
          <CardHeader>
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Trophy className="h-4 w-4 text-amber-500" />
              <span>Latest award</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            {latestBonus ? (
              <>
                <p className="text-slate-500">
                  {latestBonus.periodYear}-
                  {String(latestBonus.periodMonth).padStart(2, '0')}
                </p>
                <p className="text-base font-bold text-slate-900">
                  {latestBonus.workerName || `Worker #${latestBonus.workerId}`}
                </p>
                <div className="grid grid-cols-2 gap-2 pt-1">
                  <div className="rounded-md bg-slate-50 border border-slate-200 p-2">
                    <p className="text-slate-400">Score</p>
                    <p className="font-mono font-semibold text-teal-700">
                      {latestBonus.totalScore.toFixed(2)}
                    </p>
                  </div>
                  <div className="rounded-md bg-slate-50 border border-slate-200 p-2">
                    <p className="text-slate-400">Resolved</p>
                    <p className="font-semibold text-slate-800">
                      {latestBonus.resolvedCount}
                    </p>
                  </div>
                  <div className="rounded-md bg-slate-50 border border-slate-200 p-2">
                    <p className="text-slate-400">Avg rating</p>
                    <p className="font-semibold text-slate-800">
                      {latestBonus.averageRating.toFixed(2)}
                    </p>
                  </div>
                  <div className="rounded-md bg-slate-50 border border-slate-200 p-2">
                    <p className="text-slate-400">On-time</p>
                    <p className="font-semibold text-slate-800">
                      {Math.round(latestBonus.onTimeRate * 100)}%
                    </p>
                  </div>
                </div>
              </>
            ) : (
              <p className="text-slate-500">
                No past award recorded yet. Run{' '}
                <code className="font-mono text-[10px] bg-slate-100 px-1 rounded">
                  POST /bonus/award/previous-month
                </code>{' '}
                after each month closes.
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Priority Issues Requiring Attention Table */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900">
            Priority Issues Requiring Attention
          </h2>
          <Link
            to="/admin/reports"
            className="text-xs font-semibold text-teal-600 hover:text-teal-800 flex items-center gap-1"
          >
            <span>View all reports</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        {isReportsLoading ? (
          <TableSkeleton rows={4} />
        ) : (
          <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Issue Details</th>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Priority</th>
                    <th className="py-3 px-4">Date Reported</th>
                    <th className="py-3 px-4">Assigned Worker</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {priorityReports.map((report) => (
                    <tr key={report.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3.5 px-4 max-w-sm">
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
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <div className="flex items-center gap-1.5 text-slate-700 font-medium">
                          <Calendar className="h-3.5 w-3.5 text-teal-600 shrink-0" />
                          <span>{formatDate(report.createdAt)}</span>
                        </div>
                        <p className="text-[11px] text-slate-400 pl-5">
                          {formatRelativeTime(report.createdAt)}
                        </p>
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap text-slate-600">
                        {report.assignedWorkerName || (
                          <span className="italic text-slate-400">Unassigned</span>
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
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
