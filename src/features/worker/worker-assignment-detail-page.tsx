import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '@/hooks/use-auth';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { reportService } from '@/services/report-service';
import { useToast } from '@/hooks/use-toast';
import { formatCategory, formatCoordinates } from '@/lib/formatters';
import { StatusBadge } from '@/components/data-display/status-badge';
import { PriorityBadge } from '@/components/data-display/priority-badge';
import { StatusTimeline } from '@/components/data-display/status-timeline';
import { PhotoGallery } from '@/components/data-display/photo-gallery';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Modal } from '@/components/ui/modal';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { ErrorPanel } from '@/components/ui/error-panel';
import { Skeleton } from '@/components/ui/skeleton';
import {
  MapPin,
  Navigation,
  Wrench,
  CheckCircle2,
  Clock,
  FileCheck,
} from 'lucide-react';

export const WorkerAssignmentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [isResolveModalOpen, setIsResolveModalOpen] = useState(false);
  const [resolutionNote, setResolutionNote] = useState('');
  const [evidenceUrl, setEvidenceUrl] = useState('');
  const [noteError, setNoteError] = useState<string | null>(null);

  // Fetch report
  const {
    data: report,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['worker-order-detail', id],
    queryFn: () => (id ? reportService.getReportById(id) : Promise.reject('No ID')),
    enabled: Boolean(id),
  });

  // Start Work Mutation (assigned -> in_progress)
  const startWorkMutation = useMutation({
    mutationFn: () =>
      report && user
        ? reportService.updateReportStatus(
            report.id,
            { status: 'in_progress', note: 'Field technician commenced remediation work.' },
            user
          )
        : Promise.reject(),
    onSuccess: () => {
      toast.success('Work commenced! Status updated to In Progress.');
      queryClient.invalidateQueries({ queryKey: ['worker-order-detail', id] });
      queryClient.invalidateQueries({ queryKey: ['worker-assignments-list'] });
    },
    onError: () => toast.error('Failed to update status to In Progress.'),
  });

  // Mark Completed / Resolved Mutation
  const completeWorkMutation = useMutation({
    mutationFn: () => {
      if (!resolutionNote.trim()) {
        setNoteError('Please provide work resolution notes explaining the fix.');
        return Promise.reject('Note required');
      }
      return report && user
        ? reportService.updateReportStatus(
            report.id,
            {
              status: 'resolved',
              note: resolutionNote,
              resolutionEvidenceUrl: evidenceUrl || undefined,
            },
            user
          )
        : Promise.reject();
    },
    onSuccess: () => {
      toast.success('Task marked Resolved! Completion logged in municipal records.');
      queryClient.invalidateQueries({ queryKey: ['worker-order-detail', id] });
      queryClient.invalidateQueries({ queryKey: ['worker-assignments-list'] });
      setIsResolveModalOpen(false);
    },
    onError: (err: any) => {
      if (err !== 'Note required') toast.error('Failed to complete work order.');
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
          title="Work Order Not Found"
          message="Could not load the requested work order."
          onRetry={refetch}
        />
        <div className="mt-4 text-center">
          <Link to="/worker/assignments">
            <Button variant="outline">Back to Work Orders</Button>
          </Link>
        </div>
      </div>
    );
  }

  const isAssigned = report.status === 'assigned';
  const isInProgress = report.status === 'in_progress';
  const isResolved = report.status === 'resolved';

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      <Breadcrumbs
        items={[
          { label: 'Worker Portal', href: '/worker/dashboard' },
          { label: 'Assigned Work Orders', href: '/worker/assignments' },
          { label: `Order #${report.id}` },
        ]}
      />

      {/* Main Order Header Card */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs font-bold text-slate-500 bg-slate-100 px-2.5 py-1 rounded-md">
              Order #{report.id}
            </span>
            <span className="text-xs font-semibold text-teal-800 bg-teal-50 border border-teal-200 px-2.5 py-1 rounded-md">
              {formatCategory(report.category)}
            </span>
            <StatusBadge status={report.status} />
            <PriorityBadge priority={report.priority} />
          </div>

          <div className="flex items-center gap-2">
            <a
              href={`https://www.google.com/maps/dir/?api=1&destination=${report.latitude},${report.longitude}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button
                variant="outline"
                size="sm"
                leftIcon={<Navigation className="h-4 w-4 text-teal-600" />}
              >
                Driving Directions
              </Button>
            </a>
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

        {/* Action Controls Bar */}
        <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center gap-3">
          {isAssigned && (
            <Button
              size="lg"
              onClick={() => startWorkMutation.mutate()}
              isLoading={startWorkMutation.isPending}
              leftIcon={<Wrench className="h-5 w-5" />}
              className="bg-teal-600 hover:bg-teal-700 text-white font-semibold"
            >
              Start Work Order (In Progress)
            </Button>
          )}

          {isInProgress && (
            <Button
              size="lg"
              onClick={() => {
                setNoteError(null);
                setIsResolveModalOpen(true);
              }}
              leftIcon={<CheckCircle2 className="h-5 w-5" />}
              className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold"
            >
              Mark Completed (Log Resolution)
            </Button>
          )}

          {isResolved && (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-xs text-emerald-900 flex items-center gap-2 font-semibold">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
              <span>Work Completed & Logged</span>
            </div>
          )}
        </div>
      </div>

      {/* Resolution Note if available */}
      {report.resolutionNote && (
        <Card className="border-emerald-200 bg-emerald-50/50 shadow-sm">
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-emerald-900 flex items-center gap-2">
              <FileCheck className="h-4 w-4 text-emerald-600" />
              <span>Logged Resolution Notes</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-emerald-950 font-medium leading-relaxed">
              {report.resolutionNote}
            </p>
            {report.resolutionEvidenceUrl && (
              <a
                href={report.resolutionEvidenceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 inline-block text-xs font-semibold text-emerald-700 underline"
              >
                View Attached Completion Evidence &rarr;
              </a>
            )}
          </CardContent>
        </Card>
      )}

      {/* Grid: Timeline & Location */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="border-slate-200/90 shadow-sm">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Clock className="h-4 w-4 text-teal-600" />
              <span>Lifecycle Timeline</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <StatusTimeline report={report} />
          </CardContent>
        </Card>

        <Card className="border-slate-200/90 shadow-sm">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <MapPin className="h-4 w-4 text-teal-600" />
              <span>Field Location</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <p className="text-slate-400 font-medium">Designated Site</p>
              <p className="font-semibold text-slate-800 text-sm mt-0.5">
                {report.address || 'GPS Coordinate Pin'}
              </p>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <p className="text-slate-400 font-medium">GPS Coordinates</p>
              <p className="font-mono text-slate-700 mt-0.5">
                {formatCoordinates(report.latitude, report.longitude)}
              </p>
            </div>

            <a
              href={`https://www.google.com/maps/dir/?api=1&destination=${report.latitude},${report.longitude}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center w-full py-2.5 px-4 rounded-xl bg-slate-900 text-white font-medium hover:bg-slate-800 transition-colors gap-2"
            >
              <Navigation className="h-4 w-4 text-teal-400" />
              <span>Launch Turn-by-Turn GPS Navigation</span>
            </a>
          </CardContent>
        </Card>
      </div>

      {/* Photo Gallery */}
      <Card className="border-slate-200/90 shadow-sm">
        <CardHeader>
          <CardTitle className="text-base">Citizen Problem Photos</CardTitle>
        </CardHeader>
        <CardContent>
          <PhotoGallery photos={report.photos} />
        </CardContent>
      </Card>

      {/* Modal: Complete Work Resolution */}
      <Modal
        isOpen={isResolveModalOpen}
        onClose={() => setIsResolveModalOpen(false)}
        title="Complete Work Order"
        description="Describe remediation actions performed and optionally provide an evidence URL."
      >
        <div className="space-y-4 text-sm">
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Resolution Summary & Notes <span className="text-rose-500">*</span>
            </label>
            <textarea
              rows={4}
              value={resolutionNote}
              onChange={(e) => {
                setResolutionNote(e.target.value);
                setNoteError(null);
              }}
              placeholder="e.g. Cleared clogged catch basin with vacuum truck, asphalt patch leveled and compacted with roller..."
              className="w-full rounded-lg border border-slate-300 p-2.5 text-xs focus:ring-1 focus:ring-teal-500"
            />
            {noteError && <p className="text-xs text-rose-600 mt-1 font-medium">{noteError}</p>}
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Evidence Photo URL (Optional)
            </label>
            <input
              type="url"
              value={evidenceUrl}
              onChange={(e) => setEvidenceUrl(e.target.value)}
              placeholder="https://..."
              className="w-full rounded-lg border border-slate-300 p-2 text-xs focus:ring-1 focus:ring-teal-500"
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
            <Button variant="outline" onClick={() => setIsResolveModalOpen(false)}>
              Cancel
            </Button>
            <Button
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
              onClick={() => completeWorkMutation.mutate()}
              isLoading={completeWorkMutation.isPending}
            >
              Confirm Completion
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
