import React, { useState } from 'react';
import { cn } from '@/lib/utils';
import { Role } from '@/types/auth';

export interface AvatarProps {
  src?: string | null;
  alt?: string;
  fallback?: string;
  role?: Role;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
  showBorder?: boolean;
}

const sizeClasses = {
  xs: 'h-6 w-6 text-[10px]',
  sm: 'h-8 w-8 text-xs',
  md: 'h-10 w-10 text-sm',
  lg: 'h-14 w-14 text-lg',
  xl: 'h-20 w-20 text-2xl font-bold',
};

const roleGradients: Record<Role | 'default', string> = {
  admin: 'bg-gradient-to-tr from-indigo-600 to-indigo-700 text-white',
  worker: 'bg-gradient-to-tr from-amber-600 to-amber-700 text-white',
  citizen: 'bg-gradient-to-tr from-teal-600 to-teal-700 text-white',
  default: 'bg-gradient-to-tr from-slate-600 to-slate-700 text-white',
};

export const Avatar: React.FC<AvatarProps> = ({
  src,
  alt = 'User avatar',
  fallback,
  role,
  size = 'md',
  className,
  showBorder = false,
}) => {
  const [imageError, setImageError] = useState(false);

  const displayInitials = fallback
    ? fallback.trim().slice(0, 2).toUpperCase()
    : alt
    ? alt.trim().slice(0, 1).toUpperCase()
    : 'U';

  const roleStyle = role ? roleGradients[role] : roleGradients.default;

  const showImage = Boolean(src) && !imageError;

  return (
    <div
      className={cn(
        'relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full font-semibold shadow-xs transition-transform',
        sizeClasses[size],
        showBorder && 'ring-2 ring-white shadow-sm',
        !showImage && roleStyle,
        className
      )}
    >
      {showImage ? (
        <img
          src={src!}
          alt={alt}
          onError={() => setImageError(true)}
          className="h-full w-full object-cover"
          loading="lazy"
        />
      ) : (
        <span>{displayInitials}</span>
      )}
    </div>
  );
};
