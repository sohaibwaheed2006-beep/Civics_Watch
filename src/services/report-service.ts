import { apiClient, isMockFallbackEnabled } from '@/lib/api-client';
import {
  Report,
  CreateReportPayload,
  ReportFilterParams,
  UpdateReportStatusPayload,
  AssignReportPayload,
} from '@/types/report';
import { PaginatedResponse } from '@/types/api';
import { MockBackendAdapter } from '@/lib/mock-adapter';
import { User } from '@/types/auth';

// The backend enum uses `garbage`; the frontend uses `garbage_waste`.
// Normalise categories at the HTTP boundary in both directions.
function toBackendCategory(value: string): string {
  return value === 'garbage_waste' ? 'garbage' : value;
}

// Map the backend ReportRead shape onto the frontend Report shape: the backend
// uses `locationText`/`voteCount` and serves photos on a separate endpoint,
// while the UI reads `address`/`upvotesCount`/`photos`. This keeps every
// consumer working without touching dozens of components.
function normalizeReport(raw: any): Report {
  if (!raw || typeof raw !== 'object') return raw;
  const r = { ...raw };
  if (r.category === 'garbage') r.category = 'garbage_waste';
  if (r.address == null && r.locationText != null) r.address = r.locationText;
  if (r.upvotesCount == null) r.upvotesCount = r.voteCount ?? 0;
  // The list endpoint (ReportSummary) returns `deadlineAt`, the UI reads
  // `deadline`; reconcile so overdue badges and countdowns render.
  if (r.deadline == null && r.deadlineAt != null) r.deadline = r.deadlineAt;
  if (!Array.isArray(r.photos)) r.photos = [];
  return r as Report;
}

// Map the frontend's sortBy values to the backend's sortable column names.
function toBackendSortBy(value?: string): string | undefined {
  if (!value) return undefined;
  return value === 'createdAt' ? 'created_at' : value;
}

// Build the query the FastAPI list endpoint actually accepts. The backend
// validates every parameter strictly (unknown enum values, `limit` instead of
// `page_size`, or a `status`/`category`/`priority` of 'all' all answer 422),
// which — with the mock fallback off — would surface as a hard error. We send
// only the parameters that are set and in the backend's vocabulary.
function toReportListQuery(params: ReportFilterParams): Record<string, unknown> {
  const query: Record<string, unknown> = {
    page: params.page ?? 1,
    page_size: params.limit ?? 10,
  };
  if (params.search && params.search.trim()) query.search = params.search.trim();
  if (params.status && params.status !== 'all') query.status = params.status;
  if (params.category && params.category !== 'all') {
    query.category = toBackendCategory(params.category);
  }
  if (params.priority && params.priority !== 'all') query.priority = params.priority;
  if (params.departmentId && params.departmentId !== 'all') {
    query.department_id = params.departmentId;
  }
  if (params.assignedWorkerId) query.assigned_worker_id = params.assignedWorkerId;
  const sortBy = toBackendSortBy(params.sortBy);
  if (sortBy) query.sort_by = sortBy;
  if (params.sortOrder) query.sort_order = params.sortOrder;
  // `citizenId` is intentionally omitted: the backend scopes a citizen's list
  // to their own reports from the bearer token, so the dashboard's own-reports
  // view needs no explicit filter (and the list endpoint rejects unknown ones).
  return query;
}

// Map ReportPhotoRead (camelCased) onto the frontend ReportAttachment shape.
function normalizePhoto(p: any) {
  return {
    id: String(p.id),
    url: p.url,
    filename: p.originalFilename ?? p.filename ?? 'photo',
    fileType: p.contentType ?? p.fileType ?? 'image/jpeg',
    size: p.fileSize ?? p.size ?? 0,
    uploadedAt: p.createdAt ?? p.uploadedAt ?? new Date().toISOString(),
  };
}

export const reportService = {
  // The community map shows the WHOLE neighborhood to every role, so it must
  // NOT use GET /reports (that endpoint scopes citizens to their own reports
  // and workers to their own queue). The dedicated GET /reports/map endpoint
  // is unscoped and purpose-built for this. It returns lean markers; we
  // normalize them into the Report shape the map component already expects.
  async getMapReports(params: { status?: string; category?: string; limit?: number } = {}): Promise<Report[]> {
    try {
      const query: Record<string, unknown> = { limit: params.limit ?? 500 };
      if (params.status && params.status !== 'all') query.status = params.status;
      if (params.category && params.category !== 'all') {
        query.category = toBackendCategory(params.category);
      }
      const response = await apiClient.get('/reports/map', { params: query });
      const list = Array.isArray(response.data) ? response.data : (response.data?.data ?? []);
      return list.map(normalizeReport);
    } catch (error) {
      if (isMockFallbackEnabled()) {
        // Mock has no map endpoint; return every report (unscoped), which is
        // exactly what the community map wants.
        const res = await MockBackendAdapter.getReportsList({ limit: 1000 });
        return res.data;
      }
      throw error;
    }
  },

  async getReports(params: ReportFilterParams = {}): Promise<PaginatedResponse<Report>> {
    try {
      const response = await apiClient.get<PaginatedResponse<Report>>('/reports', {
        params: toReportListQuery(params),
      });
      return {
        ...response.data,
        data: (response.data.data || []).map(normalizeReport),
      };
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.getReportsList(params);
      }
      throw error;
    }
  },

  async getReportById(id: string): Promise<Report> {
    try {
      const response = await apiClient.get<Report>(`/reports/${id}`);
      const report = normalizeReport(response.data);
      // Photos live on a separate endpoint; fetch and attach them so the
      // detail view and gallery render real images. Non-fatal on failure.
      try {
        const photosRes = await apiClient.get(`/reports/${id}/photos`);
        const list = Array.isArray(photosRes.data)
          ? photosRes.data
          : (photosRes.data?.data ?? []);
        report.photos = list.map(normalizePhoto);
      } catch {
        report.photos = report.photos || [];
      }
      return report;
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.getReportById(id);
      }
      throw error;
    }
  },

  async createReport(payload: CreateReportPayload, user: User): Promise<Report> {
    try {
      // The backend creates the report from a JSON body, then accepts photos
      // on a separate multipart endpoint. Field names and the category enum
      // are mapped to the backend's contract here.
      const createBody = {
        title: payload.title,
        description: payload.description,
        category: toBackendCategory(payload.category),
        latitude: payload.latitude,
        longitude: payload.longitude,
        location_text: payload.address || undefined,
      };

      const response = await apiClient.post<Report>('/reports', createBody);
      const created = response.data;

      // Upload each photo to the report's photo endpoint. A photo failure
      // must not lose the report that was already created, so failures are
      // tolerated and surfaced only in the console.
      if (payload.photos && payload.photos.length > 0) {
        for (const file of payload.photos) {
          const form = new FormData();
          form.append('file', file);
          try {
            await apiClient.post(`/reports/${created.id}/photos`, form);
          } catch (photoErr) {
            console.error('Photo upload failed for report', created.id, photoErr);
          }
        }
      }

      return normalizeReport(created);
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.createReport(payload, user);
      }
      throw error;
    }
  },

  async updateReportStatus(
    id: string,
    payload: UpdateReportStatusPayload,
    user: User
  ): Promise<Report> {
    try {
      // The backend route is POST /reports/{id}/status and its schema only
      // accepts { status, note } (extra fields are rejected with 422). The
      // resolution evidence photo is uploaded through the photo endpoint, not
      // here, so we deliberately send just status + note.
      const response = await apiClient.post<Report>(`/reports/${id}/status`, {
        status: payload.status,
        note: payload.note,
      });
      return response.data;
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.updateReportStatus(id, payload, user);
      }
      throw error;
    }
  },

  async assignReport(id: string, payload: AssignReportPayload, user: User): Promise<Report> {
    try {
      // The backend's AssignmentCreate schema is strict (extra="forbid") and
      // names the free-text field `notes`, not `note`. It also derives the
      // department from the worker, so `departmentId` is accepted but ignored.
      // Build the exact body it expects (snake_case conversion happens in the
      // api-client interceptor for the camelCase keys).
      const body: Record<string, unknown> = { workerId: payload.workerId };
      if (payload.note) body.notes = payload.note;
      if (payload.priority) body.priority = payload.priority;
      if (payload.deadline) body.deadline = payload.deadline;
      const response = await apiClient.post<Report>(`/reports/${id}/assign`, body);
      return response.data;
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.assignReport(id, payload, user);
      }
      throw error;
    }
  },

  async toggleUpvote(
    id: string,
    user: User
  ): Promise<{ upvotesCount: number; hasUpvoted: boolean }> {
    try {
      // Backend returns VoteCountRead { reportId, count, voted } after the
      // camelCase transform; map it onto the shape the UI uses.
      const response = await apiClient.post<{ count: number; voted: boolean }>(
        `/reports/${id}/upvote`
      );
      return {
        upvotesCount: response.data.count,
        hasUpvoted: response.data.voted,
      };
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return await MockBackendAdapter.toggleUpvote(id, user);
      }
      throw error;
    }
  },

  async deleteReport(id: string, user: User): Promise<void> {
    try {
      await apiClient.delete(`/reports/${id}`);
    } catch (error) {
      if (isMockFallbackEnabled()) {
        await MockBackendAdapter.deleteReport(id, user);
        return;
      }
      throw error;
    }
  },
};
