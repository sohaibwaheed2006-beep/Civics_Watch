import React, { useState } from 'react';
import { ReportAttachment } from '@/types/report';
import { Modal } from '@/components/ui/modal';
import { formatFileSize } from '@/lib/formatters';
import { Eye, ImageIcon } from 'lucide-react';

export interface PhotoGalleryProps {
  photos: ReportAttachment[];
}

export const PhotoGallery: React.FC<PhotoGalleryProps> = ({ photos }) => {
  const [activePhoto, setActivePhoto] = useState<ReportAttachment | null>(null);

  if (!photos || photos.length === 0) {
    return (
      <div className="flex items-center gap-2 p-4 rounded-xl border border-dashed border-slate-200 text-xs text-slate-400 bg-slate-50/50">
        <ImageIcon className="h-4 w-4 text-slate-400" />
        <span>No photo evidence attached to this report.</span>
      </div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
        {photos.map((photo) => (
          <div
            key={photo.id}
            onClick={() => setActivePhoto(photo)}
            className="group relative aspect-video cursor-pointer overflow-hidden rounded-xl border border-slate-200 bg-slate-100 shadow-sm transition-all hover:shadow-md"
          >
            <img
              src={photo.url}
              alt={photo.filename}
              className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
              loading="lazy"
            />
            <div className="absolute inset-0 bg-slate-900/30 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white">
              <Eye className="h-5 w-5" />
            </div>
            <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-slate-950/80 to-transparent p-1.5 text-[10px] text-white truncate">
              {photo.filename}
            </div>
          </div>
        ))}
      </div>

      {/* Lightbox Modal */}
      <Modal
        isOpen={Boolean(activePhoto)}
        onClose={() => setActivePhoto(null)}
        title={activePhoto?.filename || 'Evidence Photo'}
        description={`Size: ${activePhoto ? formatFileSize(activePhoto.size) : ''}`}
        size="lg"
      >
        {activePhoto && (
          <div className="flex flex-col items-center">
            <div className="relative max-h-[70vh] overflow-hidden rounded-xl bg-slate-950 flex items-center justify-center w-full">
              <img
                src={activePhoto.url}
                alt={activePhoto.filename}
                className="max-h-[65vh] w-auto object-contain rounded-lg"
              />
            </div>
          </div>
        )}
      </Modal>
    </>
  );
};
