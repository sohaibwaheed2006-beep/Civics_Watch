import React from 'react';
import { ReportPriority } from '@/types/report';
import { PRIORITY_DETAILS } from '@/lib/constants';
import { cn } from '@/lib/utils';
import { AlertCircle, Flame, ArrowUp, ArrowDown } from 'lucide-react';

export interface PriorityBadgeProps {
  priority: ReportPriority;
  size?: 'sm' | 'md';
  className?: string;
}

export const PriorityBadge: React.FC<PriorityBadgeProps> = ({ priority, size = 'md', className }) => {
  const details = PRIORITY_DETAILS[priority] || {
    label: priority,
    bgClass: 'bg-slate-100',
    textClass: 'text-slate-700',
    borderClass: 'border-slate-200',
  };

  const getIcon = () => {
    switch (priority) {
      case 'urgent':
        return <Flame className="h-3 w-3 text-red-600 shrink-0" />;
      case 'high':
        return <AlertCircle className="h-3 w-3 text-amber-600 shrink-0" />;
      case 'medium':
        return <ArrowUp className="h-3 w-3 text-blue-600 shrink-0" />;
      case 'low':
        return <ArrowDown className="h-3 w-3 text-slate-500 shrink-0" />;
      default:
        return null;
    }
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border font-medium',
        details.bgClass,
        details.textClass,
        details.borderClass,
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-0.5 text-xs',
        className
      )}
      aria-label={`Priority: ${details.label}`}
    >
      {getIcon()}
      <span>{details.label}</span>
    </span>
  );
};
