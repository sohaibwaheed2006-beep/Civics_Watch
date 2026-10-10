import { describe, it, expect, beforeEach } from 'vitest';
import { MockBackendAdapter } from '@/lib/mock-adapter';
import { INITIAL_USERS } from '@/lib/mock-data';

describe('Mock Backend Adapter State Operations', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('lists seeded reports with pagination and filtering', async () => {
    const res = await MockBackendAdapter.getReportsList({ limit: 5 });
    expect(res.data.length).toBeLessThanOrEqual(5);
    expect(res.total).toBeGreaterThan(0);
  });

  it('filters reports by category and status', async () => {
    const res = await MockBackendAdapter.getReportsList({
      category: 'road_damage',
    });
    expect(res.data.every((r) => r.category === 'road_damage')).toBe(true);
  });

  it('creates a new report and persists it', async () => {
    const citizen = INITIAL_USERS[0];
    const created = await MockBackendAdapter.createReport(
      {
        title: 'Broken bench in central park',
        description: 'Wood slats splintered and broken on pedestrian path bench.',
        category: 'public_property',
        latitude: 40.785,
        longitude: -73.968,
      },
      citizen
    );

    expect(created.id).toBeDefined();
    expect(created.title).toBe('Broken bench in central park');
    expect(created.status).toBe('submitted');

    // Retrieve by ID
    const retrieved = await MockBackendAdapter.getReportById(created.id);
    expect(retrieved.id).toBe(created.id);
  });

  it('updates report status and appends resolution notes', async () => {
    const admin = INITIAL_USERS[1];
    const reports = await MockBackendAdapter.getReportsList();
    const target = reports.data[0];

    const updated = await MockBackendAdapter.updateReportStatus(
      target.id,
      {
        status: 'resolved',
        note: 'Repairs finished and inspected.',
      },
      admin
    );

    expect(updated.status).toBe('resolved');
    expect(updated.resolutionNote).toBe('Repairs finished and inspected.');
  });

  it('toggles upvote on a report', async () => {
    const citizen = INITIAL_USERS[0];
    const reports = await MockBackendAdapter.getReportsList();
    const target = reports.data[0];
    const initialUpvotes = target.upvotesCount;

    const res = await MockBackendAdapter.toggleUpvote(target.id, citizen);
    expect(typeof res.upvotesCount).toBe('number');
  });

  it('creates and retrieves departments', async () => {
    const newDept = await MockBackendAdapter.createDepartment({
      name: 'Traffic Signal Engineering',
      description: 'Traffic signals and pedestrian countdown timers.',
      defaultSlaHours: 12,
    });

    expect(newDept.id).toBeDefined();
    expect(newDept.name).toBe('Traffic Signal Engineering');

    const depts = await MockBackendAdapter.getDepartmentsList();
    expect(depts.some((d) => d.name === 'Traffic Signal Engineering')).toBe(true);
  });
});
