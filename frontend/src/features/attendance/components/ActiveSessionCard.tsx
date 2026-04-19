import React, { useState } from 'react';
import { Clock, MapPin, Users } from 'lucide-react';
import type { ActiveSession } from '@/types/student';
import { MarkAttendanceFlow } from './MarkAttendanceFlow';

interface ActiveSessionProps {
  session: ActiveSession;
  onAttendanceMarked: (data: any) => void;
}

export const ActiveSessionCard: React.FC<ActiveSessionProps> = ({
  session,
  onAttendanceMarked,
}) => {
  const [showAttendanceFlow, setShowAttendanceFlow] = useState(false);

  return (
    <>
      <div className="rounded-2xl bg-gradient-to-br from-indigo-50 to-indigo-100 p-6">
        {/* Badge */}
        <div className="mb-4 inline-block rounded-full bg-green-100 px-3 py-1">
          <p className="text-xs font-semibold text-green-700">ONGOING NOW</p>
        </div>

        {/* Title */}
        <h2 className="mb-2 text-2xl font-bold text-slate-900">{session.lecture.title}</h2>

        {/* Instructor */}
        <p className="mb-4 text-sm text-slate-600">by {session.lecture.instructor}</p>

        {/* Session Details */}
        <div className="mb-6 space-y-3">
          {/* Time */}
          <div className="flex items-center gap-3 text-slate-700">
            <Clock className="h-5 w-5 text-indigo-600" />
            <span className="text-sm">
              {session.lecture.startTime} - {session.lecture.endTime}
            </span>
          </div>

          {/* Location */}
          <div className="flex items-center gap-3 text-slate-700">
            <MapPin className="h-5 w-5 text-indigo-600" />
            <span className="text-sm">{session.lecture.location}</span>
          </div>

          {/* Class Code */}
          <div className="flex items-center gap-3 text-slate-700">
            <Users className="h-5 w-5 text-indigo-600" />
            <span className="text-sm font-mono text-indigo-600">
              Code: {session.lecture.classCode}
            </span>
          </div>
        </div>

        {/* Mark Attendance Button */}
        <button
          onClick={() => setShowAttendanceFlow(true)}
          disabled={session.attendanceMarked}
          className={`w-full rounded-xl py-4 font-semibold text-white transition-all duration-200 ${
            session.attendanceMarked
              ? 'bg-slate-400 cursor-not-allowed'
              : 'active:scale-95 bg-indigo-600 hover:bg-indigo-700'
          }`}
        >
          {session.attendanceMarked
            ? `✓ Marked at ${session.markedTime}`
            : 'Mark Attendance'}
        </button>

        {/* Description */}
        <p className="mt-4 text-xs text-slate-600">
          {session.lecture.description}
        </p>
      </div>

      {/* Attendance Flow Modal */}
      <MarkAttendanceFlow
        isOpen={showAttendanceFlow}
        lectureId={session.lecture.id}
        onClose={() => setShowAttendanceFlow(false)}
        onSuccess={(data) => {
          onAttendanceMarked(data);
          setShowAttendanceFlow(false);
        }}
      />
    </>
  );
};
