export interface Department {
  id: string;
  name: string;
  description: string;
  imageUrl?: string;
  defaultSlaHours: number;
  isActive: boolean;
  workerCount: number;
  activeReportsCount?: number;
  createdAt: string;
  updatedAt?: string;
}

export interface CreateDepartmentPayload {
  name: string;
  description: string;
  defaultSlaHours: number;
}

export interface UpdateDepartmentPayload {
  name?: string;
  description?: string;
  defaultSlaHours?: number;
  isActive?: boolean;
}
