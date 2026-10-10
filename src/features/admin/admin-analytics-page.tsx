import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { analyticsService } from '@/services/analytics-service';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { CardSkeleton } from '@/components/ui/skeleton';
import { ErrorPanel } from '@/components/ui/error-panel';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import { Clock, CheckCircle2, AlertTriangle, ShieldCheck } from 'lucide-react';

export const AdminAnalyticsPage: React.FC = () => {
  const { data: analytics, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin-analytics-detailed'],
    queryFn: () => analyticsService.getAnalyticsSummary(),
  });

  return (
    <div className="space-y-6">
      <Breadcrumbs
        items={[
          { label: 'Admin Portal', href: '/admin/dashboard' },
          { label: 'Analytics & SLA Performance' },
        ]}
      />

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Municipal SLA & Analytics Intelligence
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Evaluate response times, department compliance rates, and incident resolution velocity.
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : isError || !analytics ? (
        <ErrorPanel onRetry={refetch} message="Unable to load analytics metrics." />
      ) : (
        <>
          {/* Top KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="border-slate-200/90">
              <CardContent className="pt-0 flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-slate-500">Average Resolution Time</p>
                  <h3 className="text-2xl font-bold text-slate-900 mt-1">
                    {analytics.avgResolutionTimeHours} hrs
                  </h3>
                </div>
                <div className="h-10 w-10 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center">
                  <Clock className="h-5 w-5" />
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-200/90">
              <CardContent className="pt-0 flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-slate-500">Overall SLA Compliance</p>
                  <h3 className="text-2xl font-bold text-emerald-900 mt-1">92.4%</h3>
                </div>
                <div className="h-10 w-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                  <ShieldCheck className="h-5 w-5" />
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-200/90">
              <CardContent className="pt-0 flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-slate-500">Total Solved Issues</p>
                  <h3 className="text-2xl font-bold text-slate-900 mt-1">
                    {analytics.resolvedReports}
                  </h3>
                </div>
                <div className="h-10 w-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                  <CheckCircle2 className="h-5 w-5" />
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-200/90">
              <CardContent className="pt-0 flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-slate-500">Overdue Incidents</p>
                  <h3 className="text-2xl font-bold text-rose-900 mt-1">
                    {analytics.overdueReports}
                  </h3>
                </div>
                <div className="h-10 w-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
                  <AlertTriangle className="h-5 w-5" />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Department Performance Table */}
          <Card className="border-slate-200/90 shadow-sm">
            <CardHeader>
              <CardTitle className="text-sm font-semibold">
                Department Performance & SLA Adherence
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase">
                    <tr>
                      <th className="py-2.5 px-3">Department</th>
                      <th className="py-2.5 px-3">Assigned Orders</th>
                      <th className="py-2.5 px-3">Resolved</th>
                      <th className="py-2.5 px-3">Avg Response Time</th>
                      <th className="py-2.5 px-3">SLA Compliance Rate</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {analytics.departmentPerformance.map((dept) => (
                      <tr key={dept.departmentId} className="hover:bg-slate-50/80">
                        <td className="py-3 px-3 font-semibold text-slate-900">
                          {dept.departmentName}
                        </td>
                        <td className="py-3 px-3">{dept.totalAssigned}</td>
                        <td className="py-3 px-3 font-medium text-emerald-700">
                          {dept.resolvedCount}
                        </td>
                        <td className="py-3 px-3">{dept.avgResolutionHours} hrs</td>
                        <td className="py-3 px-3">
                          <div className="flex items-center gap-2">
                            <div className="w-24 bg-slate-200 rounded-full h-2 overflow-hidden">
                              <div
                                className="bg-teal-600 h-2 rounded-full"
                                style={{ width: `${dept.complianceRate}%` }}
                              />
                            </div>
                            <span className="font-bold text-slate-800">
                              {dept.complianceRate}%
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Visualizations row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card className="border-slate-200/90 shadow-sm">
              <CardHeader>
                <CardTitle className="text-sm font-semibold">Volume by Problem Category</CardTitle>
              </CardHeader>
              <CardContent className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={analytics.byCategory} margin={{ top: 10, right: 10, left: -20, bottom: 25 }}>
                    <XAxis
                      dataKey="label"
                      tick={{ fontSize: 10, fill: '#64748b' }}
                      angle={-20}
                      textAnchor="end"
                    />
                    <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#0d9488" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card className="border-slate-200/90 shadow-sm">
              <CardHeader>
                <CardTitle className="text-sm font-semibold">Resolution Velocity Over Time</CardTitle>
              </CardHeader>
              <CardContent className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={analytics.overTime} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }} />
                    <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="submitted"
                      stroke="#0d9488"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="resolved"
                      stroke="#10b981"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
};
