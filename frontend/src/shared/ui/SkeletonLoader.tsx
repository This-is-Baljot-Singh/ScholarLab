import React from 'react';

export const SkeletonLoader: React.FC<{ 
  height?: string; 
  width?: string; 
  className?: string;
  count?: number;
}> = ({ height = 'h-4', width = 'w-full', className = '', count = 1 }) => {
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className={`${height} ${width} animate-pulse rounded-lg bg-slate-200`}
        />
      ))}
    </div>
  );
};

export const BiometricVerificationSkeleton: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Icon skeleton */}
      <div className="flex justify-center">
        <div className="h-16 w-16 animate-pulse rounded-full bg-slate-200" />
      </div>

      {/* Title skeleton */}
      <SkeletonLoader height="h-6" width="w-3/4" className="mx-auto" />

      {/* Description skeleton */}
      <SkeletonLoader height="h-4" width="w-full" count={2} />

      {/* Progress indicator skeleton */}
      <div className="space-y-2">
        <SkeletonLoader height="h-2" width="w-full" />
      </div>

      {/* Button skeleton */}
      <SkeletonLoader height="h-12" width="w-full" />
    </div>
  );
};

export const AttendanceRecordSkeleton: React.FC<{ count?: number }> = ({ count = 3 }) => {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex gap-4">
          {/* Date skeleton */}
          <div className="h-12 w-12 flex-shrink-0 animate-pulse rounded-lg bg-slate-200" />

          {/* Content skeleton */}
          <div className="flex-1 space-y-2">
            <SkeletonLoader height="h-4" width="w-3/4" />
            <SkeletonLoader height="h-3" width="w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
};
