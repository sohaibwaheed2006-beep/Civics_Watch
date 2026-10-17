import { apiClient, isMockFallbackEnabled } from '@/lib/api-client';
import { MockBackendAdapter } from '@/lib/mock-adapter';
import { ReportCategory, ReportPriority } from '@/types/report';

export interface VisionAutoFill {
  category: ReportCategory;
  priority: ReportPriority;
  title: string;
  description: string;
  locationHint: string | null;
  confidence: number;
  source: string;
  spamScore: number;
  isSpam: boolean;
  spamReason: string | null;
}

// The backend enum uses `garbage`; the frontend form/type uses
// `garbage_waste`. Normalise in both directions at this boundary.
function toFrontendCategory(value: string): ReportCategory {
  return (value === 'garbage' ? 'garbage_waste' : value) as ReportCategory;
}

export interface ResolutionCheck {
  matchScore: number;
  looksFixed: boolean;
  reason: string;
  flaggedForReview: boolean;
}

export interface AutoRouteSuggestion {
  departmentId: number | null;
  departmentName: string | null;
  suggestedWorker: {
    workerId: number;
    workerName: string;
    departmentId: number | null;
    openAssignments: number;
    recentOnTimeRate: number;
    score: number;
  } | null;
}

export const aiService = {
  /** Analyze a photo and return pre-filled category / title / description. */
  async analyzePhoto(file: File): Promise<VisionAutoFill | null> {
    const form = new FormData();
    form.append('file', file);
    try {
      const response = await apiClient.post<VisionAutoFill>(
        '/ai/vision/analyze',
        form
      );
      return {
        ...response.data,
        category: toFrontendCategory(response.data.category as string),
      };
    } catch {
      // Vision is explicitly optional - fall through to manual fill.
      return null;
    }
  },

  /** Admin: ask the AI to suggest a department + worker for triage. */
  async autoRoute(reportId: number | string): Promise<AutoRouteSuggestion> {
    try {
      const response = await apiClient.get<AutoRouteSuggestion>(
        `/ai/reports/${reportId}/auto-route`
      );
      return response.data;
    } catch (error) {
      if (isMockFallbackEnabled()) {
        return (await MockBackendAdapter.getAutoRoute(String(reportId))) as AutoRouteSuggestion;
      }
      throw error;
    }
  },

  /** Admin: verify a resolution photo against the complaint. */
  async verifyResolution(
    reportId: number,
    file: File
  ): Promise<ResolutionCheck> {
    const form = new FormData();
    form.append('file', file);
    const response = await apiClient.post<ResolutionCheck>(
      `/ai/vision/verify-resolution/${reportId}`,
      form
    );
    return response.data;
  },

  /** Fetch the other reports in this report's incident cluster. */
  async cluster(reportId: number) {
    const response = await apiClient.get(`/ai/reports/${reportId}/cluster`);
    return response.data;
  },
};
