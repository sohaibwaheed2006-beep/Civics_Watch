import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/hooks/use-auth';
import { useQuery } from '@tanstack/react-query';
import { reportService } from '@/services/report-service';
import { notificationService } from '@/services/notification-service';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ReportCard } from '@/components/reports/report-card';
import { CardSkeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { ErrorPanel } from '@/components/ui/error-panel';
import {
  PlusCircle,
  Clock,
  Wrench,
  CheckCircle2,
  FileText,
  MapPin,
  ArrowRight,
  Bell,
  Map,
} from 'lucide-react';
import { formatRelativeTime } from '@/lib/formatters';

export const CitizenDashboard: React.FC = () => {
  const { user } = useAuth();

  // Fetch citizen reports
  const {
    data: reportsData,
    isLoading: isReportsLoading,
    isError: isReportsError,
    refetch: refetchReports,
  } = useQuery({
    queryKey: ['citizen-reports', user?.id],
    queryFn: () => reportService.getReports({ citizenId: user?.id, limit: 20 }),
    enabled: Boolean(user?.id),
  });

  // Fetch notifications
  const { data: notifications = [] } = useQuery({
    queryKey: ['notifications', user?.id],
    queryFn: () => (user ? notificationService.getNotifications(user.id) : []),
    enabled: Boolean(user?.id),
  });

  const reports = reportsData?.data || [];

  // Derive real statistics from citizen reports
  const totalReports = reports.length;
  const awaitingReview = reports.filter((r) => ['submitted', 'under_review'].includes(r.status)).length;
  const inProgress = reports.filter((r) => ['assigned', 'in_progress'].includes(r.status)).length;
  const resolved = reports.filter((r) => r.status === 'resolved').length;

  const recentReports = reports.slice(0, 3);
  const unreadNotifications = notifications.filter((n) => !n.isRead).slice(0, 3);

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="rounded-2xl bg-gradient-to-r from-teal-700 via-teal-800 to-slate-900 p-6 sm:p-8 text-white shadow-lg relative overflow-hidden">
        <div className="relative z-10 max-w-2xl space-y-3">
          <span className="inline-block rounded-full bg-teal-500/20 px-3 py-1 text-xs font-semibold text-teal-200 border border-teal-400/30">
            Citizen Community Portal
          </span>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            Hello, {user?.fullName || 'Resident'}!
          </h1>
          <p className="text-sm text-teal-100 leading-relaxed">
            Spot a hazard or broken infrastructure in your neighborhood? Submit a report with photos
            and GPS coordinates. We'll dispatch field teams to resolve it.
          </p>
          <div className="pt-2 flex flex-wrap gap-3">
            <Link to="/citizen/reports/new">
              <Button
                size="lg"
                className="bg-white text-teal-900 hover:bg-teal-50 font-semibold shadow-md"
                leftIcon={<PlusCircle className="h-5 w-5 text-teal-700" />}
              >
                Report an Issue
              </Button>
            </Link>
            <Link to="/citizen/map">
              <Button
                variant="outline"
                size="lg"
                className="border-teal-400/50 bg-teal-800/40 text-white hover:bg-teal-700/50"
                leftIcon={<Map className="h-5 w-5" />}
              >
                Explore Issue Map
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-slate-200/90">
          <CardContent className="pt-0 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500">Total Submitted</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{totalReports}</h3>
            </div>
            <div className="h-10 w-10 rounded-xl bg-slate-100 text-slate-600 flex items-center justify-center">
              <FileText className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200/90">
          <CardContent className="pt-0 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-amber-700">Awaiting Review</p>
              <h3 className="text-2xl font-bold text-amber-900 mt-1">{awaitingReview}</h3>
            </div>
            <div className="h-10 w-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <Clock className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200/90">
          <CardContent className="pt-0 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-teal-700">In Progress</p>
              <h3 className="text-2xl font-bold text-teal-900 mt-1">{inProgress}</h3>
            </div>
            <div className="h-10 w-10 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center">
              <Wrench className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200/90">
          <CardContent className="pt-0 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-emerald-700">Resolved</p>
              <h3 className="text-2xl font-bold text-emerald-900 mt-1">{resolved}</h3>
            </div>
            <div className="h-10 w-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <CheckCircle2 className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main content split: Recent Reports & Notifications */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent reports list (2 cols) */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-900">My Recent Reports</h2>
            {reports.length > 0 && (
              <Link
                to="/citizen/reports"
                className="text-xs font-semibold text-teal-600 hover:text-teal-800 flex items-center gap-1"
              >
                <span>View all ({totalReports})</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            )}
          </div>

          {isReportsLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <CardSkeleton />
              <CardSkeleton />
            </div>
          ) : isReportsError ? (
            <ErrorPanel onRetry={refetchReports} message="Unable to load your reports right now." />
          ) : reports.length === 0 ? (
            <EmptyState
              title="No reports filed yet"
              description="Have you noticed a pothole, street light outage, or garbage pile? Report it now and track repairs in real time."
              actionText="File Your First Report"
              onAction={() => (window.location.href = '/citizen/reports/new')}
            />
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {recentReports.map((report) => (
                <ReportCard
                  key={report.id}
                  report={report}
                  detailUrl={`/citizen/reports/${report.id}`}
                />
              ))}
            </div>
          )}
        </div>

        {/* Notifications preview (1 col) */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Bell className="h-4 w-4 text-teal-600" />
              <span>Recent Updates</span>
            </h3>
            <Link
              to="/citizen/notifications"
              className="text-xs font-semibold text-teal-600 hover:text-teal-800"
            >
              See all
            </Link>
          </div>

          <Card className="border-slate-200/90 divide-y divide-slate-100 p-0 overflow-hidden">
            {unreadNotifications.length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-400">
                You're all caught up! No unread notifications.
              </div>
            ) : (
              unreadNotifications.map((notif) => (
                <div key={notif.id} className="p-4 hover:bg-slate-50 transition-colors">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-semibold text-slate-900">{notif.title}</p>
                    <span className="text-[10px] text-slate-400">
                      {formatRelativeTime(notif.createdAt)}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 mt-1 leading-relaxed">{notif.message}</p>
                  {notif.reportId && (
                    <Link
                      to={`/citizen/reports/${notif.reportId}`}
                      className="mt-2 inline-flex items-center gap-1 text-[11px] font-medium text-teal-600 hover:text-teal-800"
                    >
                      <span>Check status</span>
                      <ArrowRight className="h-3 w-3" />
                    </Link>
                  )}
                </div>
              ))
            )}
          </Card>

          {/* Quick Help Box */}
          <div className="rounded-xl border border-teal-100 bg-teal-50/50 p-4 text-xs text-teal-900 space-y-2">
            <h4 className="font-semibold flex items-center gap-1.5">
              <MapPin className="h-4 w-4 text-teal-600" />
              <span>Civic Tip</span>
            </h4>
            <p className="text-slate-600 leading-relaxed text-[11px]">
              Attaching clear photos and accurate GPS location pins helps municipal field crews
              identify and repair problems up to 40% faster.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
