import { ReportCategory, ReportPriority, ReportStatus } from '@/types/report';
import { Role } from '@/types/auth';
import {
  CATEGORY_DETAILS,
  PRIORITY_DETAILS,
  ROLE_DETAILS,
  STATUS_DETAILS,
} from './constants';

export function formatDate(dateString?: string | null): string {
  if (!dateString) return '—';
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return dateString;
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(date);
  } catch {
    return dateString;
  }
}

export function formatDateTime(dateString?: string | null): string {
  if (!dateString) return '—';
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return dateString;
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    }).format(date);
  } catch {
    return dateString;
  }
}

export function formatRelativeTime(dateString?: string | null): string {
  if (!dateString) return '—';
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return dateString;
    const now = new Date();
    const diffSec = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffSec < 60) return 'Just now';
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
    if (diffSec < 604800) return `${Math.floor(diffSec / 86400)}d ago`;
    return formatDate(dateString);
  } catch {
    return dateString;
  }
}

export function formatCategory(category?: ReportCategory | string): string {
  if (!category) return 'Unknown';
  const found = CATEGORY_DETAILS[category as ReportCategory];
  return found ? found.label : category.replace(/_/g, ' ');
}

export function formatStatus(status?: ReportStatus | string): string {
  if (!status) return 'Unknown';
  const found = STATUS_DETAILS[status as ReportStatus];
  return found ? found.label : status.replace(/_/g, ' ');
}

export function formatPriority(priority?: ReportPriority | string): string {
  if (!priority) return 'Unknown';
  const found = PRIORITY_DETAILS[priority as ReportPriority];
  return found ? found.label : priority;
}

export function formatRole(role?: Role | string): string {
  if (!role) return 'Unknown';
  const found = ROLE_DETAILS[role as Role];
  return found ? found.label : role;
}

export function formatCoordinates(lat?: number, lng?: number): string {
  if (lat === undefined || lng === undefined || lat === null || lng === null) {
    return 'No GPS data';
  }
  return `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}
