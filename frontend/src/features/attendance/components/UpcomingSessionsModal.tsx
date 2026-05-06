import { useEffect, useMemo, useState } from 'react';
import { CalendarClock, CheckCircle2, Clock3, MapPin, X } from 'lucide-react';
import { Button } from '@/shared/ui/Button';

interface UpcomingSessionsModalProps {
  isOpen: boolean;
  onClose: () => void;
  variant?: 'sheet' | 'page';
}

interface UpcomingSession {
  id: string;
  courseCode: string;
  title: string;
  startAt: string;
  endAt: string;
  location: string;
}

const MOCK_SLOTS = [
  {
    courseCode: 'CS101',
    title: 'Foundations of Programming',
    startHour: 9,
    startMinute: 0,
    durationMinutes: 75,
    location: 'Science Building, Room 201',
  },
  {
    courseCode: 'CS203',
    title: 'Data Structures and Algorithms',
    startHour: 11,
    startMinute: 30,
    durationMinutes: 90,
    location: 'Engineering Block, Lab 3',
  },
  {
    courseCode: 'CS245',
    title: 'Database Systems',
    startHour: 14,
    startMinute: 15,
    durationMinutes: 80,
    location: 'Technology Center, Room 118',
  },
  {
    courseCode: 'CS310',
    title: 'Applied Machine Learning',
    startHour: 16,
    startMinute: 0,
    durationMinutes: 70,
    location: 'Innovation Hub, Seminar Hall B',
  },
];

const formatDayLabel = (iso: string) => {
  const date = new Date(iso);
  return date.toLocaleDateString(undefined, {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
  });
};

const formatTimeRange = (startAt: string, endAt: string) => {
  const start = new Date(startAt);
  const end = new Date(endAt);

  const formatter = new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  });

  return `${formatter.format(start)} - ${formatter.format(end)}`;
};

const buildMockSchedule = (): UpcomingSession[] => {
  const now = new Date();
  const sessions: UpcomingSession[] = [];

  for (let dayOffset = 0; dayOffset < 3; dayOffset += 1) {
    const baseDate = new Date(now);
    baseDate.setDate(now.getDate() + dayOffset + 1);
    baseDate.setSeconds(0, 0);

    const morningSlot = MOCK_SLOTS[(dayOffset * 2) % MOCK_SLOTS.length];
    const afternoonSlot = MOCK_SLOTS[(dayOffset * 2 + 1) % MOCK_SLOTS.length];

    [morningSlot, afternoonSlot].forEach((slot, index) => {
      const start = new Date(baseDate);
      start.setHours(slot.startHour + (index === 1 ? 1 : 0), slot.startMinute, 0, 0);
      const end = new Date(start.getTime() + slot.durationMinutes * 60 * 1000);

      sessions.push({
        id: `${slot.courseCode}-${start.toISOString()}`,
        courseCode: slot.courseCode,
        title: slot.title,
        startAt: start.toISOString(),
        endAt: end.toISOString(),
        location: slot.location,
      });
    });
  }

  return sessions.sort((a, b) => a.startAt.localeCompare(b.startAt));
};

const LoadingSkeleton = () => (
  <div className="space-y-6">
    {Array.from({ length: 4 }).map((_, idx) => (
      <div key={idx} className="relative pl-8">
        <div className="absolute left-0 top-1 h-3.5 w-3.5 rounded-full bg-slate-200" />
        <div className="absolute left-[6px] top-5 h-[calc(100%+8px)] w-[2px] bg-slate-100" />
        <div className="rounded-2xl border border-slate-100 bg-white p-4">
          <div className="h-3 w-24 animate-pulse rounded bg-slate-200" />
          <div className="mt-3 h-5 w-56 animate-pulse rounded bg-slate-200" />
          <div className="mt-3 h-4 w-44 animate-pulse rounded bg-slate-100" />
          <div className="mt-4 h-10 w-32 animate-pulse rounded-xl bg-slate-100" />
        </div>
      </div>
    ))}
  </div>
);

const UpcomingSessionsContent = ({
  isOpen,
  onClose,
  variant = 'sheet',
}: {
  isOpen: boolean;
  onClose: () => void;
  variant?: 'sheet' | 'page';
}) => {
  const [isLoading, setIsLoading] = useState(true);
  const [reminders, setReminders] = useState<Record<string, boolean>>({});

  const sessions = useMemo(() => buildMockSchedule(), []);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    setIsLoading(true);
    const timeoutId = window.setTimeout(() => {
      setIsLoading(false);
    }, 500);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [isOpen]);

  const groupedByDay = useMemo(() => {
    return sessions.reduce<Record<string, UpcomingSession[]>>((acc, session) => {
      const dayKey = session.startAt.slice(0, 10);
      if (!acc[dayKey]) {
        acc[dayKey] = [];
      }
      acc[dayKey].push(session);
      return acc;
    }, {});
  }, [sessions]);

  return (
    <>
      <header className={variant === 'page' ? 'border-b border-slate-200 bg-white px-6 py-4' : 'sticky top-0 z-10 border-b border-slate-200 bg-white/95 px-6 py-4 backdrop-blur'}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-700">Upcoming Sessions</p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-900">Your next 3 days of classes</h2>
            <p className="mt-1 text-sm text-slate-600">Timeline view with reminders for each lecture.</p>
          </div>
          <button
            type="button"
            className="rounded-xl border border-slate-200 p-2 text-slate-500 transition hover:bg-slate-50"
            onClick={onClose}
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </header>

      <div className="space-y-8 px-6 py-6">
          {isLoading ? (
            <LoadingSkeleton />
          ) : (
            Object.entries(groupedByDay).map(([dayKey, daySessions]) => (
              <section key={dayKey} className="space-y-4">
                <div className="inline-flex items-center rounded-full bg-cyan-50 px-3 py-1 text-xs font-semibold text-cyan-700">
                  {formatDayLabel(dayKey)}
                </div>

                <div className="space-y-5">
                  {daySessions.map((session, index) => {
                    const reminderSet = reminders[session.id];
                    const isLast = index === daySessions.length - 1;

                    return (
                      <article key={session.id} className="relative pl-8">
                        <div className="absolute left-0 top-1.5 h-3.5 w-3.5 rounded-full bg-cyan-500 ring-4 ring-cyan-100" />
                        {!isLast && <div className="absolute left-[6px] top-5 h-[calc(100%+16px)] w-[2px] bg-cyan-100" />}

                        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                          <div className="flex flex-wrap items-start justify-between gap-4">
                            <div>
                              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">{session.courseCode}</p>
                              <h3 className="mt-2 text-lg font-semibold text-slate-900">{session.title}</h3>
                            </div>
                            <span className="rounded-xl bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">Lecture</span>
                          </div>

                          <div className="mt-4 grid gap-2 text-sm text-slate-600">
                            <div className="flex items-center gap-2">
                              <Clock3 className="h-4 w-4 text-slate-400" />
                              <span>{formatTimeRange(session.startAt, session.endAt)}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <MapPin className="h-4 w-4 text-slate-400" />
                              <span>{session.location}</span>
                            </div>
                          </div>

                          <Button
                            type="button"
                            variant={reminderSet ? 'secondary' : 'outline'}
                            className="mt-5"
                            onClick={() => setReminders((prev) => ({ ...prev, [session.id]: true }))}
                            disabled={reminderSet}
                          >
                            {reminderSet ? (
                              <>
                                <CheckCircle2 className="mr-2 h-4 w-4 text-emerald-600" />
                                Reminder Set
                              </>
                            ) : (
                              <>
                                <CalendarClock className="mr-2 h-4 w-4" />
                                Set Reminder
                              </>
                            )}
                          </Button>
                        </div>
                      </article>
                    );
                  })}
                </div>
              </section>
            ))
          )}
      </div>
    </>
  );
};

export const UpcomingSessionsModal = ({ isOpen, onClose, variant = 'sheet' }: UpcomingSessionsModalProps) => {
  if (!isOpen) {
    return null;
  }

  if (variant === 'page') {
    return (
      <section className="overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-sm">
        <UpcomingSessionsContent isOpen={isOpen} onClose={onClose} variant={variant} />
      </section>
    );
  }

  return (
    <div className="fixed inset-0 z-50">
      <button
        type="button"
        className="absolute inset-0 bg-slate-900/40"
        onClick={onClose}
        aria-label="Close upcoming sessions panel"
      />

      <aside className="absolute right-0 top-0 h-full w-full max-w-2xl overflow-y-auto border-l border-slate-200 bg-white shadow-2xl">
        <UpcomingSessionsContent isOpen={isOpen} onClose={onClose} variant={variant} />
      </aside>
    </div>
  );
};