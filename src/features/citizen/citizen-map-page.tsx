import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { reportService } from '@/services/report-service';
import { IssueMap } from '@/components/maps/issue-map';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { CardSkeleton } from '@/components/ui/skeleton';
import { ErrorPanel } from '@/components/ui/error-panel';

export const CitizenMapPage: React.FC = () => {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['public-map-reports'],
    queryFn: () => reportService.getMapReports({ limit: 500 }),
  });

  const reports = data || [];

  return (
    <div className="space-y-4">
      <Breadcrumbs
        items={[
          { label: 'Citizen Portal', href: '/citizen/dashboard' },
          { label: 'Community Issue Map' },
        ]}
      />

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Neighborhood Issue Map
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Explore reported hazards, maintenance work in progress, and resolutions across your community.
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="h-[600px] w-full flex items-center justify-center bg-white rounded-2xl border border-slate-200">
          <CardSkeleton />
        </div>
      ) : isError ? (
        <ErrorPanel onRetry={refetch} message="Unable to load map data." />
      ) : (
        <IssueMap reports={reports} baseDetailRoute="/citizen/reports" />
      )}
    </div>
  );
};
