import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/hooks/use-auth';
import { useQuery } from '@tanstack/react-query';
import { assignmentService } from '@/services/assignment-service';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { StatusBadge } from '@/components/data-display/status-badge';
import { PriorityBadge } from '@/components/data-display/priority-badge';
import { CardSkeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { ErrorPanel } from '@/components/ui/error-panel';
import { formatCategory, formatDate } from '@/lib/formatters';
import { getCategoryCoverImage, handleImageFallback } from '@/lib/category-images';
import {
  ClipboardList,
  Clock,
  Wrench,
  CheckCircle2,
  AlertTriangle,
  MapPin,
  Map,
  ArrowRight,
  Navigation,
} from 'lucide-react';

export const WorkerDashboard: React.FC = () => {
  const { user } = useAuth();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['worker-dashboard-assignments', user?.id],
    queryFn: () => (user ? assignmentService.getWorkerAssignments(user.id, { limit: 20 }) : Promise.reject()),
    enabled: Boolean(user?.id),
  });

  const assignments = data?.data || [];

  const totalAssigned = assignments.length;
  const awaitingAction = assignments.filter((a) => a.status === 'assigned').length;
  const inProgress = assignments.filter((a) => a.status === 'in_progress').length;
  const completed = assignments.filter((a) => a.status === 'resolved').length;
  const overdue = assignments.filter((a) => a.isOverdue && a.status !== 'resolved').length;

  const urgentTasks = assignments
    .filter((a) => a.status !== 'resolved')
    .slice(0, 3);

  return (
    <div className="space-y-6">
      {/* Worker Greeting Banner with Field Operations Photo */}
      <div className="rounded-2xl bg-gradient-to-r from-amber-900 via-amber-950 to-slate-900 p-6 sm:p-8 text-white shadow-xl relative overflow-hidden border border-amber-800/40">
        <img
          src="https://images.unsplash.com/photo-1504307651254-35680f356dfd?auto=format&fit=crop&w=1200&q=80"
          alt="Field Operations"
          onError={(e) => {
            const img = e.currentTarget as HTMLImageElement;
            if (!img.src.includes('/images/hero/worker-hero.jpg')) {
              img.src = '/images/hero/worker-hero.jpg';
            } else {
              img.style.display = 'none';
            }
          }}
          className="absolute inset-0 h-full w-full object-cover object-center opacity-25 mix-blend-screen pointer-events-none"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-amber-950/80 via-amber-900/60 to-transparent pointer-events-none" />
        <div className="relative z-10 max-w-2xl space-y-3">
          <span className="inline-block rounded-full bg-amber-500/20 px-3 py-1 text-xs font-semibold text-amber-200 border border-amber-400/30">
            Field Technician Portal &bull; {user?.departmentName || 'Public Works'}
          </span>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            Welcome, {user?.fullName || 'Technician'}!
          </h1>
          <p className="text-sm text-amber-100 leading-relaxed">
            Here are your dispatched maintenance orders. Inspect details, view navigation directions,
            and log your repair resolutions directly from the field.
          </p>
          <div className="pt-2 flex flex-wrap gap-3">
            <Link to="/worker/assignments">
              <Button
                size="lg"
                className="bg-white text-amber-900 hover:bg-amber-50 font-semibold shadow-md"
                leftIcon={<ClipboardList className="h-5 w-5 text-amber-700" />}
              >
                View All Work Orders ({totalAssigned})
              </Button>
            </Link>
            <Link to="/worker/map">
              <Button
                variant="outline"
                size="lg"
                className="border-amber-400/50 bg-amber-800/40 text-white hover:bg-amber-700/50"
                leftIcon={<Map className="h-5 w-5" />}
              >
                Open Field Map
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <Card className="border-slate-200/90">
          <CardContent className="pt-0 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500">Total Work Orders</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{totalAssigned}</h3>
            </div>
            <div className="h-10 w-10 rounded-xl bg-slate-100 text-slate-600 flex items-center justify-center">
              <ClipboardList className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200/90">
          <CardContent className="pt-0 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-amber-700">Awaiting Action</p>
              <h3 className="text-2xl font-bold text-amber-900 mt-1">{awaitingAction}</h3>
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
              <p className="text-xs font-medium text-emerald-700">Completed</p>
              <h3 className="text-2xl font-bold text-emerald-900 mt-1">{completed}</h3>
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
              <h3 className="text-2xl font-bold text-rose-900 mt-1">{overdue}</h3>
            </div>
            <div className="h-10 w-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
              <AlertTriangle className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Immediate Attention Tasks */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900">
            Immediate Action Orders
          </h2>
          {assignments.length > 0 && (
            <Link
              to="/worker/assignments"
              className="text-xs font-semibold text-teal-600 hover:text-teal-800 flex items-center gap-1"
            >
              <span>All work orders</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          )}
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>
        ) : isError ? (
          <ErrorPanel onRetry={refetch} message="Failed to load your work orders." />
        ) : urgentTasks.length === 0 ? (
          <EmptyState
            title="All tasks completed!"
            description="You currently have no pending tasks awaiting inspection or repair."
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {urgentTasks.map((assignment) => {
              const photoUrl =
                assignment.report.photos && assignment.report.photos.length > 0
                  ? assignment.report.photos[0].url
                  : getCategoryCoverImage(assignment.report.category);

              return (
                <Card
                  key={assignment.id}
                  hoverEffect
                  className="flex flex-col justify-between group overflow-hidden border-slate-200/90 hover:border-amber-400"
                >
                  <div>
                    {/* Card photo header */}
                    <div className="relative aspect-[16/9] -mx-5 -mt-5 mb-3 bg-slate-100 overflow-hidden border-b border-slate-100">
                      <img
                        src={photoUrl}
                        alt={assignment.report.title}
                        onError={(e) => {
                          const target = e.currentTarget as HTMLImageElement;
                          const catCover = getCategoryCoverImage(assignment.report.category);
                          if (target.src !== catCover) {
                            target.src = catCover;
                          } else {
                            handleImageFallback(e, assignment.report.category);
                          }
                        }}
                        className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                        loading="lazy"
                      />
                      <div className="absolute top-2.5 left-2.5">
                        <StatusBadge status={assignment.report.status} size="sm" />
                      </div>
                      <div className="absolute top-2.5 right-2.5">
                        <PriorityBadge priority={assignment.report.priority} size="sm" />
                      </div>
                    </div>

                    <h3 className="text-sm font-semibold text-slate-900 group-hover:text-amber-700 transition-colors line-clamp-1">
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
            );
          })}
        </div>
        )}
      </div>
    </div>
  );
};
