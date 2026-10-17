import { apiClient, isMockFallbackEnabled } from '@/lib/api-client';
import {
  AnalyticsSummary,
  StatusCount,
  CategoryCount,
  TimeSeriesDataPoint,
  DepartmentMetric,
} from '@/types/analytics';
import { MockBackendAdapter } from '@/lib/mock-adapter';

const STATUS_LABELS: Record<string, string> = {
  submitted: 'Submitted',
  under_review: 'Under Review',
  assigned: 'Assigned',
  in_progress: 'In Progress',
  resolved: 'Resolved',
  rejected: 'Rejected',
  reopened: 'Reopened',
};

const CATEGORY_LABELS: Record<string, string> = {
  road_damage: 'Road Damage',
  streetlight: 'Streetlight',
  garbage_waste: 'Garbage & Waste',
  water_leak: 'Water Leak',
  drainage: 'Drainage',
  public_property: 'Public Property',
  other: 'Other',
};

// Backend enum uses `garbage`; the frontend uses `garbage_waste`.
function normCategory(c: string): string {
  return c === 'garbage' ? 'garbage_waste' : c;
}

function asArray<T>(v: unknown): T[] {
  if (Array.isArray(v)) return v as T[];
  const data = (v as { data?: unknown })?.data;
  return Array.isArray(data) ? (data as T[]) : [];
}

export const analyticsService = {
  // The backend exposes analytics across several endpoints; the dashboard
  // wants one composed summary object. We fetch them in parallel and map the
  // backend field names to the frontend shape. Every array defaults to [] and
  // every scalar to 0 so a missing/empty response never crashes a chart.
  async getAnalyticsSummary(): Promise<AnalyticsSummary> {
    try {
      const [overviewR, statusR, categoryR, timeR, deptR] = await Promise.all([
        apiClient.get('/analytics/overview'),
        apiClient.get('/analytics/reports-by-status'),
        apiClient.get('/analytics/reports-by-category'),
        apiClient.get('/analytics/reports-over-time'),
        apiClient.get('/analytics/department-performance'),
      ]);

      const overview = (overviewR.data || {}) as Record<string, number>;

      const byStatus: StatusCount[] = asArray<{ status: string; count: number }>(
        statusR.data
      ).map((b) => ({
        status: b.status as StatusCount['status'],
        label: STATUS_LABELS[b.status] || b.status,
        count: b.count,
      }));

      const byCategory: CategoryCount[] = asArray<{ category: string; count: number }>(
        categoryR.data
      ).map((b) => {
        const cat = normCategory(b.category);
        return {
          category: cat as CategoryCount['category'],
          label: CATEGORY_LABELS[cat] || cat,
          count: b.count,
        };
      });

      const overTime: TimeSeriesDataPoint[] = asArray<{
        day?: string;
        date?: string;
        submitted?: number;
        resolved?: number;
        count?: number;
      }>(timeR.data).map((b) => ({
        date: String(b.day ?? b.date ?? ''),
        submitted: Number(b.submitted ?? b.count ?? 0),
        resolved: Number(b.resolved ?? 0),
      }));

      const departmentPerformance: DepartmentMetric[] = asArray<{
        departmentId: number | string;
        departmentName: string;
        totalReports?: number;
        totalAssigned?: number;
        resolvedReports?: number;
        resolvedCount?: number;
        overdueReports?: number;
        averageResolutionHours?: number | null;
        avgResolutionHours?: number | null;
      }>(deptR.data).map((d) => {
        const total = Number(d.totalReports ?? d.totalAssigned ?? 0);
        const resolved = Number(d.resolvedReports ?? d.resolvedCount ?? 0);
        const overdue = Number(d.overdueReports ?? 0);
        return {
          departmentId: String(d.departmentId),
          departmentName: d.departmentName,
          totalAssigned: total,
          resolvedCount: resolved,
          avgResolutionHours: Number(d.averageResolutionHours ?? d.avgResolutionHours ?? 0),
          complianceRate: total > 0 ? Math.round(((total - overdue) / total) * 100) : 100,
        };
      });

      const inProgress = byStatus
        .filter((s) => s.status === 'assigned' || s.status === 'in_progress')
        .reduce((sum, s) => sum + s.count, 0);

      return {
        totalReports: Number(overview.totalReports ?? 0),
        openReports: Number(overview.openReports ?? 0),
        inProgressReports: inProgress,
        resolvedReports: Number(overview.resolvedReports ?? 0),
        overdueReports: Number(overview.overdueReports ?? 0),
        avgResolutionTimeHours: Number(overview.averageResolutionHours ?? 0),
        byStatus,
        byCategory,
        overTime,
        departmentPerformance,
      };
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.getAnalytics();
      }
      throw error;
    }
  },
};
