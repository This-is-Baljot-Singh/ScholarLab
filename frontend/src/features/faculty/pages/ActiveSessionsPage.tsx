import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { CalendarClock, Clock3, Loader2, Users, ArrowUpRight } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { LectureAudioUpload } from '../components';

interface ActiveSessionSummary {
  id: string;
  status: string;
  title: string;
  instructor: string;
  students: number;
  startedAt: string;
}

import { AlertCircle } from 'lucide-react';

export const ActiveSessionsPage: React.FC = () => {
  const { data: activeSessions, isLoading: isLoadingSessions, isError, error } = useQuery<ActiveSessionSummary[]>({
    queryKey: ['faculty-live-sessions'],
    queryFn: async () => {
      const response = await apiClient.get('/attendance/sessions');
      return Array.isArray(response.data) ? response.data : [];
    },
    staleTime: 30_000,
    retry: 1,
  });

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] rounded-[2rem] border border-red-100 bg-red-50/50 p-8 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-red-100 text-red-600 mb-4">
          <AlertCircle className="h-8 w-8" />
        </div>
        <h3 className="text-xl font-semibold text-red-900">Service Unavailable</h3>
        <p className="mt-2 text-red-600 max-w-md">
          We're having trouble connecting to the campus attendance service. 
          Please ensure the backend is running locally and try again.
        </p>
      </div>
    );
  }

  const sessionId = activeSessions?.[0]?.id ?? null;

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
            Active sessions
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-900">
            Live teaching sessions at a glance
          </h2>
        </div>
        {isLoadingSessions ? (
          <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-500">
            <Loader2 className="h-3.5 w-3.5 animate-spin text-indigo-600" />
            Syncing sessions
          </span>
        ) : (
          <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-500">
            <Clock3 className="h-3.5 w-3.5 text-indigo-600" />
            {activeSessions?.length ?? 0} live
          </span>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            {activeSessions?.map((session) => (
              <article
                key={session.id}
                className="rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-indigo-600">
                      {session.status}
                    </p>
                    <h3 className="mt-2 text-lg font-semibold text-slate-900">{session.title}</h3>
                  </div>
                  <div className="rounded-2xl bg-indigo-50 p-3 text-indigo-600">
                    <CalendarClock className="h-5 w-5" />
                  </div>
                </div>

                <div className="mt-5 space-y-3 text-sm text-slate-600">
                  <div className="flex items-center gap-2">
                    <Users className="h-4 w-4 text-slate-400" />
                    <span>{session.students} students engaged</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock3 className="h-4 w-4 text-slate-400" />
                    <span>{session.startedAt}</span>
                  </div>
                </div>

                <button
                  type="button"
                  className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-indigo-600 transition hover:text-indigo-700"
                >
                  Open session
                  <ArrowUpRight className="h-4 w-4" />
                </button>
              </article>
            ))}
          </div>
        </div>
        <div className="lg:col-span-1">
          <LectureAudioUpload 
            sessionId={sessionId || 'unknown'} 
            courseId="CS101"
          />
        </div>
      </div>
    </div>
  );
};
