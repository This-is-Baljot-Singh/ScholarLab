import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Bell } from 'lucide-react';
import { apiClient } from '@/api/client';
import { useStudentWebSocket } from '@/shared/hooks/useStudentWebSocket';
import { ActiveSessionCard } from '../components/ActiveSessionCard';
import { CurriculumGrid } from '@/features/curriculum/components/CurriculumGrid';
import { AttendanceHistory } from '../components/AttendanceHistory';
import { SkeletonLoader } from '@/shared/ui/SkeletonLoader';
import type { StudentDashboard, CurriculumItem } from '@/types/student';

export const StudentDashboardPage: React.FC = () => {
  const [unlockedCurriculum, setUnlockedCurriculum] = useState<CurriculumItem[]>([]);
  const [activeTab, setActiveTab] = useState<'session' | 'curriculum' | 'attendance'>(
    'session'
  );

  const { data: dashboard, isLoading, isError } = useQuery<StudentDashboard>({
    queryKey: ['student-dashboard'],
    queryFn: () => apiClient.get('/student/dashboard').then((res) => res.data),
  });

  const {
    isConnected,
    emitAttendanceMarked,
    unlockedItems,
  } = useStudentWebSocket(true);

  useEffect(() => {
    if (unlockedItems.length > 0) {
      setUnlockedCurriculum((prev) => {
        const newItems = unlockedItems.filter(
          (item) => !prev.find((p) => p.id === item.id)
        );
        return [...prev, ...newItems];
      });
    }
  }, [unlockedItems]);

  const handleAttendanceMarked = () => {
    if (dashboard?.activeSession?.lecture.id) {
      emitAttendanceMarked(dashboard.activeSession.lecture.id);
    }
  };

  if (isError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <div className="text-center">
          <p className="text-lg font-semibold text-slate-900">Unable to load dashboard</p>
          <p className="mt-1 text-sm text-slate-600">Please try again later</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 pb-20">
      {/* Header */}
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white px-4 py-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
            <p className="mt-0.5 text-xs text-slate-600">
              {isConnected ? '🟢 Connected' : '⚫ Offline'}
            </p>
          </div>
          <button className="relative rounded-lg bg-slate-100 p-2 transition-colors hover:bg-slate-200">
            <Bell className="h-5 w-5 text-slate-700" />
            <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs font-bold text-white">
              2
            </span>
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="px-4 py-6">
        {isLoading ? (
          <div className="space-y-4">
            <SkeletonLoader height="h-40" />
            <SkeletonLoader height="h-32" count={2} />
          </div>
        ) : (
          <>
            {/* Tab Navigation */}
            <div className="mb-6 flex gap-2 overflow-x-auto pb-2">
              {([
                { id: 'session', label: '🎓 Active Session' },
                { id: 'curriculum', label: '📚 Curriculum' },
                { id: 'attendance', label: '📊 History' },
              ] as const).map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`whitespace-nowrap rounded-full px-4 py-2 text-sm font-medium transition-all duration-200 ${
                    activeTab === tab.id
                      ? 'active:scale-95 bg-indigo-600 text-white shadow-md'
                      : 'bg-white text-slate-700 border border-slate-200'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Active Session Tab */}
            {activeTab === 'session' &&
              (dashboard?.activeSession ? (
                <ActiveSessionCard
                  session={dashboard.activeSession}
                  onAttendanceMarked={handleAttendanceMarked}
                />
              ) : (
                <div className="rounded-2xl bg-slate-100 p-8 text-center">
                  <p className="text-slate-600">No active sessions right now</p>
                  <p className="mt-2 text-sm text-slate-500">
                    Check back later for upcoming lectures
                  </p>
                </div>
              ))}

            {/* Curriculum Tab */}
            {activeTab === 'curriculum' && (
              <div className="space-y-4">
                <div>
                  <h2 className="mb-4 text-lg font-semibold text-slate-900">
                    Unlocked Materials
                  </h2>
                  {dashboard?.unlockedCurriculum &&
                  dashboard.unlockedCurriculum.length > 0 ? (
                    <CurriculumGrid
                      items={[...dashboard.unlockedCurriculum, ...unlockedCurriculum]}
                      onItemClick={(item) => {
                        if (item.url) {
                          window.open(item.url, '_blank');
                        }
                      }}
                    />
                  ) : (
                    <div className="rounded-lg bg-slate-100 p-6 text-center">
                      <p className="text-slate-600">No curriculum unlocked yet</p>
                      <p className="mt-1 text-sm text-slate-500">
                        Mark attendance in class to unlock materials
                      </p>
                    </div>
                  )}
                </div>

                {/* New Unlocked Items Notification */}
                {unlockedCurriculum.length > 0 && (
                  <div className="rounded-lg border-l-4 border-green-600 bg-green-50 p-4">
                    <p className="text-sm font-semibold text-green-800">
                      ✨ {unlockedCurriculum.length} new item
                      {unlockedCurriculum.length !== 1 ? 's' : ''} unlocked!
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Attendance Tab */}
            {activeTab === 'attendance' && (
              <AttendanceHistory records={dashboard?.recentAttendance || []} />
            )}
          </>
        )}
      </main>

      {/* Floating Action Button for Quick Access */}
      {dashboard?.activeSession && (
        <div className="fixed bottom-20 right-4 animate-bounce">
          <button className="h-14 w-14 rounded-full bg-indigo-600 text-white shadow-lg transition-all duration-200 hover:scale-110 active:scale-95">
            <span className="text-2xl">👆</span>
          </button>
        </div>
      )}
    </div>
  );
};
