/**
 * StudentCurriculumView - Displays curriculum resources with timeline visualization
 * Fetches from GET /api/curriculum/resources/{session_id}
 * Auto-re-renders when attendance check-in succeeds via shouldRefreshResources flag
 */

import React, { useEffect, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  FileText,
  Presentation,
  Video,
  Zap,
  Lock,
  Unlock,
  Download,
  ExternalLink,
  Loader2,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';
import { curriculumAPI } from '@/api/studentAPI';
import { useStudentDashboardStore } from '@/store/dashboardStore';
import { SkeletonLoader } from '@/shared/ui/SkeletonLoader';
import { Button } from '@/shared/ui/Button';
import type { UnlockedResource } from '@/types/dashboard';
import { cn } from '@/lib/utils';

interface StudentCurriculumViewProps {
  sessionId: string;
  showAllUnlocked?: boolean;
}

export const StudentCurriculumView: React.FC<StudentCurriculumViewProps> = ({
  sessionId,
  showAllUnlocked = false,
}) => {
  const queryClient = useQueryClient();
  const shouldRefreshResources = useStudentDashboardStore(
    (s) => s.shouldRefreshResources
  );
  const setShouldRefreshResources = useStudentDashboardStore(
    (s) => s.setShouldRefreshResources
  );

  // Fetch session-specific curriculum resources
  const { data: sessionResources = [], isLoading: isLoadingSession } = useQuery({
    queryKey: ['curriculum', 'resources', sessionId],
    queryFn: () => curriculumAPI.getSessionResources(sessionId),
    staleTime: 1000 * 60 * 5,
    retry: 1,
  });

  // Fetch all unlocked items if showing complete view
  const { data: unlockedItems = [], isLoading: isLoadingUnlocked } = useQuery({
    queryKey: ['curriculum', 'unlocked'],
    queryFn: curriculumAPI.getUnlockedItems,
    enabled: showAllUnlocked,
    staleTime: 1000 * 60 * 5,
    retry: 1,
  });

  // Invalidate and refetch when check-in succeeds
  useEffect(() => {
    if (shouldRefreshResources) {
      queryClient.invalidateQueries({
        queryKey: ['curriculum', 'resources', sessionId],
      });
      queryClient.invalidateQueries({ queryKey: ['curriculum', 'unlocked'] });
      setShouldRefreshResources(false);
    }
  }, [shouldRefreshResources, sessionId, queryClient, setShouldRefreshResources]);

  const displayResources = useMemo(() => {
    if (showAllUnlocked) {
      return unlockedItems;
    }
    return sessionResources;
  }, [sessionResources, unlockedItems, showAllUnlocked]);

  // Separate recently unlocked from older ones
  const now = new Date();
  const fiveMinutesAgo = new Date(now.getTime() - 5 * 60 * 1000);

  const recentlyUnlocked = displayResources.filter((r) => {
    const unlockedAt = new Date(r.unlockedAt);
    return unlockedAt > fiveMinutesAgo;
  });

  const otherResources = displayResources.filter((r) => {
    const unlockedAt = new Date(r.unlockedAt);
    return unlockedAt <= fiveMinutesAgo;
  });

  const isLoading = showAllUnlocked ? isLoadingUnlocked : isLoadingSession;

  if (isLoading && displayResources.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="mb-6 text-lg font-semibold text-slate-900">
          Curriculum Resources
        </h2>
        <div className="space-y-4">
          <SkeletonLoader height="h-20" count={3} />
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">
            Curriculum Resources
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {displayResources.length} resource{displayResources.length !== 1 ? 's' : ''}{' '}
            available
          </p>
        </div>
        {recentlyUnlocked.length > 0 && (
          <div className="inline-flex items-center gap-2 rounded-full bg-green-50 px-3 py-1">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <span className="text-xs font-medium text-green-700">
              {recentlyUnlocked.length} new
            </span>
          </div>
        )}
      </div>

      {displayResources.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 py-8 text-center">
          <Lock className="mx-auto h-12 w-12 text-slate-300" />
          <p className="mt-3 text-sm font-medium text-slate-600">
            No resources available yet
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Check in to a session to unlock curriculum materials
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Recently unlocked section */}
          {recentlyUnlocked.length > 0 && (
            <div className="space-y-3 rounded-lg border-2 border-green-200 bg-green-50 p-4">
              <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-green-700">
                <CheckCircle2 className="h-4 w-4" />
                Just Unlocked
              </p>
              <div className="space-y-3">
                {recentlyUnlocked.map((resource) => (
                  <ResourceCard
                    key={resource.id}
                    resource={resource}
                    isNew={true}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Other resources section */}
          {otherResources.length > 0 && (
            <div className="space-y-3">
              {recentlyUnlocked.length > 0 && (
                <p className="text-xs font-semibold uppercase tracking-widest text-slate-500">
                  Previous Resources
                </p>
              )}
              {otherResources.map((resource) => (
                <ResourceCard
                  key={resource.id}
                  resource={resource}
                  isNew={false}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/**
 * Individual resource card component
 */
interface ResourceCardProps {
  resource: UnlockedResource;
  isNew: boolean;
}

const ResourceCard: React.FC<ResourceCardProps> = ({ resource, isNew }) => {
  const typeConfig = getResourceTypeConfig(resource.type);
  const unlockedDate = new Date(resource.unlockedAt);

  return (
    <div
      className={cn(
        'group relative overflow-hidden rounded-lg border-2 p-4 transition-all duration-300',
        isNew
          ? 'animate-in slide-in-from-left-4 border-green-200 bg-white shadow-md hover:shadow-lg'
          : 'border-slate-200 bg-slate-50 hover:border-slate-300 hover:bg-white hover:shadow-sm'
      )}
    >
      {/* Animated background for newly unlocked */}
      {isNew && (
        <div className="absolute inset-0 -z-10 bg-gradient-to-r from-green-50 to-transparent opacity-0 transition-opacity duration-1000 group-hover:opacity-100" />
      )}

      <div className="flex items-start gap-4">
        {/* Icon */}
        <div
          className={cn(
            'mt-1 flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-lg transition-all',
            typeConfig.iconBg
          )}
        >
          {typeConfig.icon}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div>
              <h3 className="font-semibold text-slate-900">{resource.title}</h3>
              <p className="mt-0.5 text-xs text-slate-600">{typeConfig.label}</p>
            </div>
            {isNew && (
              <span className="inline-flex flex-shrink-0 items-center rounded-full bg-green-100 px-2 py-1 text-xs font-semibold text-green-700">
                New
              </span>
            )}
          </div>

          {/* Description */}
          {resource.description && (
            <p className="mt-2 line-clamp-2 text-sm text-slate-600">
              {resource.description}
            </p>
          )}

          {/* Metadata */}
          {resource.metadata && (
            <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-600">
              {resource.metadata.duration && (
                <span className="inline-flex items-center gap-1">
                  ⏱️ {resource.metadata.duration} min
                </span>
              )}
              {resource.metadata.pages && (
                <span className="inline-flex items-center gap-1">
                  📄 {resource.metadata.pages} pages
                </span>
              )}
              {resource.metadata.points && (
                <span className="inline-flex items-center gap-1">
                  ⭐ {resource.metadata.points} points
                </span>
              )}
            </div>
          )}

          {/* Unlock date */}
          <p className="mt-2 text-xs text-slate-500">
            Unlocked {unlockedDate.toLocaleString('en-US', {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </p>
        </div>

        {/* Actions */}
        <div className="flex flex-shrink-0 flex-col gap-2">
          {resource.url && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.open(resource.url, '_blank')}
              className="gap-1"
            >
              <Download className="h-4 w-4" />
              <span className="hidden sm:inline">Get</span>
            </Button>
          )}
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-green-100 text-green-600">
            <Unlock className="h-4 w-4" />
          </div>
        </div>
      </div>

      {/* Timeline indicator */}
      {isNew && (
        <div className="absolute left-0 top-0 h-1 w-0 animate-pulse bg-green-500 duration-1000" />
      )}
    </div>
  );
};

/**
 * Get configuration for resource type
 */
interface ResourceTypeConfig {
  label: string;
  icon: React.ReactNode;
  iconBg: string;
}

const getResourceTypeConfig = (type: string): ResourceTypeConfig => {
  switch (type) {
    case 'pdf':
      return {
        label: 'PDF Document',
        icon: <FileText className="h-6 w-6" />,
        iconBg: 'bg-red-100 text-red-600',
      };
    case 'slides':
      return {
        label: 'Presentation',
        icon: <Presentation className="h-6 w-6" />,
        iconBg: 'bg-orange-100 text-orange-600',
      };
    case 'video':
      return {
        label: 'Video',
        icon: <Video className="h-6 w-6" />,
        iconBg: 'bg-blue-100 text-blue-600',
      };
    case 'quiz':
      return {
        label: 'Quiz',
        icon: <Zap className="h-6 w-6" />,
        iconBg: 'bg-purple-100 text-purple-600',
      };
    case 'assignment':
      return {
        label: 'Assignment',
        icon: <Zap className="h-6 w-6" />,
        iconBg: 'bg-indigo-100 text-indigo-600',
      };
    default:
      return {
        label: type.charAt(0).toUpperCase() + type.slice(1),
        icon: <FileText className="h-6 w-6" />,
        iconBg: 'bg-slate-100 text-slate-600',
      };
  }
};
