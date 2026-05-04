import React, { useState } from 'react';
import { useAuthStore } from '@/store/authStore';
import { useStudentWebSocket } from '@/shared/hooks/useStudentWebSocket';
import { MarkAttendanceFlow } from '../components/MarkAttendanceFlow';
import { Loader2, Wifi, WifiOff, BookOpen, Clock } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';

// Define the type for the curriculum item based on your MongoDB schema
interface UnlockedModule {
  id: string;
  course_id: string;
  title: string;
  unlocked_at: string;
  resource_uris: string[];
}

export const StudentDashboardPage: React.FC = () => {
  const user = useAuthStore((state) => state.user);
  const [isAttendanceOpen, setIsAttendanceOpen] = useState(false);
  const [selectedSession, setSelectedSession] = useState<{ sessionId: string; geofenceId: string } | null>(null);
  
  // Initialize the WebSocket connection for real-time curriculum unlocks
  const { isConnected } = useStudentWebSocket();

  // Fetch recently unlocked curriculum modules
  // This query will be automatically invalidated and refetched by the WebSocket hook 
  // when a 'curriculum:unlocked' event is received.
  const { data: recentUnlocks, isLoading: isLoadingUnlocks } = useQuery<UnlockedModule[]>({
    queryKey: ['recent-unlocks'],
    queryFn: async () => {
      const response = await apiClient.get('/student/curriculum/recent');
      return response.data;
    },
  });

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Student Portal</h1>
          <p className="text-slate-600 mt-1">Welcome back, {user.name}</p>
        </div>
        
        {/* Real-time connection status indicator */}
        <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white shadow-sm border border-slate-200">
          {isConnected ? (
            <>
              <Wifi className="w-4 h-4 text-emerald-500" />
              <span className="text-sm font-medium text-slate-700">Sync Active</span>
            </>
          ) : (
            <>
              <WifiOff className="w-4 h-4 text-slate-400" />
              <span className="text-sm font-medium text-slate-500">Reconnecting...</span>
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          {/* Main Attendance Marking Component */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="p-6 border-b border-slate-100 bg-slate-50/50">
              <h2 className="text-xl font-semibold text-slate-800">Active Sessions</h2>
              <p className="text-sm text-slate-500">Verify your physical presence to unlock curriculum materials.</p>
            </div>
            <div className="p-6">
              <MarkAttendanceFlow
                isOpen={isAttendanceOpen}
                sessionId={selectedSession?.sessionId || ''}
                geofenceId={selectedSession?.geofenceId || ''}
                userEmail={user?.email || ''}
                onClose={() => setIsAttendanceOpen(false)}
                onSuccess={() => {
                  setIsAttendanceOpen(false);
                  setSelectedSession(null);
                }}
              />
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {/* Curriculum Preview / Stats Widget */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <div className="flex items-center gap-2 mb-4">
              <BookOpen className="w-5 h-5 text-indigo-600" />
              <h3 className="text-lg font-semibold text-slate-800">Recent Unlocks</h3>
            </div>
            
            <div className="space-y-4">
              {isLoadingUnlocks ? (
                <div className="flex justify-center py-6">
                  <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
                </div>
              ) : recentUnlocks && recentUnlocks.length > 0 ? (
                <div className="space-y-3">
                  {recentUnlocks.slice(0, 5).map((module) => (
                    <div 
                      key={module.id} 
                      className="p-4 rounded-lg border border-slate-100 bg-slate-50 hover:bg-slate-100 transition-colors shadow-sm"
                    >
                      <p className="text-xs font-bold text-indigo-600 mb-1 uppercase tracking-wider">
                        {module.course_id}
                      </p>
                      <p className="text-sm font-medium text-slate-800 line-clamp-2">
                        {module.title}
                      </p>
                      <div className="flex items-center gap-1 mt-3 text-xs text-slate-500">
                        <Clock className="w-3.5 h-3.5" />
                        <span>{new Date(module.unlocked_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 bg-slate-50 rounded-lg border border-slate-200 border-dashed">
                  <BookOpen className="w-8 h-8 text-slate-300 mx-auto mb-3" />
                  <p className="text-sm text-slate-500 font-medium">
                    No recent unlocks found.
                  </p>
                  <p className="text-xs text-slate-400 mt-1 px-4">
                    Verify your attendance today to reveal new curriculum modules.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};