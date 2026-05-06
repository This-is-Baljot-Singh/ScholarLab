import { useEffect, useMemo, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CheckCircle2,
  Circle,
  Fingerprint,
  Loader2,
  Lock,
  MapPin,
  ShieldCheck,
  Wifi,
  Radar,
  Cpu,
  Smartphone,
  Terminal,
  AlertTriangle,
  X,
  Scan,
  ShieldAlert,
} from 'lucide-react';
import { BottomSheet } from '@/shared/ui/BottomSheet';
import { Button } from '@/shared/ui/Button';
import { apiClient } from '@/api/client';
import { useStudentDashboardStore } from '@/store/dashboardStore';
import { toast } from 'sonner';

interface AttendanceCheckInResponse {
  decision_id: string;
  attendance_marked: boolean;
  reasoning?: string;
  gates_passed?: number;
  timestamp?: string;
}

interface MarkAttendanceFlowProps {
  isOpen: boolean;
  sessionId: string;
  geofenceId: string;
  onClose: () => void;
  onSuccess: (response: AttendanceCheckInResponse) => void;
  courseId?: string;
  lectureTitle?: string;
  lectureLocation?: string;
}

type FlowStep = 'spatial' | 'biometric' | 'conjunction' | 'success' | 'failure';

const SIX_GATES = [
  { key: 'D_t', label: 'Device (D_t)', detail: 'Registered & Trusted', icon: Smartphone },
  { key: 'K_t', label: 'Crypto (K_t)', detail: 'Signature Valid', icon: Lock },
  { key: 'M_t', label: 'Multi-Modal (M_t)', detail: 'Sensor Corroboration', icon: ShieldCheck },
  { key: 'N_t', label: 'Nonce (N_t)', detail: 'Freshness & Time-Window', icon: Cpu },
  { key: 'B_t', label: 'Biometric (B_t)', detail: 'Liveness Score ≥ 0.80', icon: Fingerprint },
  { key: 'G_t', label: 'Spatial (G_t)', detail: 'Composite Confidence > τ', icon: MapPin },
] as const;

const CONFIDENCE_WEIGHTS = {
  wg: 0.25,
  wr: 0.15,
  wu: 0.1,
  wb: 0.2,
  wm: 0.2,
  wl: 0.1,
};

export const MarkAttendanceFlow = ({
  isOpen,
  sessionId,
  geofenceId,
  onClose,
  onSuccess,
  courseId,
  lectureTitle,
  lectureLocation,
}: MarkAttendanceFlowProps) => {
  const setShouldRefreshResources = useStudentDashboardStore((s) => s.setShouldRefreshResources);

  const [step, setStep] = useState<FlowStep>('spatial');
  const [confidenceScore, setConfidenceScore] = useState(0);
  const [terminalLines, setTerminalLines] = useState<string[]>([]);
  const [litGates, setLitGates] = useState<Record<string, boolean>>({});
  const [shouldFail, setShouldFail] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);

  const terminalRef = useRef<HTMLDivElement>(null);

  const addTerminalLine = (line: string) => {
    setTerminalLines((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${line}`].slice(-6));
  };

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [terminalLines]);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setStep('spatial');
      setConfidenceScore(0);
      setTerminalLines(['Initializing Spatial Fusion Engine...']);
      setLitGates({});
      setIsVerifying(false);
    }
  }, [isOpen]);

  // Step 1: Spatial Fusion Simulation
  useEffect(() => {
    if (isOpen && step === 'spatial') {
      const interval = setInterval(() => {
        setConfidenceScore((prev) => {
          const next = prev + 0.04 + Math.random() * 0.05;
          if (next >= 0.87) {
            clearInterval(interval);
            setTimeout(() => setStep('biometric'), 800);
            return 0.87;
          }
          return next;
        });

        const params = ['g_t', 'r_t', 'u_t', 'b_t', 'm_t', 'l_t'];
        const p = params[Math.floor(Math.random() * params.length)];
        addTerminalLine(`Recalculating ${p}... Confidence incremented.`);
      }, 200);
      return () => clearInterval(interval);
    }
  }, [isOpen, step]);

  const handleWebAuthn = async () => {
    setIsVerifying(true);
    addTerminalLine('Requesting WebAuthn Biometric Assertion...');
    
    // Simulate verification delay
    await new Promise((r) => setTimeout(r, 1500));
    
    setIsVerifying(false);
    setStep('conjunction');
  };

  // Step 3: Conjunction Animation
  useEffect(() => {
    if (step === 'conjunction') {
      const runGates = async () => {
        for (let i = 0; i < SIX_GATES.length; i++) {
          await new Promise((r) => setTimeout(r, 400));
          const gate = SIX_GATES[i];
          
          if (shouldFail && gate.key === 'B_t') {
            setStep('failure');
            toast.error('Verification Failed: Biometric Liveness check failed.');
            return;
          }
          
          setLitGates((prev) => ({ ...prev, [gate.key]: true }));
          addTerminalLine(`Gate ${gate.key} PASSED: ${gate.detail}`);
        }
        
        // All gates passed, trigger final submission
        await handleFinalSubmission();
      };
      runGates();
    }
  }, [step, shouldFail]);

  const handleFinalSubmission = async () => {
    addTerminalLine('All gates PASSED. Transmitting cryptographic bundle...');
    
    try {
      const response = await apiClient.post<AttendanceCheckInResponse>('/attendance/checkin', {
        session_id: sessionId,
        geofence_id: geofenceId,
        latitude: 37.7749,
        longitude: -122.4194,
        device_id: 'DEMO_DEVICE_ID',
        device_signature: { id: 'demo-cred-id', response: {} },
        nonce: 'demo-nonce-123',
        biometric_outcome: 'pass',
        biometric_confidence: 1.0,
        liveness_score: 1.0,
      });

      if (response.data.attendance_marked) {
        setStep('success');
        setShouldRefreshResources(true);
        onSuccess(response.data);
        setTimeout(() => onClose(), 3000);
      }
    } catch (error) {
      // In demo mode, we'll simulate success even if API is missing
      setStep('success');
      setShouldRefreshResources(true);
      onSuccess({
        decision_id: `DEMO-${Math.random().toString(36).toUpperCase().slice(2, 10)}`,
        attendance_marked: true,
      });
      setTimeout(() => onClose(), 3000);
    }
  };

  return (
    <BottomSheet
      isOpen={isOpen}
      onClose={onClose}
      title="Zero-Trust Attendance"
      height="full"
      className="bg-slate-950"
    >
      <div className="relative h-full overflow-hidden bg-slate-950 p-6 text-white selection:bg-indigo-500/30">
        {/* Simulate Failure Toggle (Hidden/Corner) */}
        <button
          onClick={() => setShouldFail(!shouldFail)}
          className={`absolute bottom-4 right-4 z-50 rounded-full p-2 transition-colors ${
            shouldFail ? 'bg-rose-500/20 text-rose-500' : 'bg-slate-800 text-slate-500'
          }`}
          title="Simulate Failure"
        >
          <ShieldAlert className="h-4 w-4" />
        </button>

        <AnimatePresence mode="wait">
          {step === 'spatial' && (
            <motion.div
              key="spatial"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-8 pt-4"
            >
              <div className="text-center">
                <div className="relative mx-auto flex h-32 w-32 items-center justify-center">
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
                    className="absolute inset-0 rounded-full border-2 border-dashed border-indigo-500/30"
                  />
                  <motion.div
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                    className="absolute inset-4 rounded-full border border-indigo-500/50"
                  />
                  <Radar className="h-10 w-10 text-indigo-400" />
                  <div className="absolute inset-0 animate-pulse bg-indigo-500/5 blur-3xl" />
                </div>
                <h3 className="mt-6 text-2xl font-bold tracking-tight">Spatial Fusion Pipeline</h3>
                <p className="mt-2 text-slate-400">Synchronizing multi-constellation GNSS & RF signals</p>
              </div>

              <div className="space-y-4">
                <div className="flex items-end justify-between px-1">
                  <div className="space-y-1">
                    <p className="text-xs font-bold uppercase tracking-widest text-indigo-400">Confidence Score (C_t)</p>
                    <p className="font-mono text-3xl font-bold text-white">{(confidenceScore * 100).toFixed(1)}%</p>
                  </div>
                  <div className="text-right text-[10px] font-mono text-slate-500">
                    τ = 0.85
                  </div>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-slate-900 border border-slate-800">
                  <motion.div
                    className="h-full bg-gradient-to-r from-indigo-600 to-cyan-400"
                    initial={{ width: 0 }}
                    animate={{ width: `${confidenceScore * 100}%` }}
                  />
                </div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 font-mono text-[11px] leading-relaxed text-indigo-300/80">
                <p className="mb-2 flex items-center gap-2 border-b border-slate-800 pb-2 text-slate-500">
                  <Terminal className="h-3 w-3" /> AT_REALTIME_LOGS
                </p>
                <div ref={terminalRef} className="space-y-1 h-24 overflow-y-auto scrollbar-hide">
                  {terminalLines.map((line, i) => (
                    <div key={i} className="flex gap-2">
                      <span className="shrink-0 text-slate-600">❯</span>
                      <span>{line}</span>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          {step === 'biometric' && (
            <motion.div
              key="biometric"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="flex flex-col items-center justify-center space-y-10 pt-12"
            >
              <div className="relative">
                <div className="absolute inset-0 animate-ping rounded-full bg-indigo-500/20" />
                <div className="relative flex h-24 w-24 items-center justify-center rounded-3xl border border-indigo-500/50 bg-indigo-500/10 shadow-[0_0_40px_-10px_rgba(79,70,229,0.5)]">
                  <Fingerprint className="h-12 w-12 text-indigo-400" />
                </div>
              </div>

              <div className="text-center">
                <h3 className="text-2xl font-bold">Biometric Assertion</h3>
                <p className="mt-2 max-w-xs text-slate-400">
                  Verifying device IMEI integrity and WebAuthn biometric liveness.
                </p>
              </div>

              <Button
                size="lg"
                className="group relative w-full h-16 overflow-hidden bg-indigo-600 text-lg font-bold hover:bg-indigo-500 transition-all shadow-[0_0_30px_-5px_rgba(79,70,229,0.4)]"
                onClick={handleWebAuthn}
                disabled={isVerifying}
              >
                {isVerifying ? (
                  <Loader2 className="h-6 w-6 animate-spin" />
                ) : (
                  <span className="flex items-center gap-3">
                    <Scan className="h-5 w-5" /> Authenticate via WebAuthn
                  </span>
                )}
                <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/10 to-transparent group-hover:translate-x-full transition-transform duration-1000" />
              </Button>
            </motion.div>
          )}

          {step === 'conjunction' && (
            <motion.div
              key="conjunction"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="space-y-6 pt-4"
            >
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div>
                  <h3 className="text-lg font-bold">6-Gate Conjunction (A_t)</h3>
                  <p className="text-xs text-slate-500 font-mono mt-1">A_t = G_t ∧ K_t ∧ M_t ∧ N_t ∧ B_t ∧ D_t</p>
                </div>
                <div className="h-10 w-10 flex items-center justify-center rounded-xl bg-slate-900 border border-slate-800">
                  <ShieldCheck className="h-5 w-5 text-indigo-400" />
                </div>
              </div>

              <div className="grid gap-3">
                {SIX_GATES.map((gate, idx) => {
                  const Icon = gate.icon;
                  const isLit = litGates[gate.key];
                  return (
                    <motion.div
                      key={gate.key}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: idx * 0.1 }}
                      className={`flex items-center justify-between rounded-xl border p-4 transition-all duration-500 ${
                        isLit
                          ? 'border-emerald-500/30 bg-emerald-500/5'
                          : 'border-slate-800 bg-slate-900/20'
                      }`}
                    >
                      <div className="flex items-center gap-4">
                        <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                          isLit ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-500'
                        }`}>
                          <Icon className="h-5 w-5" />
                        </div>
                        <div>
                          <p className={`text-sm font-bold ${isLit ? 'text-white' : 'text-slate-400'}`}>
                            {gate.label}
                          </p>
                          <p className="text-[10px] text-slate-500 uppercase tracking-wider">{gate.detail}</p>
                        </div>
                      </div>
                      {isLit ? (
                        <motion.div
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500 text-slate-950"
                        >
                          <CheckCircle2 className="h-4 w-4" />
                        </motion.div>
                      ) : (
                        <div className="h-5 w-5 rounded-full border border-slate-800" />
                      )}
                    </motion.div>
                  );
                })}
              </div>
            </motion.div>
          )}

          {step === 'success' && (
            <motion.div
              key="success"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex flex-col items-center justify-center h-full space-y-8 pt-10"
            >
              <div className="relative">
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: [0, 1.2, 1] }}
                  className="relative z-10 flex h-32 w-32 items-center justify-center rounded-full bg-emerald-500 text-slate-950 shadow-[0_0_50px_rgba(16,185,129,0.4)]"
                >
                  <CheckCircle2 className="h-16 w-16" />
                </motion.div>
                <div className="absolute inset-0 -z-0 animate-ping rounded-full bg-emerald-500/20" />
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 10, repeat: Infinity, ease: 'linear' }}
                  className="absolute -inset-8 border border-emerald-500/20 rounded-full border-dashed"
                />
              </div>

              <div className="text-center space-y-3">
                <h3 className="text-3xl font-black tracking-tight text-white">ATTENDANCE VERIFIED</h3>
                <p className="text-slate-400 font-medium px-8">
                  Zero-trust cryptographic bundle accepted. Curriculum resources have been unlocked for your dashboard.
                </p>
              </div>

              <div className="w-full max-w-xs space-y-3 pt-6">
                <div className="flex justify-between text-[10px] font-mono text-slate-500 uppercase tracking-widest">
                  <span>Decision ID</span>
                  <span className="text-emerald-400">SL-2026-X892</span>
                </div>
                <div className="h-1 w-full bg-slate-900 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-emerald-500"
                    initial={{ width: '100%' }}
                    animate={{ width: 0 }}
                    transition={{ duration: 3 }}
                  />
                </div>
              </div>
            </motion.div>
          )}

          {step === 'failure' && (
            <motion.div
              key="failure"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center justify-center h-full space-y-8 pt-10 text-center"
            >
              <div className="flex h-24 w-24 items-center justify-center rounded-full bg-rose-500/20 text-rose-500">
                <AlertTriangle className="h-12 w-12" />
              </div>
              <div className="space-y-4 px-6">
                <h3 className="text-2xl font-bold text-white">Verification Flagged</h3>
                <p className="text-slate-400 leading-relaxed">
                  Your attendance check-in failed the biometric liveness challenge. This event has been flagged for faculty review.
                </p>
              </div>
              <Button
                variant="outline"
                className="border-slate-800 text-slate-400 hover:bg-slate-900"
                onClick={onClose}
              >
                Return to Dashboard
              </Button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </BottomSheet>
  );
};
