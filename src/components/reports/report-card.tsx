import React from 'react';
import { Link } from 'react-router-dom';
import { Report } from '@/types/report';
import { Card } from '@/components/ui/card';
import { StatusBadge } from '@/components/data-display/status-badge';
import { PriorityBadge } from '@/components/data-display/priority-badge';
import { formatCategory, formatDate } from '@/lib/formatters';
import { MapPin, ThumbsUp, Calendar, ArrowRight, Camera } from 'lucide-react';
import { getCategoryCoverImage, handleImageFallback } from '@/lib/category-images';

export interface ReportCardProps {
  report: Report;
  detailUrl: string;
}

export const ReportCard: React.FC<ReportCardProps> = ({ report, detailUrl }) => {
  const hasPhoto = report.photos && report.photos.length > 0;
  const photoUrl = hasPhoto ? report.photos[0].url : getCategoryCoverImage(report.category);

  return (
    <Card hoverEffect className="flex flex-col justify-between group overflow-hidden border-slate-200/90 hover:border-teal-300">
      <div>
        {/* Header photo with category visual fallback */}
        <div className="relative aspect-[16/9] -mx-5 -mt-5 mb-4 bg-slate-900/10 overflow-hidden border-b border-slate-100">
          <img
            src={photoUrl}
            alt={report.title}
            onError={(e) => {
              const target = e.currentTarget as HTMLImageElement;
              const catCover = getCategoryCoverImage(report.category);
              if (target.src !== catCover) {
                target.src = catCover;
              } else {
                handleImageFallback(e, report.category);
              }
            }}
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
            loading="lazy"
          />

          {/* Badges Overlay */}
          <div className="absolute top-3 left-3 flex items-center gap-1.5 shadow-sm">
            <StatusBadge status={report.status} size="sm" />
          </div>
          <div className="absolute top-3 right-3 shadow-sm">
            <PriorityBadge priority={report.priority} size="sm" />
          </div>

          {/* Multiple photos or fallback indicator */}
          {hasPhoto && report.photos.length > 1 && (
            <div className="absolute bottom-2 right-2 bg-slate-900/75 backdrop-blur-xs text-white text-[10px] font-medium px-2 py-0.5 rounded-full flex items-center gap-1">
              <Camera className="h-3 w-3" />
              <span>+{report.photos.length - 1}</span>
            </div>
          )}

          {!hasPhoto && (
            <div className="absolute bottom-2 right-2 bg-slate-900/60 backdrop-blur-xs text-slate-200 text-[10px] font-medium px-2 py-0.5 rounded-full">
              Category visual
            </div>
          )}
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
