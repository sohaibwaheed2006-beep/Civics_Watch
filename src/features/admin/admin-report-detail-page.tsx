import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '@/hooks/use-auth';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { reportService } from '@/services/report-service';
import { departmentService } from '@/services/department-service';
import { userService } from '@/services/user-service';
import { useToast } from '@/hooks/use-toast';
import { getPermittedStatusTransitions } from '@/lib/permissions';
import { formatCategory, formatCoordinates, formatDateTime } from '@/lib/formatters';
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
import { ReportPriority, ReportStatus } from '@/types/report';
import {
  MapPin,
  UserCheck,
  User,
  Clock,
  Calendar,
} from 'lucide-react';

export const AdminReportDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Modals
  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false);
  const [isStatusModalOpen, setIsStatusModalOpen] = useState(false);
  const [selectedNewStatus, setSelectedNewStatus] = useState<ReportStatus | null>(null);
  const [statusNote, setStatusNote] = useState('');

  // Assignment modal fields
  const [selectedDeptId, setSelectedDeptId] = useState('');
  const [selectedWorkerId, setSelectedWorkerId] = useState('');
  const [selectedPriority, setSelectedPriority] = useState<ReportPriority>('medium');
  const [deadlineDate, setDeadlineDate] = useState('');

  // Fetch report
  const {
    data: report,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['admin-report-detail', id],
    queryFn: () => (id ? reportService.getReportById(id) : Promise.reject('No ID')),
    enabled: Boolean(id),
  });

  // Fetch departments
  const { data: departments = [] } = useQuery({
    queryKey: ['departments-list'],
    queryFn: () => departmentService.getDepartments(),
  });

  // Fetch workers
  const { data: usersData } = useQuery({
    queryKey: ['workers-list', selectedDeptId],
    queryFn: () =>
      userService.getUsers({
        role: 'worker',
        departmentId: selectedDeptId && selectedDeptId !== 'all' ? selectedDeptId : undefined,
        isActive: true,
        limit: 50,
      }),
  });

  const availableWorkers = usersData?.data || [];

  // Mutations
  const updateStatusMutation = useMutation({
    mutationFn: (newStatus: ReportStatus) =>
      report && user
        ? reportService.updateReportStatus(report.id, { status: newStatus, note: statusNote }, user)
        : Promise.reject(),
    onSuccess: (updated) => {
      toast.success(`Report status changed to "${updated.status.replace(/_/g, ' ')}".`);
      queryClient.invalidateQueries({ queryKey: ['admin-report-detail', id] });
      queryClient.invalidateQueries({ queryKey: ['admin-reports-list'] });
      setIsStatusModalOpen(false);
      setStatusNote('');
    },
    onError: () => toast.error('Failed to change status.'),
  });

  const assignMutation = useMutation({
    mutationFn: () =>
      report && user
        ? reportService.assignReport(
            report.id,
            {
              workerId: selectedWorkerId,
              departmentId: selectedDeptId,
              priority: selectedPriority,
              deadline: deadlineDate || undefined,
            },
            user
          )
        : Promise.reject(),
    onSuccess: () => {
      toast.success('Worker assigned and dispatch notification sent.');
      queryClient.invalidateQueries({ queryKey: ['admin-report-detail', id] });
      queryClient.invalidateQueries({ queryKey: ['admin-reports-list'] });
      setIsAssignModalOpen(false);
    },
    onError: () => toast.error('Failed to assign worker.'),
  });

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-5xl mx-auto">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-44 w-full rounded-xl" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    );
  }

  if (isError || !report) {
    return (
      <div className="max-w-2xl mx-auto my-12">
        <ErrorPanel
          title="Report Not Found"
          message="Could not load the requested report from the municipal database."
          onRetry={refetch}
        />
        <div className="mt-4 text-center">
          <Link to="/admin/reports">
            <Button variant="outline">Back to Reports</Button>
          </Link>
        </div>
      </div>
    );
  }

  const permittedTransitions = getPermittedStatusTransitions(user, report.status);

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      <Breadcrumbs
        items={[
          { label: 'Admin Portal', href: '/admin/dashboard' },
          { label: 'Report Management', href: '/admin/reports' },
          { label: `Report #${report.id}` },
        ]}
      />

      {/* Main Governance Header Card */}
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

          {/* Action buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSelectedDeptId(report.departmentId || departments[0]?.id || '');
                setSelectedPriority(report.priority);
                setIsAssignModalOpen(true);
              }}
              leftIcon={<UserCheck className="h-4 w-4 text-teal-600" />}
            >
              {report.assignedWorkerId ? 'Reassign Worker' : 'Assign Worker'}
            </Button>

            {permittedTransitions.length > 0 && (
              <div className="flex items-center gap-1.5">
                {permittedTransitions.map((nextStatus) => (
                  <Button
                    key={nextStatus}
                    size="sm"
                    variant={nextStatus === 'rejected' ? 'danger' : 'primary'}
                    onClick={() => {
                      setSelectedNewStatus(nextStatus);
                      setIsStatusModalOpen(true);
                    }}
                  >
                    Mark {nextStatus.replace(/_/g, ' ')}
                  </Button>
                ))}
              </div>
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

        {/* Reporter info badge */}
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 pt-2 border-t border-slate-100 text-xs text-slate-500">
          <div className="flex items-center gap-1.5">
            <User className="h-3.5 w-3.5 text-slate-400" />
            <span>Citizen: </span>
            <span className="font-semibold text-slate-800">{report.citizenName}</span>
            <span className="text-slate-400">({report.citizenEmail})</span>
          </div>

          <div className="flex items-center gap-1.5">
            <Calendar className="h-3.5 w-3.5 text-slate-400" />
            <span>Submitted: {formatDateTime(report.createdAt)}</span>
          </div>
        </div>
      </div>

      {/* Grid: Details & Governance metadata */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left col: Status Timeline & Evidence (2 cols) */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="border-slate-200/90 shadow-sm">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Clock className="h-4 w-4 text-teal-600" />
                <span>Status & Governance Progression</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <StatusTimeline report={report} />
            </CardContent>
          </Card>

          {/* Photo Gallery */}
          <Card className="border-slate-200/90 shadow-sm">
            <CardHeader>
              <CardTitle className="text-base">Photo Evidence</CardTitle>
            </CardHeader>
            <CardContent>
              <PhotoGallery photos={report.photos} />
            </CardContent>
          </Card>
        </div>

        {/* Right col: Assignment, Department & Location (1 col) */}
        <div className="space-y-6">
          {/* Assignment Box */}
          <Card className="border-slate-200/90 shadow-sm">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <UserCheck className="h-4 w-4 text-teal-600" />
                <span>Assignment & SLA</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div>
                <p className="text-slate-400 font-medium">Department</p>
                <p className="font-semibold text-slate-800 text-sm mt-0.5">
                  {report.departmentName || 'Not Assigned'}
                </p>
              </div>

              <div>
                <p className="text-slate-400 font-medium">Assigned Worker</p>
                <p className="font-semibold text-slate-800 text-sm mt-0.5">
                  {report.assignedWorkerName || 'Pending Dispatch'}
                </p>
              </div>

              <div>
                <p className="text-slate-400 font-medium">Target Deadline</p>
                <p className="font-semibold text-amber-700 mt-0.5">
                  {report.deadline ? formatDateTime(report.deadline) : 'Standard SLA'}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Location Box */}
          <Card className="border-slate-200/90 shadow-sm">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <MapPin className="h-4 w-4 text-teal-600" />
                <span>Location</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div>
                <p className="text-slate-400 font-medium">Address</p>
                <p className="font-semibold text-slate-800 mt-0.5">
                  {report.address || 'GPS Coordinate Pin'}
                </p>
              </div>

              <div>
                <p className="text-slate-400 font-medium">GPS Coordinates</p>
                <p className="font-mono text-slate-700 mt-0.5">
                  {formatCoordinates(report.latitude, report.longitude)}
                </p>
              </div>

              <div className="pt-2">
                <a
                  href={`https://www.google.com/maps/search/?api=1&query=${report.latitude},${report.longitude}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-teal-600 hover:text-teal-800 font-medium inline-block"
                >
                  View on Google Maps &rarr;
                </a>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Modal: Assign Worker */}
      <Modal
        isOpen={isAssignModalOpen}
        onClose={() => setIsAssignModalOpen(false)}
        title="Dispatch / Reassign Field Worker"
        description="Select the appropriate municipal department and certified technician."
      >
        <div className="space-y-4 text-sm">
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Responsible Department
            </label>
            <select
              value={selectedDeptId}
              onChange={(e) => setSelectedDeptId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white p-2 text-xs focus:ring-1 focus:ring-teal-500"
            >
              {departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.defaultSlaHours}h SLA)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Field Worker
            </label>
            <select
              value={selectedWorkerId}
              onChange={(e) => setSelectedWorkerId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white p-2 text-xs focus:ring-1 focus:ring-teal-500"
            >
              <option value="">Select a worker...</option>
              {availableWorkers.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.fullName} ({w.email})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Priority Override
              </label>
              <select
                value={selectedPriority}
                onChange={(e) => setSelectedPriority(e.target.value as any)}
                className="w-full rounded-lg border border-slate-300 bg-white p-2 text-xs focus:ring-1 focus:ring-teal-500"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Target Deadline
              </label>
              <input
                type="datetime-local"
                value={deadlineDate}
                onChange={(e) => setDeadlineDate(e.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white p-2 text-xs focus:ring-1 focus:ring-teal-500"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-slate-100">
            <Button variant="outline" onClick={() => setIsAssignModalOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => assignMutation.mutate()}
              isLoading={assignMutation.isPending}
              disabled={!selectedWorkerId}
            >
              Confirm Assignment
            </Button>
          </div>
        </div>
      </Modal>

      {/* Modal: Status Transition with Administrative Note */}
      <Modal
        isOpen={isStatusModalOpen}
        onClose={() => setIsStatusModalOpen(false)}
        title={`Change Status to "${selectedNewStatus?.replace(/_/g, ' ')}"?`}
        description="This will transition the lifecycle state and notify the citizen reporter."
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Administrative Note (Optional)
            </label>
            <textarea
              rows={3}
              value={statusNote}
              onChange={(e) => setStatusNote(e.target.value)}
              placeholder="Explain rationale, triage decision, or instructions..."
              className="w-full rounded-lg border border-slate-300 p-2.5 text-xs focus:ring-1 focus:ring-teal-500"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => setIsStatusModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant={selectedNewStatus === 'rejected' ? 'danger' : 'primary'}
              onClick={() => selectedNewStatus && updateStatusMutation.mutate(selectedNewStatus)}
              isLoading={updateStatusMutation.isPending}
            >
              Update Status
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
