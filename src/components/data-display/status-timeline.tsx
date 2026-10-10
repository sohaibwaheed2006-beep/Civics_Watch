import React from 'react';
import { Report, ReportStatus } from '@/types/report';
import { formatDateTime } from '@/lib/formatters';
import { Check, Clock, UserCheck, Wrench, CheckCircle2, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface StatusTimelineProps {
  report: Report;
}

export const StatusTimeline: React.FC<StatusTimelineProps> = ({ report }) => {
  const steps: { key: ReportStatus; label: string; icon: React.ReactNode }[] = [
    { key: 'submitted', label: 'Submitted', icon: <Clock className="h-4 w-4" /> },
    { key: 'under_review', label: 'Under Review', icon: <Check className="h-4 w-4" /> },
    { key: 'assigned', label: 'Assigned', icon: <UserCheck className="h-4 w-4" /> },
    { key: 'in_progress', label: 'In Progress', icon: <Wrench className="h-4 w-4" /> },
    { key: 'resolved', label: 'Resolved', icon: <CheckCircle2 className="h-4 w-4" /> },
  ];

  const statusOrder: Record<ReportStatus, number> = {
    submitted: 0,
    under_review: 1,
    assigned: 2,
    in_progress: 3,
    resolved: 4,
    rejected: -1,
    reopened: 2,
  };

  const currentIdx = statusOrder[report.status];
  const isRejected = report.status === 'rejected';

  return (
    <div className="py-4">
      {isRejected ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 flex items-center gap-3">
          <XCircle className="h-6 w-6 text-rose-600 shrink-0" />
          <div>
            <h4 className="text-sm font-semibold text-rose-900">Report Rejected</h4>
            <p className="text-xs text-rose-700 mt-0.5">
              This report was determined to be outside municipal jurisdiction, a duplicate, or
              unable to be verified.
            </p>
          </div>
        </div>
      ) : (
        <div className="relative">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            {steps.map((step, idx) => {
              const isPast = idx < currentIdx;
              const isCurrent = idx === currentIdx;

              return (
                <div key={step.key} className="flex items-center sm:flex-col sm:items-center text-left sm:text-center flex-1 w-full sm:w-auto">
                  <div
                    className={cn(
                      'flex h-9 w-9 items-center justify-center rounded-full border-2 transition-colors shrink-0 mr-3 sm:mr-0 sm:mb-2',
                      isPast && 'border-teal-600 bg-teal-600 text-white',
                      isCurrent && 'border-teal-600 bg-white text-teal-600 ring-4 ring-teal-50',
                      !isPast && !isCurrent && 'border-slate-200 bg-white text-slate-300'
                    )}
                  >
                    {step.icon}
                  </div>
                  <div>
                    <p
                      className={cn(
                        'text-xs font-semibold',
                        (isPast || isCurrent) ? 'text-slate-900' : 'text-slate-400'
                      )}
                    >
                      {step.label}
                    </p>
                    {isCurrent && (
                      <span className="text-[10px] text-teal-600 font-medium">Current Status</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Timestamp log */}
      <div className="mt-6 border-t border-slate-100 pt-4 text-xs text-slate-500 flex flex-wrap gap-x-6 gap-y-2">
        <div>
          <span className="text-slate-400">Created: </span>
          <span className="font-medium text-slate-700">{formatDateTime(report.createdAt)}</span>
        </div>
        <div>
          <span className="text-slate-400">Last Updated: </span>
          <span className="font-medium text-slate-700">{formatDateTime(report.updatedAt)}</span>
        </div>
        {report.deadline && (
          <div>
            <span className="text-slate-400">SLA Target: </span>
            <span className="font-medium text-amber-700">{formatDateTime(report.deadline)}</span>
          </div>
        )}
      </div>
    </div>
  );
};
