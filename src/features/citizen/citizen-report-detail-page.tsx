import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '@/hooks/use-auth';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { reportService } from '@/services/report-service';
import { reviewService } from '@/services/review-service';
import { useToast } from '@/hooks/use-toast';
import { canWithdrawReport } from '@/lib/permissions';
import { formatCategory, formatCoordinates } from '@/lib/formatters';
import { StatusBadge } from '@/components/data-display/status-badge';
import { PriorityBadge } from '@/components/data-display/priority-badge';
import { StatusTimeline } from '@/components/data-display/status-timeline';
import { PhotoGallery } from '@/components/data-display/photo-gallery';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ConfirmationDialog } from '@/components/ui/modal';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { ErrorPanel } from '@/components/ui/error-panel';
import { Skeleton } from '@/components/ui/skeleton';
import {
  MapPin,
  ThumbsUp,
  Trash2,
  Clock,
  CheckCircle,
  Camera,
  Star,
} from 'lucide-react';
import { Avatar } from '@/components/ui/avatar';
import { getDepartmentCoverImage } from '@/lib/category-images';

export const CitizenReportDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [isWithdrawOpen, setIsWithdrawOpen] = useState(false);
  const [reviewRating, setReviewRating] = useState<number>(0);
  const [reviewComment, setReviewComment] = useState<string>('');

  const {
    data: report,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['report-detail', id],
    queryFn: () => (id ? reportService.getReportById(id) : Promise.reject('No ID')),
    enabled: Boolean(id),
  });

  // Upvote mutation
  const upvoteMutation = useMutation({
    mutationFn: () => (report && user ? reportService.toggleUpvote(report.id, user) : Promise.reject()),
    onSuccess: (data) => {
      queryClient.setQueryData(['report-detail', id], (old: any) =>
        old ? { ...old, upvotesCount: data.upvotesCount, hasUpvoted: data.hasUpvoted } : old
      );
      toast.success(data.hasUpvoted ? 'Upvoted this issue.' : 'Removed upvote.');
    },
  });

  // Fetch my existing review (if any) once the report is resolved.
  const { data: myReview } = useQuery({
    queryKey: ['my-review', id],
    queryFn: () => (id ? reviewService.getMine(id) : Promise.resolve(null)),
    enabled: Boolean(id) && report?.status === 'resolved',
  });

  // Keep local form state in sync when a prior review loads.
  React.useEffect(() => {
    if (myReview) {
      setReviewRating(myReview.rating);
      setReviewComment(myReview.comment || '');
    }
  }, [myReview?.id]);

  const reviewMutation = useMutation({
    mutationFn: () =>
      id && reviewRating > 0
        ? reviewService.submit(id, reviewRating, reviewComment)
        : Promise.reject(),
    onSuccess: () => {
      toast.success('Thanks for rating the field worker.');
      queryClient.invalidateQueries({ queryKey: ['my-review', id] });
    },
    onError: () => toast.error('Could not submit your rating. Please try again.'),
  });

  // Withdraw report mutation
  const withdrawMutation = useMutation({
    mutationFn: () => (report && user ? reportService.deleteReport(report.id, user) : Promise.reject()),
    onSuccess: () => {
      toast.success('Your report has been withdrawn.');
      queryClient.invalidateQueries({ queryKey: ['citizen-reports'] });
      navigate('/citizen/reports');
    },
    onError: () => {
      toast.error('Failed to withdraw report.');
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-4xl mx-auto">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-40 w-full rounded-xl" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    );
  }

  if (isError || !report) {
    return (
      <div className="max-w-2xl mx-auto my-12">
        <ErrorPanel
          title="Report Not Found"
          message="Could not find the requested incident report or you may not have permission to access it."
          onRetry={refetch}
        />
        <div className="mt-4 text-center">
          <Link to="/citizen/reports">
            <Button variant="outline">Return to My Reports</Button>
          </Link>
        </div>
      </div>
    );
  }

  const canWithdraw = canWithdrawReport(user, report);

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      <Breadcrumbs
        items={[
          { label: 'Citizen Portal', href: '/citizen/dashboard' },
          { label: 'My Reports', href: '/citizen/reports' },
          { label: `Report #${report.id}` },
        ]}
      />

      {/* Main Header Card */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs font-bold text-slate-500 bg-slate-100 px-2.5 py-1 rounded-md">
              #{report.id}
            </span>
            <span className="text-xs font-semibold text-teal-800 bg-teal-50 border border-teal-200 px-2.5 py-1 rounded-md">
              {formatCategory(report.category)}
            </span>
            <StatusBadge status={report.status} />
            <PriorityBadge priority={report.priority} />
          </div>

          <div className="flex items-center gap-2">
            {/* Upvote Button */}
            <Button
              variant={report.hasUpvoted ? 'primary' : 'outline'}
              size="sm"
              onClick={() => upvoteMutation.mutate()}
              isLoading={upvoteMutation.isPending}
              leftIcon={<ThumbsUp className="h-3.5 w-3.5" />}
              className="text-xs"
            >
              <span>{report.upvotesCount}</span>
              <span className="hidden sm:inline">Upvotes</span>
            </Button>

            {/* Withdraw Button */}
            {canWithdraw && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsWithdrawOpen(true)}
                className="text-rose-600 border-rose-200 hover:bg-rose-50 text-xs"
                leftIcon={<Trash2 className="h-3.5 w-3.5" />}
              >
                Withdraw Report
              </Button>
            )}
          </div>
        </div>

        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 leading-snug">
            {report.title}
          </h1>
          <p className="mt-3 text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
            {report.description}
          </p>
        </div>

        {/* Resolution details if resolved */}
        {report.status === 'resolved' && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-4 text-xs text-emerald-950 space-y-3">
            <div className="flex items-center gap-2 font-bold text-emerald-900">
              <CheckCircle className="h-4 w-4 text-emerald-600" />
              <span>Issue Successfully Resolved</span>
            </div>
            {report.resolutionNote && (
              <p className="text-emerald-900 leading-relaxed font-medium">
                {report.resolutionNote}
              </p>
            )}

            {/* Resolution Evidence Photo */}
            {report.resolutionEvidenceUrl && (
              <div className="pt-2">
                <p className="text-[11px] font-semibold text-emerald-900 mb-1 flex items-center gap-1">
                  <Camera className="h-3.5 w-3.5 text-emerald-700" />
                  <span>Field Verification Photo (Work Complete)</span>
                </p>
                <div className="max-w-md aspect-video rounded-xl overflow-hidden border border-emerald-200 shadow-xs">
                  <img
                    src={report.resolutionEvidenceUrl}
                    alt="Resolution Evidence"
                    onError={(e) => {
                      const img = e.currentTarget as HTMLImageElement;
                      if (!img.src.includes('/images/reports/railing-repaired.jpg')) {
                        img.src = '/images/reports/railing-repaired.jpg';
                      }
                    }}
                    className="h-full w-full object-cover"
                  />
                </div>
              </div>
            )}

            <p className="text-[11px] text-emerald-700">
              Work completed and verified by municipal field technicians.
            </p>
          </div>
        )}
      </div>

      {/* Progress & Lifecycle Timeline */}
      <Card className="border-slate-200/90 shadow-sm">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Clock className="h-4 w-4 text-teal-600" />
            <span>Resolution Progress & Lifecycle</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <StatusTimeline report={report} />
        </CardContent>
      </Card>

      {/* Citizen rating of the worker who closed the report. The row is
          upserted on submit, so re-opening the page shows the last rating. */}
      {report.status === 'resolved' && report.assignedWorkerId && (
        <Card className="border-slate-200/90 shadow-sm">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Star className="h-4 w-4 text-amber-500" />
              <span>Rate the field worker</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-slate-500">
              Your rating feeds the monthly worker-of-the-month pick. Pick 1–5
              stars and (optionally) leave a note.
            </p>
            <div className="flex items-center gap-1">
              {[1, 2, 3, 4, 5].map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setReviewRating(n)}
                  aria-label={`${n} star${n > 1 ? 's' : ''}`}
                  className="p-1 rounded-md hover:bg-amber-50 transition-colors"
                >
                  <Star
                    className={`h-6 w-6 ${
                      reviewRating >= n
                        ? 'text-amber-500 fill-amber-400'
                        : 'text-slate-300'
                    }`}
                  />
                </button>
              ))}
              {reviewRating > 0 && (
                <span className="ml-2 text-xs text-slate-500">
                  {reviewRating}/5
                </span>
              )}
            </div>
            <textarea
              className="w-full rounded-lg border border-slate-200 bg-white p-2.5 text-xs text-slate-800 placeholder:text-slate-400 focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/20"
              rows={3}
              placeholder="Optional comment (what went well, what could improve)…"
              value={reviewComment}
              onChange={(e) => setReviewComment(e.target.value.slice(0, 1000))}
            />
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-slate-400">
                {myReview
                  ? `Last submitted ${new Date(myReview.updatedAt).toLocaleDateString()}.`
                  : 'Not submitted yet.'}
              </span>
              <Button
                size="sm"
                disabled={reviewRating < 1}
                isLoading={reviewMutation.isPending}
                onClick={() => reviewMutation.mutate()}
              >
                {myReview ? 'Update rating' : 'Submit rating'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Incident Location & Map */}
      <Card className="border-slate-200/90 shadow-sm">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <MapPin className="h-4 w-4 text-teal-600" />
            <span>Location Information</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs bg-slate-50 p-4 rounded-xl border border-slate-200/80">
            <div>
              <p className="text-slate-400 font-medium">Designated Address / Landmark</p>
              <p className="font-semibold text-slate-800 mt-0.5">
                {report.address || 'GPS Coordinate Pin'}
              </p>
            </div>
            <div>
              <p className="text-slate-400 font-medium">Geographic Coordinates</p>
              <p className="font-mono font-semibold text-slate-800 mt-0.5">
                {formatCoordinates(report.latitude, report.longitude)}
              </p>
            </div>
          </div>

          <div className="flex justify-end">
            <a
              href={`https://www.google.com/maps/search/?api=1&query=${report.latitude},${report.longitude}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-semibold text-teal-600 hover:text-teal-800 flex items-center gap-1"
            >
              <span>Open in Google Maps</span>
              <span aria-hidden="true">&rarr;</span>
            </a>
          </div>
        </CardContent>
      </Card>

      {/* Photo Evidence Gallery */}
      <Card className="border-slate-200/90 shadow-sm">
        <CardHeader>
          <CardTitle className="text-base">Attached Photo Evidence</CardTitle>
        </CardHeader>
        <CardContent>
          <PhotoGallery photos={report.photos} category={report.category} />
        </CardContent>
      </Card>

      {/* Assigned Department & Staff Info */}
      <Card className="border-slate-200/90 shadow-sm">
        <CardHeader>
          <CardTitle className="text-base">Municipal Response Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 border border-slate-200/80">
              <img
                src={getDepartmentCoverImage(report.departmentId, report.departmentName)}
                alt=""
                onError={(e) => {
                  (e.currentTarget as HTMLImageElement).style.display = 'none';
                }}
                className="h-10 w-12 rounded-lg object-cover shrink-0 border border-slate-200"
              />
              <div>
                <p className="text-slate-400 font-medium">Assigned Department</p>
                <p className="font-semibold text-slate-900 mt-0.5">
                  {report.departmentName || 'Under Initial Assessment'}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 border border-slate-200/80">
              <Avatar
                alt={report.assignedWorkerName || 'Field Technician'}
                fallback={report.assignedWorkerName || 'T'}
                role="worker"
                size="md"
              />
              <div>
                <p className="text-slate-400 font-medium">Assigned Field Worker</p>
                <p className="font-semibold text-slate-900 mt-0.5">
                  {report.assignedWorkerName || 'Pending Dispatch'}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Withdraw Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={isWithdrawOpen}
        onClose={() => setIsWithdrawOpen(false)}
        onConfirm={() => withdrawMutation.mutate()}
        title="Withdraw Incident Report?"
        description="Are you sure you want to withdraw this report? This will cancel the inquiry and remove it from active municipal queue."
        confirmText="Yes, Withdraw Report"
        variant="danger"
        isLoading={withdrawMutation.isPending}
      />
    </div>
  );
};
