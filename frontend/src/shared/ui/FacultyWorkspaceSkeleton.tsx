import React from 'react';
import { SkeletonLoader } from '@/shared/ui/SkeletonLoader';

export const FacultyWorkspaceSkeleton: React.FC = () => {
  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Overview/Hero skeleton */}
      <div className="rounded-[2rem] border border-slate-200 bg-white p-8 sm:p-10 shadow-sm overflow-hidden relative">
        <div className="grid gap-8 lg:grid-cols-2">
          <div className="space-y-6">
            <div className="flex gap-2">
              <SkeletonLoader height="h-6" width="w-32" className="rounded-full" />
              <SkeletonLoader height="h-6" width="w-48" className="rounded-full" />
            </div>
            <SkeletonLoader height="h-12" width="w-full" />
            <SkeletonLoader height="h-4" width="w-3/4" count={2} />
            <div className="grid grid-cols-3 gap-4 pt-4">
              <SkeletonLoader height="h-20" width="w-full" className="rounded-2xl" />
              <SkeletonLoader height="h-20" width="w-full" className="rounded-2xl" />
              <SkeletonLoader height="h-20" width="w-full" className="rounded-2xl" />
            </div>
          </div>
          <div className="hidden lg:block space-y-4">
            <SkeletonLoader height="h-32" width="w-full" className="rounded-3xl" />
            <SkeletonLoader height="h-32" width="w-full" className="rounded-3xl" />
          </div>
        </div>
      </div>

      {/* Grid of cards skeleton */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <div className="lg:col-span-2 grid gap-6 sm:grid-cols-2">
          <div className="rounded-[1.5rem] border border-slate-200 bg-white p-6 shadow-sm space-y-4">
            <SkeletonLoader height="h-5" width="w-1/3" />
            <SkeletonLoader height="h-8" width="w-full" />
            <SkeletonLoader height="h-20" width="w-full" className="rounded-xl" />
          </div>
          <div className="rounded-[1.5rem] border border-slate-200 bg-white p-6 shadow-sm space-y-4">
            <SkeletonLoader height="h-5" width="w-1/3" />
            <SkeletonLoader height="h-8" width="w-full" />
            <SkeletonLoader height="h-20" width="w-full" className="rounded-xl" />
          </div>
        </div>
        <div className="rounded-[1.5rem] border border-slate-200 bg-white p-6 shadow-sm space-y-4">
          <SkeletonLoader height="h-5" width="w-1/2" />
          <div className="h-40 w-full animate-pulse rounded-2xl bg-slate-100" />
          <SkeletonLoader height="h-10" width="w-full" className="rounded-xl" />
        </div>
      </div>
    </div>
  );
};
