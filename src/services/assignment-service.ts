import { isMockFallbackEnabled } from '@/lib/api-client';
import { Assignment, AssignmentFilterParams } from '@/types/assignment';
import { PaginatedResponse } from '@/types/api';
import { MockBackendAdapter } from '@/lib/mock-adapter';
import { reportService } from '@/services/report-service';
import { Report } from '@/types/report';

// Shape a report assigned to a worker into the Assignment view-model the
// worker pages consume. The backend has a lean `/assignments/my` endpoint, but
// the UI needs the full report (title, category, location, status, deadline),
// which the reports list already carries. GET /reports is automatically scoped
// to the worker's own queue for a worker token, so this returns exactly their
// dispatched work — with pagination and filtering handled server-side.
function reportToAssignment(rep: Report, workerId: string): Assignment {
  const overdue =
    Boolean(rep.deadline) &&
    new Date(rep.deadline as string).getTime() < Date.now() &&
    rep.status !== 'resolved' &&
    rep.status !== 'rejected';
  return {
    id: `assign-${rep.id}`,
    reportId: rep.id,
    report: rep,
    workerId,
    workerName: rep.assignedWorkerName || 'Field Worker',
    assignedById: '',
    assignedByName: rep.departmentName || 'Dispatch',
    assignedAt: rep.updatedAt || rep.createdAt,
    deadline: rep.deadline,
    isOverdue: overdue,
    status: rep.status,
  };
}

export const assignmentService = {
  async getWorkerAssignments(
    workerId: string,
    params: AssignmentFilterParams = {}
  ): Promise<PaginatedResponse<Assignment>> {
    try {
      const res = await reportService.getReports({
        assignedWorkerId: workerId,
        status: params.status,
        priority: params.priority,
        page: params.page,
        limit: params.limit,
      });
      return {
        ...res,
        data: res.data.map((rep) => reportToAssignment(rep, workerId)),
      };
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.getWorkerAssignments(workerId, params);
      }
      throw error;
    }
  },
};
