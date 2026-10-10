import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/hooks/use-auth';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notificationService } from '@/services/notification-service';
import { useToast } from '@/hooks/use-toast';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { EmptyState } from '@/components/ui/empty-state';
import { TableSkeleton } from '@/components/ui/skeleton';
import { ErrorPanel } from '@/components/ui/error-panel';
import { formatRelativeTime } from '@/lib/formatters';
import { Bell, CheckCheck, ArrowRight } from 'lucide-react';

export const NotificationsPage: React.FC = () => {
  const { user } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [filter, setFilter] = useState<'all' | 'unread'>('all');

  const { data: notifications = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['notifications-page', user?.id],
    queryFn: () => (user ? notificationService.getNotifications(user.id) : []),
    enabled: Boolean(user?.id),
  });

  // Mark single as read
  const markReadMutation = useMutation({
    mutationFn: (id: string) => notificationService.markAsRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications', user?.id] });
      queryClient.invalidateQueries({ queryKey: ['notifications-page', user?.id] });
    },
  });

  // Mark all as read
  const markAllMutation = useMutation({
    mutationFn: () => (user ? notificationService.markAllAsRead(user.id) : Promise.resolve()),
    onSuccess: () => {
      toast.success('All notifications marked as read.');
      queryClient.invalidateQueries({ queryKey: ['notifications', user?.id] });
      queryClient.invalidateQueries({ queryKey: ['notifications-page', user?.id] });
    },
  });

  const filteredNotifications = notifications.filter((n) => {
    if (filter === 'unread') return !n.isRead;
    return true;
  });

  const unreadCount = notifications.filter((n) => !n.isRead).length;

  const getReportUrl = (reportId?: string) => {
    if (!reportId || !user) return '#';
    switch (user.role) {
      case 'citizen':
        return `/citizen/reports/${reportId}`;
      case 'worker':
        return `/worker/assignments/${reportId}`;
      case 'admin':
        return `/admin/reports/${reportId}`;
    }
  };

  const getBreadcrumbDashboard = () => {
    if (!user) return '/dashboard';
    switch (user.role) {
      case 'citizen':
        return '/citizen/dashboard';
      case 'worker':
        return '/worker/dashboard';
      case 'admin':
        return '/admin/dashboard';
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      <Breadcrumbs
        items={[
          { label: 'Dashboard', href: getBreadcrumbDashboard() },
          { label: 'Notifications' },
        ]}
      />

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Notifications & Alerts
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Stay informed about your reports, assignment dispatches, and resolution progress.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => markAllMutation.mutate()}
              isLoading={markAllMutation.isPending}
              leftIcon={<CheckCheck className="h-4 w-4 text-teal-600" />}
              className="text-xs"
            >
              Mark all as read
            </Button>
          )}
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200">
        <button
          onClick={() => setFilter('all')}
          className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition-colors ${
            filter === 'all'
              ? 'border-teal-600 text-teal-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          All Notifications ({notifications.length})
        </button>
        <button
          onClick={() => setFilter('unread')}
          className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition-colors ${
            filter === 'unread'
              ? 'border-teal-600 text-teal-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Unread ({unreadCount})
        </button>
      </div>

      {/* Notifications list */}
      {isLoading ? (
        <TableSkeleton rows={5} />
      ) : isError ? (
        <ErrorPanel onRetry={refetch} message="Failed to load notifications." />
      ) : filteredNotifications.length === 0 ? (
        <EmptyState
          icon={Bell}
          title={filter === 'unread' ? 'No unread notifications' : 'No notifications yet'}
          description="You are completely up to date. Future updates on reports will appear here."
        />
      ) : (
        <Card className="border-slate-200/90 divide-y divide-slate-100 p-0 overflow-hidden shadow-sm">
          {filteredNotifications.map((notif) => (
            <div
              key={notif.id}
              className={`p-4 sm:p-5 transition-colors flex items-start justify-between gap-4 hover:bg-slate-50/80 ${
                !notif.isRead ? 'bg-teal-50/20' : 'bg-white'
              }`}
            >
              <div className="flex items-start gap-3.5">
                <div
                  className={`h-9 w-9 rounded-xl flex items-center justify-center shrink-0 mt-0.5 ${
                    !notif.isRead
                      ? 'bg-teal-100 text-teal-700'
                      : 'bg-slate-100 text-slate-500'
                  }`}
                >
                  <Bell className="h-4 w-4" />
                </div>

                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-semibold text-slate-900">{notif.title}</h4>
                    {!notif.isRead && (
                      <span className="h-2 w-2 rounded-full bg-teal-600 shrink-0" />
                    )}
                  </div>

                  <p className="text-xs text-slate-600 leading-relaxed max-w-xl">
                    {notif.message}
                  </p>

                  <div className="flex items-center gap-3 pt-1 text-[11px] text-slate-400">
                    <span>{formatRelativeTime(notif.createdAt)}</span>
                    {notif.reportId && (
                      <Link
                        to={getReportUrl(notif.reportId)}
                        className="font-medium text-teal-600 hover:text-teal-800 inline-flex items-center gap-0.5"
                      >
                        <span>View related issue</span>
                        <ArrowRight className="h-3 w-3" />
                      </Link>
                    )}
                  </div>
                </div>
              </div>

              {!notif.isRead && (
                <button
                  onClick={() => markReadMutation.mutate(notif.id)}
                  title="Mark as read"
                  className="text-xs text-slate-400 hover:text-teal-700 shrink-0 p-1"
                >
                  <CheckCheck className="h-4 w-4" />
                </button>
              )}
            </div>
          ))}
        </Card>
      )}
    </div>
  );
};
