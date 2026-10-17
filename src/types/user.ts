import { Role } from './auth';

export interface UserListItem {
  id: string;
  email: string;
  fullName: string;
  role: Role;
  avatarUrl?: string;
  phone?: string;
  departmentId?: string;
  departmentName?: string;
  isActive: boolean;
  createdAt: string;
  assignedTasksCount?: number;
}

export interface CreateWorkerPayload {
  fullName: string;
  email: string;
  password: string;
  phone?: string;
  departmentId: string;
}

export interface UpdateUserPayload {
  fullName?: string;
  phone?: string;
  role?: Role;
  departmentId?: string;
  isActive?: boolean;
}

export interface UserFilterParams {
  search?: string;
  role?: Role | 'all';
  isActive?: boolean;
  departmentId?: string | 'all';
  page?: number;
  limit?: number;
}
