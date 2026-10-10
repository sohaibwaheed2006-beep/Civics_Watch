import React from 'react';
import { useAuth } from '@/hooks/use-auth';
import { useQuery } from '@tanstack/react-query';
import { assignmentService } from '@/services/assignment-service';
import { IssueMap } from '@/components/maps/issue-map';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { CardSkeleton } from '@/components/ui/skeleton';
import { ErrorPanel } from '@/components/ui/error-panel';

export const WorkerMapPage: React.FC = () => {
  const { user } = useAuth();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['worker-map-assignments', user?.id],
    queryFn: () => (user ? assignmentService.getWorkerAssignments(user.id, { limit: 50 }) : Promise.reject()),
    enabled: Boolean(user?.id),
  });

  const reports = (data?.data || []).map((a) => a.report);

  return (
    <div className="space-y-4">
      <Breadcrumbs
        items={[
          { label: 'Worker Portal', href: '/worker/dashboard' },
          { label: 'Field Navigation Map' },
        ]}
      />

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Field Technician Navigation Map
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Geographic view of all issues assigned to you. Tap any pin to inspect the problem or trigger directions.
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="h-[600px] w-full flex items-center justify-center bg-white rounded-2xl border border-slate-200">
          <CardSkeleton />
        </div>
      ) : isError ? (
        <ErrorPanel onRetry={refetch} message="Unable to load field map." />
      ) : (
        <IssueMap reports={reports} baseDetailRoute="/worker/assignments" />
      )}
    </div>
  );
};
