import React from 'react';
import { useAuth } from '@/hooks/use-auth';
import { useQuery } from '@tanstack/react-query';
import { reportService } from '@/services/report-service';
import { IssueMap } from '@/components/maps/issue-map';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { CardSkeleton } from '@/components/ui/skeleton';
import { ErrorPanel } from '@/components/ui/error-panel';

export const WorkerMapPage: React.FC = () => {
  const { user } = useAuth();

  // Workers see the whole community map; their own assignments are highlighted
  // (larger, ringed, badged) and can be isolated with the "My assignments"
  // filter on the map toolbar.
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['worker-map-reports'],
    queryFn: () => reportService.getMapReports({ limit: 500 }),
  });

  const reports = data || [];

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
            Geographic view of every community issue. Your assignments are highlighted — use the "My assignments" filter to focus on them.
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
        <IssueMap
          reports={reports}
          baseDetailRoute="/worker/assignments"
          highlightWorkerId={user?.id}
        />
      )}
    </div>
  );
};
