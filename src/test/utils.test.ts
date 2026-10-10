import { describe, it, expect } from 'vitest';
import {
  formatDate,
  formatCategory,
  formatStatus,
  formatPriority,
  formatCoordinates,
  formatFileSize,
} from '@/lib/formatters';
import {
  canCreateReport,
  canEditReport,
  canWithdrawReport,
  getPermittedStatusTransitions,
} from '@/lib/permissions';
import { parseApiError } from '@/lib/api-errors';
import { User } from '@/types/auth';
import { Report } from '@/types/report';

describe('Formatting Utilities', () => {
  it('formats dates accurately', () => {
    expect(formatDate(null)).toBe('—');
    expect(formatDate('2026-10-10T08:00:00Z')).toContain('2026');
  });

  it('formats report categories and statuses', () => {
    expect(formatCategory('road_damage')).toBe('Road Damage / Pothole');
    expect(formatCategory('streetlight')).toBe('Streetlight Outage');
    expect(formatStatus('in_progress')).toBe('In Progress');
    expect(formatPriority('urgent')).toBe('Urgent');
  });

  it('formats coordinates and file sizes', () => {
    expect(formatCoordinates(40.7128, -74.006)).toBe('40.71280, -74.00600');
    expect(formatCoordinates(undefined, undefined)).toBe('No GPS data');
    expect(formatFileSize(1024)).toBe('1 KB');
    expect(formatFileSize(1048576)).toBe('1 MB');
  });
});

describe('Permission and Access Rules', () => {
  const citizenUser: User = {
    id: 'user-c1',
    email: 'c@example.com',
    fullName: 'Citizen One',
    role: 'citizen',
    isActive: true,
    createdAt: '2026-01-01',
  };

  const adminUser: User = {
    id: 'user-a1',
    email: 'a@example.com',
    fullName: 'Admin One',
    role: 'admin',
    isActive: true,
    createdAt: '2026-01-01',
  };

  const workerUser: User = {
    id: 'user-w1',
    email: 'w@example.com',
    fullName: 'Worker One',
    role: 'worker',
    isActive: true,
    createdAt: '2026-01-01',
  };

  const sampleReport: Report = {
    id: 'rep-1',
    title: 'Test Pothole',
    description: 'Deep road hazard',
    category: 'road_damage',
    status: 'submitted',
    priority: 'medium',
    latitude: 40.7,
    longitude: -74.0,
    photos: [],
    citizenId: 'user-c1',
    citizenName: 'Citizen One',
    citizenEmail: 'c@example.com',
    upvotesCount: 0,
    createdAt: '2026-10-10',
    updatedAt: '2026-10-10',
  };

  it('evaluates report creation permissions', () => {
    expect(canCreateReport(citizenUser)).toBe(true);
    expect(canCreateReport(adminUser)).toBe(true);
    expect(canCreateReport(workerUser)).toBe(false);
  });

  it('evaluates citizen report editing and withdrawal permissions', () => {
    expect(canEditReport(citizenUser, sampleReport)).toBe(true);
    expect(canWithdrawReport(citizenUser, sampleReport)).toBe(true);

    // Another citizen cannot edit or withdraw
    const otherCitizen: User = { ...citizenUser, id: 'user-c2' };
    expect(canEditReport(otherCitizen, sampleReport)).toBe(false);
    expect(canWithdrawReport(otherCitizen, sampleReport)).toBe(false);

    // After in_progress, citizen cannot withdraw
    const inProgressReport: Report = { ...sampleReport, status: 'in_progress' };
    expect(canWithdrawReport(citizenUser, inProgressReport)).toBe(false);
  });

  it('computes permitted status transitions per role', () => {
    const adminTransitions = getPermittedStatusTransitions(adminUser, 'submitted');
    expect(adminTransitions).toContain('under_review');
    expect(adminTransitions).toContain('assigned');
    expect(adminTransitions).toContain('rejected');

    const workerTransitions = getPermittedStatusTransitions(workerUser, 'assigned');
    expect(workerTransitions).toEqual(['in_progress']);

    const workerInProgress = getPermittedStatusTransitions(workerUser, 'in_progress');
    expect(workerInProgress).toEqual(['resolved']);
  });
});

describe('API Error Parser', () => {
  it('parses standard error objects and strings', () => {
    const err = new Error('Custom failure');
    const parsed = parseApiError(err);
    expect(parsed.message).toBe('Custom failure');
  });

  it('parses network failures', () => {
    const axiosNetworkErr = {
      isAxiosError: true,
      message: 'Network Error',
      response: undefined,
    };
    const parsed = parseApiError(axiosNetworkErr);
    expect(parsed.isNetworkError).toBe(true);
    expect(parsed.message).toContain('Cannot reach the server');
  });
});
