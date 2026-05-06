/**
 * ActiveClassroomView - Shows current classroom status with check-in counters
 * Displays "Currently Teaching: CS101" with live student verification stats
 */

import React, { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Users,
  CheckCircle2,
  AlertCircle,
  Clock,
  MapPin,
  Loader2,
} from 'lucide-react';
import { classroomAPI } from '@/api/facultyAPI';
import { SkeletonLoader } from '@/shared/ui/SkeletonLoader';
import { cn } from '@/lib/utils';

interface ActiveClassroomViewProps {
  sessionId?: string;
  showDetails?: boolean;
}

// Mock data for development
const MOCK_CLASSROOM = {
  sessionId: 'session-101',
  courseId: 'CS101',
  courseTitle: 'Introduction to Computer Science',
  instructorName: 'Dr. Sarah Chen',
  startTime: new Date().toISOString(),
  location: 'Science Building, Room 201',
  totalEnrolled: 45,
  successfulCheckIns: 38,
  flaggedForReview: 2,
};

export const ActiveClassroomView: React.FC<ActiveClassroomViewProps> = ({
  sessionId,
  showDetails = true,
}) => {
  // Fetch active classroom
  const { data: classroom, isLoading, error } = useQuery({
    queryKey: ['classroom', 'active', sessionId],
    queryFn: classroomAPI.getActiveClassroom,
    staleTime: 1000 * 30, // 30 seconds for real-time updates
    retry: 1,
    refetchInterval: 1000 * 15, // Poll every 15 seconds
  });

  // Fetch check-in stats
  const currentSessionId = classroom?.sessionId || sessionId;
  const { data: checkInStats } = useQuery({
    queryKey: ['classroom', 'checkin-stats', currentSessionId],
    queryFn: () => classroomAPI.getCheckInStats(currentSessionId!),
    enabled: !!currentSessionId,
    staleTime: 1000 * 10, // 10 seconds for real-time data
    refetchInterval: 1000 * 5, // Poll every 5 seconds
  });

  const displayClassroom = useMemo(() => {
    if (classroom) return classroom;
    if (error) {
      console.warn('Using mock classroom data:', error);
      return MOCK_CLASSROOM;
    }
    return null;
  }, [classroom, error]);

  if (isLoading && !displayClassroom) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="space-y-4">
          <SkeletonLoader height="h-6" width="w-1/2" />
          <SkeletonLoader height="h-20" />
        </div>
      </div>
    );
  }

  if (!displayClassroom) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6">
        <p className="text-sm text-slate-600">No active classroom session</p>
      </div>
    );
  }

  const checkedInPercentage = Math.round(
    (displayClassroom.successfulCheckIns / displayClassroom.totalEnrolled) * 100
  );

  const notCheckedIn =
    displayClassroom.totalEnrolled -
    displayClassroom.successfulCheckIns -
    displayClassroom.flaggedForReview;

  return (
    <div className="overflow-hidden rounded-2xl border-2 border-indigo-200 bg-gradient-to-br from-indigo-50 to-white shadow-sm">
      {/* Header */}
      <div className="border-b border-indigo-100 bg-indigo-50 px-6 py-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-indigo-600">
              Currently Teaching
            </p>
            <h2 className="mt-2 text-2xl font-bold text-slate-900">
              {displayClassroom.courseId}: {displayClassroom.courseTitle}
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              {displayClassroom.instructorName}
            </p>
          </div>
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-indigo-600 text-white">
            <Users className="h-7 w-7" />
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="p-6">
        {/* Session Info */}
        {showDetails && (
          <div className="mb-6 space-y-2 text-sm">
            <div className="flex items-center gap-2 text-slate-600">
              <Clock className="h-4 w-4 text-slate-400" />
              <span>
                Started{' '}
                {new Date(displayClassroom.startTime).toLocaleTimeString('en-US', {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </span>
            </div>
            <div className="flex items-center gap-2 text-slate-600">
              <MapPin className="h-4 w-4 text-slate-400" />
              <span>{displayClassroom.location}</span>
            </div>
          </div>
        )}

        {/* Check-in Status Grid */}
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            {/* Successful Check-ins */}
            <div className="rounded-lg border-2 border-green-200 bg-green-50 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-widest text-green-600">
                    Verified
                  </p>
                  <p className="mt-2 text-3xl font-bold text-green-700">
                    {displayClassroom.successfulCheckIns}
                  </p>
                  <p className="mt-1 text-xs text-green-600">
                    {checkedInPercentage}% of class
                  </p>
                </div>
                <CheckCircle2 className="h-8 w-8 text-green-600" />
              </div>
            </div>

            {/* Flagged for Review */}
            <div className="rounded-lg border-2 border-amber-200 bg-amber-50 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-widest text-amber-600">
                    Flagged
                  </p>
                  <p className="mt-2 text-3xl font-bold text-amber-700">
                    {displayClassroom.flaggedForReview}
                  </p>
                  <p className="mt-1 text-xs text-amber-600">Needs review</p>
                </div>
                <AlertCircle className="h-8 w-8 text-amber-600" />
              </div>
            </div>

            {/* Not Yet Checked In */}
            <div className="rounded-lg border-2 border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-widest text-slate-600">
                    Pending
                  </p>
                  <p className="mt-2 text-3xl font-bold text-slate-700">
                    {notCheckedIn}
                  </p>
                  <p className="mt-1 text-xs text-slate-600">Awaiting check-in</p>
                </div>
                <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
              </div>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-slate-700">Overall Check-in Progress</span>
              <span className="font-semibold text-indigo-600">
                {displayClassroom.successfulCheckIns} / {displayClassroom.totalEnrolled}
              </span>
            </div>
            <div className="overflow-hidden rounded-full bg-slate-200 h-3">
              <div
                className={cn(
                  'h-full bg-gradient-to-r from-indigo-500 to-indigo-600 transition-all duration-500',
                  checkedInPercentage === 100 && 'from-green-500 to-green-600'
                )}
                style={{ width: `${checkedInPercentage}%` }}
              />
            </div>
          </div>

          {/* Status Message */}
          <div className="rounded-lg bg-indigo-50 p-4 text-sm">
            <p className="text-indigo-900">
              {checkedInPercentage === 100
                ? '✨ All students have successfully checked in!'
                : displayClassroom.flaggedForReview > 0
                  ? `⚠️ ${displayClassroom.flaggedForReview} student${displayClassroom.flaggedForReview > 1 ? 's' : ''} flagged for manual review. Check the Student Management table for details.`
                  : `${displayClassroom.totalEnrolled - displayClassroom.successfulCheckIns} student${displayClassroom.totalEnrolled - displayClassroom.successfulCheckIns !== 1 ? 's' : ''} still checking in...`}
            </p>
          </div>
        </div>

        {/* Real-time Indicator */}
        {checkInStats && (
          <div className="mt-4 flex items-center gap-2 text-xs text-slate-500">
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-indigo-600" />
            Last updated {new Date().toLocaleTimeString('en-US', {
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
            })}
          </div>
        )}
      </div>
    </div>
  );
};
