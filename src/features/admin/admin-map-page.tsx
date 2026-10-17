import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { reportService } from '@/services/report-service';
import { IssueMap } from '@/components/maps/issue-map';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { CardSkeleton } from '@/components/ui/skeleton';
import { ErrorPanel } from '@/components/ui/error-panel';

export const AdminMapPage: React.FC = () => {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin-map-reports'],
    queryFn: () => reportService.getMapReports({ limit: 500 }),
  });

  const reports = data || [];

  return (
    <div className="space-y-4">
      <Breadcrumbs
        items={[
          { label: 'Admin Portal', href: '/admin/dashboard' },
          { label: 'Municipal Issue Map' },
        ]}
      />

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Municipal GIS & Incident Map
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Geographic overview of all active, in-progress, and resolved infrastructure reports across all districts.
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="h-[600px] w-full flex items-center justify-center bg-white rounded-2xl border border-slate-200">
          <CardSkeleton />
        </div>
      ) : isError ? (
        <ErrorPanel onRetry={refetch} message="Unable to load municipal map data." />
      ) : (
        <IssueMap reports={reports} baseDetailRoute="/admin/reports" />
      )}
    </div>
  );
};
