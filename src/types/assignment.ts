import { Report } from './report';

export interface Assignment {
  id: string;
  reportId: string;
  report: Report;
  workerId: string;
  workerName: string;
  assignedById: string;
  assignedByName: string;
  assignedAt: string;
  deadline?: string;
  isOverdue: boolean;
  status: Report['status'];
  workNotes?: string[];
}

export interface AssignmentFilterParams {
  status?: Report['status'] | 'all';
  priority?: Report['priority'] | 'all';
  isOverdue?: boolean;
  page?: number;
  limit?: number;
}
