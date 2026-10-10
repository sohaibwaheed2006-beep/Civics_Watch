import React from 'react';
import { ReportStatus } from '@/types/report';
import { STATUS_DETAILS } from '@/lib/constants';
import { cn } from '@/lib/utils';

export interface StatusBadgeProps {
  status: ReportStatus;
  size?: 'sm' | 'md';
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md', className }) => {
  const details = STATUS_DETAILS[status] || {
    label: status,
    bgClass: 'bg-slate-100',
    textClass: 'text-slate-700',
    dotClass: 'bg-slate-400',
    borderClass: 'border-slate-200',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border font-medium',
        details.bgClass,
        details.textClass,
        details.borderClass,
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs',
        className
      )}
      role="status"
      aria-label={`Status: ${details.label}`}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full shrink-0', details.dotClass)} aria-hidden="true" />
      <span>{details.label}</span>
    </span>
  );
};
