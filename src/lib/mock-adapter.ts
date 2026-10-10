import {
  INITIAL_ANALYTICS,
  INITIAL_DEPARTMENTS,
  INITIAL_NOTIFICATIONS,
  INITIAL_REPORTS,
  INITIAL_USERS,
} from './mock-data';
import { User, LoginCredentials, RegisterData, AuthResponse } from '@/types/auth';
import {
  Report,
  CreateReportPayload,
  ReportFilterParams,
  UpdateReportStatusPayload,
  AssignReportPayload,
} from '@/types/report';
import {
  Department,
  CreateDepartmentPayload,
  UpdateDepartmentPayload,
} from '@/types/department';
import {
  UserListItem,
  UserFilterParams,
  CreateWorkerPayload,
  UpdateUserPayload,
} from '@/types/user';
import { Assignment, AssignmentFilterParams } from '@/types/assignment';
import { Notification } from '@/types/notification';
import { AnalyticsSummary } from '@/types/analytics';
import { PaginatedResponse } from '@/types/api';

const STORAGE_KEYS = {
  REPORTS: 'nir_mock_reports',
  DEPARTMENTS: 'nir_mock_departments',
  USERS: 'nir_mock_users',
  NOTIFICATIONS: 'nir_mock_notifications',
};

function getStorageItem<T>(key: string, defaultValue: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) {
      localStorage.setItem(key, JSON.stringify(defaultValue));
      return defaultValue;
    }
    return JSON.parse(raw);
  } catch {
    return defaultValue;
  }
}

function setStorageItem<T>(key: string, val: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(val));
  } catch (e) {
    console.error('Storage error', e);
  }
}

export class MockBackendAdapter {
  private static getReports(): Report[] {
    return getStorageItem<Report[]>(STORAGE_KEYS.REPORTS, INITIAL_REPORTS);
  }

  private static setReports(reports: Report[]): void {
    setStorageItem(STORAGE_KEYS.REPORTS, reports);
  }

  private static getDepartments(): Department[] {
    return getStorageItem<Department[]>(STORAGE_KEYS.DEPARTMENTS, INITIAL_DEPARTMENTS);
  }

  private static setDepartments(depts: Department[]): void {
    setStorageItem(STORAGE_KEYS.DEPARTMENTS, depts);
  }

  private static getUsers(): User[] {
    return getStorageItem<User[]>(STORAGE_KEYS.USERS, INITIAL_USERS);
  }

  private static setUsers(users: User[]): void {
    setStorageItem(STORAGE_KEYS.USERS, users);
  }

  private static getNotifications(): Notification[] {
    return getStorageItem<Notification[]>(STORAGE_KEYS.NOTIFICATIONS, INITIAL_NOTIFICATIONS);
  }

  private static setNotifications(notifs: Notification[]): void {
    setStorageItem(STORAGE_KEYS.NOTIFICATIONS, notifs);
  }

  // Auth
  static async login(creds: LoginCredentials): Promise<AuthResponse> {
    await new Promise((r) => setTimeout(r, 300));
    const users = this.getUsers();
    let found = users.find((u) => u.email.toLowerCase() === creds.email.toLowerCase());

    // Fallback: If matching password123 or demo accounts
    if (!found) {
      if (creds.email.includes('admin')) {
        found = users.find((u) => u.role === 'admin') || users[1];
      } else if (creds.email.includes('worker')) {
        found = users.find((u) => u.role === 'worker') || users[2];
      } else {
        found = users.find((u) => u.role === 'citizen') || users[0];
      }
    }

    if (!found || !found.isActive) {
      throw new Error('Invalid email or password.');
    }

    const token = `mock-bearer-token-${found.id}-${Date.now()}`;
    return {
      accessToken: token,
      tokenType: 'bearer',
      user: found,
    };
  }

  static async register(data: RegisterData): Promise<AuthResponse> {
    await new Promise((r) => setTimeout(r, 400));
    const users = this.getUsers();
    if (users.some((u) => u.email.toLowerCase() === data.email.toLowerCase())) {
      throw new Error('A user with this email address already exists.');
    }

    const newUser: User = {
      id: `user-citizen-${Date.now()}`,
      email: data.email,
      fullName: data.fullName,
      role: 'citizen', // Citizen strictly enforced
      phone: data.phone,
      isActive: true,
      createdAt: new Date().toISOString(),
    };

    users.push(newUser);
    this.setUsers(users);

    const token = `mock-bearer-token-${newUser.id}-${Date.now()}`;
    return {
      accessToken: token,
      tokenType: 'bearer',
      user: newUser,
    };
  }

  static async getCurrentUser(userId?: string): Promise<User> {
    const users = this.getUsers();
    if (userId) {
      const user = users.find((u) => u.id === userId);
      if (user) return user;
    }
    return users[0];
  }

  // Reports
  static async getReportsList(params: ReportFilterParams = {}): Promise<PaginatedResponse<Report>> {
    await new Promise((r) => setTimeout(r, 200));
    let reports = this.getReports();

    if (params.search) {
      const query = params.search.toLowerCase();
      reports = reports.filter(
        (r) =>
          r.title.toLowerCase().includes(query) ||
          r.description.toLowerCase().includes(query) ||
          r.id.toLowerCase().includes(query) ||
          r.address?.toLowerCase().includes(query)
      );
    }

    if (params.status && params.status !== 'all') {
      reports = reports.filter((r) => r.status === params.status);
    }

    if (params.category && params.category !== 'all') {
      reports = reports.filter((r) => r.category === params.category);
    }

    if (params.priority && params.priority !== 'all') {
      reports = reports.filter((r) => r.priority === params.priority);
    }

    if (params.departmentId && params.departmentId !== 'all') {
      reports = reports.filter((r) => r.departmentId === params.departmentId);
    }

    if (params.citizenId) {
      reports = reports.filter((r) => r.citizenId === params.citizenId);
    }

    if (params.assignedWorkerId) {
      reports = reports.filter((r) => r.assignedWorkerId === params.assignedWorkerId);
    }

    // Sort
    reports.sort((a, b) => {
      const order = params.sortOrder === 'asc' ? 1 : -1;
      return (new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()) * (order === 1 ? -1 : 1);
    });

    const page = params.page || 1;
    const limit = params.limit || 10;
    const total = reports.length;
    const totalPages = Math.ceil(total / limit) || 1;
    const startIndex = (page - 1) * limit;
    const data = reports.slice(startIndex, startIndex + limit);

    return {
      data,
      total,
      page,
      limit,
      totalPages,
    };
  }

  static async getReportById(id: string): Promise<Report> {
    await new Promise((r) => setTimeout(r, 150));
    const reports = this.getReports();
    const found = reports.find((r) => r.id === id);
    if (!found) {
      throw new Error(`Report #${id} not found.`);
    }
    return found;
  }

  static async createReport(
    payload: CreateReportPayload,
    currentUser: User
  ): Promise<Report> {
    await new Promise((r) => setTimeout(r, 450));
    const reports = this.getReports();

    const newId = `rep-${Math.floor(100 + Math.random() * 900)}`;
    const now = new Date().toISOString();

    const created: Report = {
      id: newId,
      title: payload.title,
      description: payload.description,
      category: payload.category,
      status: 'submitted',
      priority: 'medium',
      latitude: payload.latitude,
      longitude: payload.longitude,
      address: payload.address || `${payload.latitude.toFixed(4)}, ${payload.longitude.toFixed(4)}`,
      photos: payload.photos
        ? payload.photos.map((file, idx) => ({
            id: `photo-${Date.now()}-${idx}`,
            url: URL.createObjectURL(file),
            filename: file.name,
            fileType: file.type,
            size: file.size,
            uploadedAt: now,
          }))
        : [],
      citizenId: currentUser.id,
      citizenName: currentUser.fullName,
      citizenEmail: currentUser.email,
      upvotesCount: 1,
      hasUpvoted: true,
      createdAt: now,
      updatedAt: now,
    };

    reports.unshift(created);
    this.setReports(reports);

    // Add notification to admin
    const notifs = this.getNotifications();
    notifs.unshift({
      id: `notif-${Date.now()}`,
      userId: 'user-admin-1',
      title: 'New Citizen Report Submitted',
      message: `"${created.title}" in category ${created.category} was submitted by ${currentUser.fullName}.`,
      type: 'status_change',
      reportId: created.id,
      isRead: false,
      createdAt: now,
    });
    this.setNotifications(notifs);

    return created;
  }

  static async updateReportStatus(
    id: string,
    payload: UpdateReportStatusPayload,
    currentUser: User
  ): Promise<Report> {
    await new Promise((r) => setTimeout(r, 300));
    const reports = this.getReports();
    const idx = reports.findIndex((r) => r.id === id);
    if (idx === -1) throw new Error('Report not found');

    const rep = reports[idx];
    rep.status = payload.status;
    rep.updatedAt = new Date().toISOString();
    if (payload.note) {
      rep.resolutionNote = payload.note;
    }
    if (payload.resolutionEvidenceUrl) {
      rep.resolutionEvidenceUrl = payload.resolutionEvidenceUrl;
    }

    reports[idx] = rep;
    this.setReports(reports);

    // Notify citizen
    const notifs = this.getNotifications();
    notifs.unshift({
      id: `notif-${Date.now()}`,
      userId: rep.citizenId,
      title: `Status Changed to ${payload.status.replace(/_/g, ' ')}`,
      message: `Report "${rep.title}" status updated by ${currentUser.fullName}.`,
      type: payload.status === 'resolved' ? 'resolution' : 'status_change',
      reportId: rep.id,
      isRead: false,
      createdAt: new Date().toISOString(),
    });
    this.setNotifications(notifs);

    return rep;
  }

  static async assignReport(
    id: string,
    payload: AssignReportPayload,
    adminUser: User
  ): Promise<Report> {
    await new Promise((r) => setTimeout(r, 350));
    const reports = this.getReports();
    const idx = reports.findIndex((r) => r.id === id);
    if (idx === -1) throw new Error('Report not found');

    const users = this.getUsers();
    const worker = users.find((u) => u.id === payload.workerId);
    if (!worker) throw new Error('Worker not found');

    const depts = this.getDepartments();
    const dept = depts.find((d) => d.id === (payload.departmentId || worker.departmentId));

    const rep = reports[idx];
    rep.assignedWorkerId = worker.id;
    rep.assignedWorkerName = worker.fullName;
    rep.departmentId = dept ? dept.id : worker.departmentId;
    rep.departmentName = dept ? dept.name : worker.departmentName;
    if (payload.priority) rep.priority = payload.priority;
    if (payload.deadline) rep.deadline = payload.deadline;
    rep.status = 'assigned';
    rep.updatedAt = new Date().toISOString();

    reports[idx] = rep;
    this.setReports(reports);

    // Notify worker
    const notifs = this.getNotifications();
    notifs.unshift({
      id: `notif-${Date.now()}`,
      userId: worker.id,
      title: 'New Work Assignment',
      message: `You were assigned report "${rep.title}" by ${adminUser.fullName}.`,
      type: 'assignment',
      reportId: rep.id,
      isRead: false,
      createdAt: new Date().toISOString(),
    });
    this.setNotifications(notifs);

    return rep;
  }

  static async toggleUpvote(id: string, _user: User): Promise<{ upvotesCount: number; hasUpvoted: boolean }> {
    const reports = this.getReports();
    const rep = reports.find((r) => r.id === id);
    if (!rep) throw new Error('Report not found');

    rep.hasUpvoted = !rep.hasUpvoted;
    rep.upvotesCount = (rep.upvotesCount || 0) + (rep.hasUpvoted ? 1 : -1);
    this.setReports(reports);

    return { upvotesCount: rep.upvotesCount, hasUpvoted: rep.hasUpvoted };
  }

  static async deleteReport(id: string, currentUser: User): Promise<void> {
    const reports = this.getReports();
    const rep = reports.find((r) => r.id === id);
    if (!rep) throw new Error('Report not found');
    if (currentUser.role === 'citizen' && rep.citizenId !== currentUser.id) {
      throw new Error('Not authorized to delete this report.');
    }
    const filtered = reports.filter((r) => r.id !== id);
    this.setReports(filtered);
  }

  // Departments
  static async getDepartmentsList(): Promise<Department[]> {
    await new Promise((r) => setTimeout(r, 150));
    return this.getDepartments();
  }

  static async createDepartment(payload: CreateDepartmentPayload): Promise<Department> {
    await new Promise((r) => setTimeout(r, 300));
    const depts = this.getDepartments();
    if (depts.some((d) => d.name.toLowerCase() === payload.name.toLowerCase())) {
      throw new Error('A department with this name already exists.');
    }

    const created: Department = {
      id: `dept-${Date.now()}`,
      name: payload.name,
      description: payload.description,
      defaultSlaHours: payload.defaultSlaHours,
      isActive: true,
      workerCount: 0,
      activeReportsCount: 0,
      createdAt: new Date().toISOString(),
    };

    depts.push(created);
    this.setDepartments(depts);
    return created;
  }

  static async updateDepartment(id: string, payload: UpdateDepartmentPayload): Promise<Department> {
    await new Promise((r) => setTimeout(r, 250));
    const depts = this.getDepartments();
    const idx = depts.findIndex((d) => d.id === id);
    if (idx === -1) throw new Error('Department not found');

    depts[idx] = {
      ...depts[idx],
      ...payload,
      updatedAt: new Date().toISOString(),
    };
    this.setDepartments(depts);
    return depts[idx];
  }

  // Users
  static async getUsersList(params: UserFilterParams = {}): Promise<PaginatedResponse<UserListItem>> {
    await new Promise((r) => setTimeout(r, 200));
    let users = this.getUsers();

    if (params.search) {
      const q = params.search.toLowerCase();
      users = users.filter(
        (u) => u.fullName.toLowerCase().includes(q) || u.email.toLowerCase().includes(q)
      );
    }

    if (params.role && params.role !== 'all') {
      users = users.filter((u) => u.role === params.role);
    }

    if (params.departmentId && params.departmentId !== 'all') {
      users = users.filter((u) => u.departmentId === params.departmentId);
    }

    if (params.isActive !== undefined) {
      users = users.filter((u) => u.isActive === params.isActive);
    }

    const page = params.page || 1;
    const limit = params.limit || 10;
    const total = users.length;
    const totalPages = Math.ceil(total / limit) || 1;
    const startIndex = (page - 1) * limit;

    const data: UserListItem[] = users.slice(startIndex, startIndex + limit).map((u) => ({
      id: u.id,
      email: u.email,
      fullName: u.fullName,
      role: u.role,
      phone: u.phone,
      departmentId: u.departmentId,
      departmentName: u.departmentName,
      isActive: u.isActive,
      createdAt: u.createdAt,
    }));

    return {
      data,
      total,
      page,
      limit,
      totalPages,
    };
  }

  static async createWorker(payload: CreateWorkerPayload): Promise<User> {
    await new Promise((r) => setTimeout(r, 350));
    const users = this.getUsers();
    if (users.some((u) => u.email.toLowerCase() === payload.email.toLowerCase())) {
      throw new Error('A user with this email already exists.');
    }

    const depts = this.getDepartments();
    const dept = depts.find((d) => d.id === payload.departmentId);

    const newWorker: User = {
      id: `user-worker-${Date.now()}`,
      email: payload.email,
      fullName: payload.fullName,
      role: 'worker',
      phone: payload.phone,
      departmentId: payload.departmentId,
      departmentName: dept?.name,
      isActive: true,
      createdAt: new Date().toISOString(),
    };

    users.push(newWorker);
    this.setUsers(users);

    // update dept worker count
    if (dept) {
      dept.workerCount = (dept.workerCount || 0) + 1;
      this.setDepartments(depts);
    }

    return newWorker;
  }

  static async updateUser(id: string, payload: UpdateUserPayload): Promise<User> {
    await new Promise((r) => setTimeout(r, 250));
    const users = this.getUsers();
    const idx = users.findIndex((u) => u.id === id);
    if (idx === -1) throw new Error('User not found');

    const existing = users[idx];
    if (existing.role === 'admin' && payload.isActive === false) {
      const activeAdmins = users.filter((u) => u.role === 'admin' && u.isActive);
      if (activeAdmins.length <= 1) {
        throw new Error('Cannot deactivate the sole active system administrator.');
      }
    }

    let deptName = existing.departmentName;
    if (payload.departmentId) {
      const depts = this.getDepartments();
      const d = depts.find((dept) => dept.id === payload.departmentId);
      deptName = d?.name;
    }

    users[idx] = {
      ...existing,
      ...payload,
      departmentName: deptName,
      updatedAt: new Date().toISOString(),
    };

    this.setUsers(users);
    return users[idx];
  }

  // Worker Assignments
  static async getWorkerAssignments(
    workerId: string,
    params: AssignmentFilterParams = {}
  ): Promise<PaginatedResponse<Assignment>> {
    await new Promise((r) => setTimeout(r, 200));
    const reports = this.getReports();
    const workerReports = reports.filter((r) => r.assignedWorkerId === workerId);

    let filtered = workerReports;
    if (params.status && params.status !== 'all') {
      filtered = filtered.filter((r) => r.status === params.status);
    }
    if (params.priority && params.priority !== 'all') {
      filtered = filtered.filter((r) => r.priority === params.priority);
    }

    const assignments: Assignment[] = filtered.map((rep) => ({
      id: `assign-${rep.id}`,
      reportId: rep.id,
      report: rep,
      workerId,
      workerName: rep.assignedWorkerName || 'Field Worker',
      assignedById: 'user-admin-1',
      assignedByName: 'Marcus Vance',
      assignedAt: rep.createdAt,
      deadline: rep.deadline,
      isOverdue: rep.deadline ? new Date(rep.deadline).getTime() < Date.now() : false,
      status: rep.status,
    }));

    const page = params.page || 1;
    const limit = params.limit || 10;
    const total = assignments.length;
    const totalPages = Math.ceil(total / limit) || 1;
    const startIndex = (page - 1) * limit;

    return {
      data: assignments.slice(startIndex, startIndex + limit),
      total,
      page,
      limit,
      totalPages,
    };
  }

  // Notifications
  static async getNotificationsList(userId: string): Promise<Notification[]> {
    await new Promise((r) => setTimeout(r, 150));
    const notifs = this.getNotifications();
    return notifs.filter((n) => n.userId === userId);
  }

  static async markNotificationRead(id: string): Promise<void> {
    const notifs = this.getNotifications();
    const n = notifs.find((item) => item.id === id);
    if (n) {
      n.isRead = true;
      this.setNotifications(notifs);
    }
  }

  static async markAllNotificationsRead(userId: string): Promise<void> {
    const notifs = this.getNotifications();
    notifs.forEach((n) => {
      if (n.userId === userId) n.isRead = true;
    });
    this.setNotifications(notifs);
  }

  // Analytics
  static async getAnalytics(): Promise<AnalyticsSummary> {
    await new Promise((r) => setTimeout(r, 250));
    const reports = this.getReports();

    // Recompute current counts dynamically from live reports state
    const openReports = reports.filter((r) => ['submitted', 'under_review'].includes(r.status)).length;
    const inProgressReports = reports.filter((r) => ['assigned', 'in_progress'].includes(r.status)).length;
    const resolvedReports = reports.filter((r) => r.status === 'resolved').length;

    return {
      ...INITIAL_ANALYTICS,
      totalReports: reports.length,
      openReports,
      inProgressReports,
      resolvedReports,
    };
  }
}
