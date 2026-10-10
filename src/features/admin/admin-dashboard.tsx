import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { analyticsService } from '@/services/analytics-service';
import { reportService } from '@/services/report-service';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { StatusBadge } from '@/components/data-display/status-badge';
import { PriorityBadge } from '@/components/data-display/priority-badge';
import { CardSkeleton, TableSkeleton } from '@/components/ui/skeleton';
import { ErrorPanel } from '@/components/ui/error-panel';
import { formatCategory } from '@/lib/formatters';
import {
  FileText,
  Clock,
  Wrench,
  CheckCircle2,
  AlertOctagon,
  Building,
  ArrowRight,
  ClipboardList,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
} from 'recharts';

const STATUS_COLORS: Record<string, string> = {
  submitted: '#94a3b8',
  under_review: '#f59e0b',
  assigned: '#3b82f6',
  in_progress: '#0d9488',
  resolved: '#10b981',
  rejected: '#f43f5e',
};

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

      {/* Visualizations Section (Recharts) */}
      {analytics && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Status Breakdown (Donut) */}
          <Card className="border-slate-200/90 shadow-sm">
            <CardHeader>
              <CardTitle className="text-sm font-semibold">Reports by Status</CardTitle>
            </CardHeader>
            <CardContent className="h-64 flex flex-col items-center justify-center">
              <ResponsiveContainer width="100%" height="80%">
                <PieChart>
                  <Pie
                    data={analytics.byStatus}
                    dataKey="count"
                    nameKey="label"
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={75}
                    paddingAngle={3}
                  >
                    {analytics.byStatus.map((entry) => (
                      <Cell
                        key={entry.status}
                        fill={STATUS_COLORS[entry.status] || '#cbd5e1'}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#ffffff',
                      borderRadius: '0.75rem',
                      border: '1px solid #e2e8f0',
                      fontSize: '12px',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>

              <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-[11px] text-slate-600 mt-1">
                {analytics.byStatus.slice(0, 4).map((item) => (
                  <div key={item.status} className="flex items-center gap-1.5">
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ backgroundColor: STATUS_COLORS[item.status] }}
                    />
                    <span>{item.label}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Category Breakdown (Bar Chart) */}
          <Card className="border-slate-200/90 shadow-sm">
            <CardHeader>
              <CardTitle className="text-sm font-semibold">Reports by Category</CardTitle>
            </CardHeader>
            <CardContent className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={analytics.byCategory} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                  <XAxis
                    dataKey="label"
                    tick={{ fontSize: 10, fill: '#64748b' }}
                    interval={0}
                    angle={-20}
                    textAnchor="end"
                  />
                  <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#ffffff',
                      borderRadius: '0.75rem',
                      border: '1px solid #e2e8f0',
                      fontSize: '12px',
                    }}
                  />
                  <Bar dataKey="count" fill="#0d9488" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Time Series Trend (Line Chart) */}
          <Card className="border-slate-200/90 shadow-sm">
            <CardHeader>
              <CardTitle className="text-sm font-semibold">Weekly Report Velocity</CardTitle>
            </CardHeader>
            <CardContent className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={analytics.overTime} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }} />
                  <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#ffffff',
                      borderRadius: '0.75rem',
                      border: '1px solid #e2e8f0',
                      fontSize: '12px',
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="submitted"
                    stroke="#0d9488"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    name="Submitted"
                  />
                  <Line
                    type="monotone"
                    dataKey="resolved"
                    stroke="#10b981"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    name="Resolved"
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>
      )}

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
