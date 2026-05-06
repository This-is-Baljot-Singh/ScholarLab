import { CheckCircle2, ShieldCheck, Target, X } from 'lucide-react';
import { DEMO_STUDENT_PERFORMANCE_SNAPSHOT } from '@/features/analytics/lib/studentPerformance';

interface StudentRiskPostureModalProps {
  isOpen: boolean;
  onClose: () => void;
  variant?: 'sheet' | 'page';
}

interface PositiveFactor {
  label: string;
  detail: string;
}

const MAX_SCORE = 100;

const POSITIVE_FACTORS: PositiveFactor[] = [
  {
    label: 'Consistent Geofence Attendance',
    detail: '95% verified within campus boundary',
  },
  {
    label: 'Prompt Assignment Submissions',
    detail: '8 of last 8 submissions on time',
  },
  {
    label: 'High Curriculum Engagement',
    detail: '97% module interaction completion',
  },
];

const Gauge = ({ score }: { score: number }) => {
  const radius = 92;
  const circumference = Math.PI * radius;
  const normalized = Math.max(0, Math.min(score, MAX_SCORE));
  const progressOffset = circumference * (1 - normalized / MAX_SCORE);

  return (
    <div className="relative mx-auto w-full max-w-md pt-4">
      <svg viewBox="0 0 220 130" className="h-48 w-full">
        <path
          d="M 18 112 A 92 92 0 0 1 202 112"
          fill="none"
          stroke="#e2e8f0"
          strokeWidth="14"
          strokeLinecap="round"
        />
        <path
          d="M 18 112 A 92 92 0 0 1 202 112"
          fill="none"
          stroke="#10b981"
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={progressOffset}
          style={{ transition: 'stroke-dashoffset 900ms ease' }}
        />
      </svg>

      <div className="absolute inset-x-0 top-[48%] text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Current Posture</p>
        <p className="mt-2 text-5xl font-semibold tracking-tight text-emerald-500">{score}</p>
        <p className="mt-1 text-sm font-medium text-slate-500">Safe · out of 100</p>
      </div>
    </div>
  );
};

const RiskPostureContent = ({ onClose, variant = 'sheet' }: { onClose: () => void; variant?: 'sheet' | 'page' }) => {
  const safetyScore = DEMO_STUDENT_PERFORMANCE_SNAPSHOT.safetyScore;
  const riskScore = DEMO_STUDENT_PERFORMANCE_SNAPSHOT.riskScore;

  return (
    <>
      <header className={variant === 'page' ? 'border-b border-slate-200 bg-white px-6 py-4' : 'sticky top-0 z-10 border-b border-slate-200 bg-white/95 px-6 py-4 backdrop-blur'}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Risk Score</p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-900">Student Risk Posture</h2>
            <p className="mt-1 text-sm text-slate-600">Visibility into your live analytics stability indicators.</p>
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

      <div className="space-y-6 px-6 py-6">
        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-center gap-2 text-emerald-600">
            <ShieldCheck className="h-4 w-4" />
            <p className="text-sm font-semibold">Safe Posture Maintained</p>
          </div>
          <Gauge score={safetyScore} />
          <div className="mt-2 flex justify-center gap-2 text-sm font-semibold">
            <span className="rounded-full bg-emerald-50 px-3 py-1 text-emerald-700">Safety {safetyScore}%</span>
            <span className="rounded-full bg-rose-50 px-3 py-1 text-rose-700">Risk {riskScore}%</span>
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <p className="text-sm font-semibold text-slate-900">What is keeping your score high</p>
          <div className="mt-4 space-y-3">
            {POSITIVE_FACTORS.map((factor) => (
              <div key={factor.label} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-500" />
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{factor.label}</p>
                    <p className="mt-1 text-sm text-slate-600">{factor.detail}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-slate-50 p-5">
          <div className="flex items-start gap-3">
            <Target className="mt-0.5 h-5 w-5 text-indigo-600" />
            <div>
              <p className="text-sm font-semibold text-slate-900">Improve Score</p>
              <p className="mt-2 text-sm text-slate-600">
                Review Module 4 materials and complete the reinforcement quiz to move your posture
                closer to 100%.
              </p>
            </div>
          </div>
        </section>
      </div>
    </>
  );
};

export const StudentRiskPostureModal = ({ isOpen, onClose, variant = 'sheet' }: StudentRiskPostureModalProps) => {
  if (!isOpen) {
    return null;
  }

  if (variant === 'page') {
    return (
      <section className="overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-sm">
        <RiskPostureContent onClose={onClose} variant={variant} />
      </section>
    );
  }

  return (
    <div className="fixed inset-0 z-50">
      <button
        type="button"
        className="absolute inset-0 bg-slate-900/40"
        onClick={onClose}
        aria-label="Close risk posture panel"
      />

      <aside className="absolute right-0 top-0 h-full w-full max-w-2xl overflow-y-auto border-l border-slate-200 bg-white shadow-2xl">
        <RiskPostureContent onClose={onClose} variant={variant} />
      </aside>
    </div>
  );
};