import { apiClient, isMockFallbackEnabled } from '@/lib/api-client';
import { MockBackendAdapter } from '@/lib/mock-adapter';
import { parseApiError } from '@/lib/api-errors';
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
  issueDetected: boolean;
  retakeReason: string | null;
}

/**
 * Outcome of analysing a citizen photo. The wizard must only advance on
 * `detected`; the other two keep the citizen on the photo step.
 *
 * - `detected`     the AI found a reportable issue; `data` pre-fills the form.
 * - `retake`       the photo is the problem (unreadable, too dark/blurry, or
 *                  not a public issue). Ask for a different photo.
 * - `unavailable`  the AI service is the problem (outage, quota, network).
 *                  The same photo can be retried.
 */
export type PhotoAnalysis =
  | { status: 'detected'; data: VisionAutoFill }
  | { status: 'retake'; reason: string }
  | { status: 'unavailable'; reason: string };

const DEFAULT_RETAKE_REASON =
  "We couldn't spot a clear public issue in this photo. Retake it closer to the problem, in good light, with the issue filling the frame.";

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
  /**
   * Analyze a photo. Never throws: every failure is mapped onto a
   * {@link PhotoAnalysis} status so the caller can decide between "retake the
   * photo" and "try again", instead of silently continuing without AI.
   */
  async analyzePhoto(file: File): Promise<PhotoAnalysis> {
    const form = new FormData();
    form.append('file', file);
    try {
      const response = await apiClient.post<VisionAutoFill>(
        '/ai/vision/analyze',
        form
      );
      const data: VisionAutoFill = {
        ...response.data,
        category: toFrontendCategory(response.data.category as string),
      };
      // `issueDetected` is absent on older backends; only an explicit false
      // (or a spam verdict) blocks the citizen.
      if (data.isSpam || data.issueDetected === false) {
        return {
          status: 'retake',
          reason: data.retakeReason || data.spamReason || DEFAULT_RETAKE_REASON,
        };
      }
      return { status: 'detected', data };
    } catch (error) {
      const parsed = parseApiError(error);
      // 4xx on the photo itself (unreadable image, wrong type, too large,
      // empty file): a different photo is the fix.
      if (
        parsed.code === 'photo_not_recognized' ||
        (parsed.status !== undefined &&
          [400, 409, 413, 415, 422].includes(parsed.status))
      ) {
        return { status: 'retake', reason: parsed.message || DEFAULT_RETAKE_REASON };
      }
      // Network error, 401, 5xx, vision_unavailable: the photo is fine.
      return {
        status: 'unavailable',
        reason: parsed.isNetworkError
          ? 'Could not reach the server to analyze your photo. Check your connection and try again.'
          : parsed.code === 'vision_unavailable'
            ? parsed.message
            : 'Photo analysis is temporarily unavailable. Please try again in a moment.',
      };
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
