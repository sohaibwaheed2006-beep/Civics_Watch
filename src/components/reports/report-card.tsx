import React from 'react';
import { Link } from 'react-router-dom';
import { Report } from '@/types/report';
import { Card } from '@/components/ui/card';
import { StatusBadge } from '@/components/data-display/status-badge';
import { PriorityBadge } from '@/components/data-display/priority-badge';
import { formatCategory, formatDate } from '@/lib/formatters';
import { MapPin, ThumbsUp, Calendar, ArrowRight, ImageIcon } from 'lucide-react';

export interface ReportCardProps {
  report: Report;
  detailUrl: string;
}

export const ReportCard: React.FC<ReportCardProps> = ({ report, detailUrl }) => {
  const hasPhoto = report.photos && report.photos.length > 0;

  return (
    <Card hoverEffect className="flex flex-col justify-between group overflow-hidden border-slate-200/90 hover:border-teal-300">
      <div>
        {/* Header photo or placeholder banner */}
        <div className="relative aspect-[16/9] -mx-5 -mt-5 mb-4 bg-slate-100 overflow-hidden border-b border-slate-100">
          {hasPhoto ? (
            <img
              src={report.photos[0].url}
              alt={report.title}
              className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
              loading="lazy"
            />
          ) : (
            <div className="h-full w-full flex flex-col items-center justify-center text-slate-400 bg-gradient-to-br from-slate-50 to-slate-100">
              <ImageIcon className="h-8 w-8 text-slate-300 mb-1" />
              <span className="text-xs font-medium text-slate-400">No photo uploaded</span>
            </div>
          )}

          <div className="absolute top-3 left-3 flex items-center gap-1.5 shadow-sm">
            <StatusBadge status={report.status} size="sm" />
          </div>
          <div className="absolute top-3 right-3 shadow-sm">
            <PriorityBadge priority={report.priority} size="sm" />
          </div>
        </div>

        {/* Category tag */}
        <div className="flex items-center justify-between text-xs text-slate-500 mb-1.5">
          <span className="font-semibold text-teal-700 bg-teal-50 px-2 py-0.5 rounded-md border border-teal-100">
            {formatCategory(report.category)}
          </span>
          <span className="text-[11px] text-slate-400 flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            {formatDate(report.createdAt)}
          </span>
        </div>

        {/* Title & Description */}
        <h4 className="text-sm font-semibold text-slate-900 group-hover:text-teal-700 transition-colors line-clamp-1">
          {report.title}
        </h4>
        <p className="text-xs text-slate-600 mt-1 line-clamp-2 leading-relaxed">
          {report.description}
        </p>
      </div>

      {/* Footer Info */}
      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
        <div className="flex items-center gap-1 truncate max-w-[170px]">
          <MapPin className="h-3.5 w-3.5 text-slate-400 shrink-0" />
          <span className="truncate">{report.address || `${report.latitude.toFixed(3)}, ${report.longitude.toFixed(3)}`}</span>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {report.upvotesCount > 0 && (
            <span className="flex items-center gap-1 text-slate-500 text-xs">
              <ThumbsUp className="h-3 w-3 text-teal-600" />
              <span>{report.upvotesCount}</span>
            </span>
          )}

          <Link
            to={detailUrl}
            className="flex items-center gap-1 font-medium text-teal-600 hover:text-teal-700 group/link"
          >
            <span>Details</span>
            <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover/link:translate-x-0.5" />
          </Link>
        </div>
      </div>
    </Card>
  );
};
