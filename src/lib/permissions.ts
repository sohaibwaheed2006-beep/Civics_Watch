import { User, Role } from '@/types/auth';
import { Report, ReportStatus } from '@/types/report';

export function hasRole(user: User | null, roles: Role | Role[]): boolean {
  if (!user) return false;
  const roleList = Array.isArray(roles) ? roles : [roles];
  return roleList.includes(user.role);
}

export function canCreateReport(user: User | null): boolean {
  return hasRole(user, ['citizen', 'admin']);
}

export function canEditReport(user: User | null, report: Report): boolean {
  if (!user) return false;
  if (user.role === 'admin') return true;
  if (user.role === 'citizen') {
    return user.id === report.citizenId && report.status === 'submitted';
  }
  return false;
}

export function canWithdrawReport(user: User | null, report: Report): boolean {
  if (!user) return false;
  if (user.role === 'admin') return true;
  if (user.role === 'citizen') {
    return (
      user.id === report.citizenId &&
      (report.status === 'submitted' || report.status === 'under_review')
    );
  }
  return false;
}

export function canUpvoteReport(user: User | null): boolean {
  return Boolean(user && user.role === 'citizen');
}

export function canAssignReport(user: User | null): boolean {
  return hasRole(user, 'admin');
}

export function canManageDepartments(user: User | null): boolean {
  return hasRole(user, 'admin');
}

export function canManageUsers(user: User | null): boolean {
  return hasRole(user, 'admin');
}

export function canViewAnalytics(user: User | null): boolean {
  return hasRole(user, 'admin');
}

export function canUpdateWorkStatus(user: User | null, report: Report): boolean {
  if (!user) return false;
  if (user.role === 'admin') return true;
  if (user.role === 'worker') {
    return user.id === report.assignedWorkerId;
  }
  return false;
}

export function getPermittedStatusTransitions(
  user: User | null,
  currentStatus: ReportStatus
): ReportStatus[] {
  if (!user) return [];

  if (user.role === 'admin') {
    switch (currentStatus) {
      case 'submitted':
        return ['under_review', 'assigned', 'rejected'];
      case 'under_review':
        return ['assigned', 'in_progress', 'rejected'];
      case 'assigned':
        return ['in_progress', 'under_review', 'rejected'];
      case 'in_progress':
        return ['resolved', 'assigned', 'rejected'];
      case 'resolved':
        return ['reopened'];
      case 'rejected':
        return ['under_review', 'reopened'];
      case 'reopened':
        return ['under_review', 'assigned', 'in_progress'];
      default:
        return [];
    }
  }

  if (user.role === 'worker') {
    switch (currentStatus) {
      case 'assigned':
        return ['in_progress'];
      case 'in_progress':
        return ['resolved'];
      default:
        return [];
    }
  }

  return [];
}
