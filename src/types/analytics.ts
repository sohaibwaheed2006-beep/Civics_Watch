import { ReportCategory, ReportStatus } from './report';

export interface StatusCount {
  status: ReportStatus;
  label: string;
  count: number;
}

export interface CategoryCount {
  category: ReportCategory;
  label: string;
  count: number;
}

export interface TimeSeriesDataPoint {
  date: string;
  submitted: number;
  resolved: number;
}

export interface DepartmentMetric {
  departmentId: string;
  departmentName: string;
  totalAssigned: number;
  resolvedCount: number;
  avgResolutionHours: number;
  complianceRate: number; // SLA compliance percentage
}

export interface AnalyticsSummary {
  totalReports: number;
  openReports: number;
  inProgressReports: number;
  resolvedReports: number;
  overdueReports: number;
  avgResolutionTimeHours: number;
  byStatus: StatusCount[];
  byCategory: CategoryCount[];
  overTime: TimeSeriesDataPoint[];
  departmentPerformance: DepartmentMetric[];
}
