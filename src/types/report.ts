export type ReportStatus =
  | 'submitted'
  | 'under_review'
  | 'assigned'
  | 'in_progress'
  | 'resolved'
  | 'rejected'
  | 'reopened';

export type ReportPriority = 'low' | 'medium' | 'high' | 'urgent';

export type ReportCategory =
  | 'road_damage'
  | 'streetlight'
  | 'garbage_waste'
  | 'water_leak'
  | 'drainage'
  | 'public_property'
  | 'other';

export interface ReportAttachment {
  id: string;
  url: string;
  filename: string;
  fileType: string;
  size: number;
  uploadedAt: string;
}

export interface StatusHistoryItem {
  id: string;
  fromStatus?: ReportStatus;
  toStatus: ReportStatus;
  changedById: string;
  changedByName: string;
  changedByRole: string;
  note?: string;
  timestamp: string;
}

export interface Report {
  id: string;
  title: string;
  description: string;
  category: ReportCategory;
  status: ReportStatus;
  priority: ReportPriority;
  latitude: number;
  longitude: number;
  address?: string;
  photos: ReportAttachment[];
  citizenId: string;
  citizenName: string;
  citizenEmail: string;
  departmentId?: string;
  departmentName?: string;
  assignedWorkerId?: string;
  assignedWorkerName?: string;
  upvotesCount: number;
  hasUpvoted?: boolean;
  createdAt: string;
  updatedAt: string;
  deadline?: string;
  resolutionNote?: string;
  resolutionEvidenceUrl?: string;
  duplicateCandidateId?: string;
  // AI automation fields (populated by the backend when available)
  aiCategory?: string;
  aiConfidence?: number;
  aiTitleSuggested?: string;
  aiDescriptionSuggested?: string;
  aiPrioritySuggested?: string;
  duplicateScore?: number;
  duplicateOfReportId?: number;
  incidentClusterId?: number;
  resolutionPhotoMatchScore?: number;
  resolutionFlaggedForReview?: boolean;
  resolutionReviewReason?: string;
}

export interface CreateReportPayload {
  title: string;
  description: string;
  category: ReportCategory;
  latitude: number;
  longitude: number;
  address?: string;
  photos?: File[];
}

export interface UpdateReportStatusPayload {
  status: ReportStatus;
  note?: string;
  resolutionEvidenceUrl?: string;
}

export interface AssignReportPayload {
  workerId: string;
  departmentId?: string;
  priority?: ReportPriority;
  deadline?: string;
  note?: string;
}

export interface ReportFilterParams {
  search?: string;
  status?: ReportStatus | 'all';
  category?: ReportCategory | 'all';
  priority?: ReportPriority | 'all';
  departmentId?: string | 'all';
  citizenId?: string;
  assignedWorkerId?: string;
  page?: number;
  limit?: number;
  sortBy?: 'createdAt' | 'priority' | 'status';
  sortOrder?: 'asc' | 'desc';
}
