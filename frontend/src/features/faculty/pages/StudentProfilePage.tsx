import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  User, 
  MapPin, 
  Phone, 
  Hash, 
  ArrowLeft, 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle,
  Clock,
  Activity,
  ChevronRight,
  Loader2,
  AlertCircle
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Cell
} from 'recharts';
import { apiClient } from '@/lib/api';
import { Button } from '@/shared/ui/Button';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface StudentProfile {
  personal_details: {
    id: string;
    name: string;
    email: string;
    roll_number: string;
    address: string;
    parents_contact: string;
  };
  attendance_history: Array<{
    id: string;
    sessionId: string;
    sessionTitle: string;
    timestamp: string;
    status: string;
    gates: {
      device: boolean;
      kinematic: boolean;
      memory: boolean;
      network: boolean;
      biometric: boolean;
      geofence: boolean;
    };
  }>;
}

interface SHAPExplanation {
  feature: string;
  value: number;
  shap_impact: number;
  human_readable: string;
}

interface RiskPrediction {
  user_id: string;
  risk_label: number;
  risk_probability: number;
  shap_explanations: SHAPExplanation[];
}

// ---------------------------------------------------------------------------
// Sub-Components
// ---------------------------------------------------------------------------

const GateIndicator: React.FC<{ label: string; passed: boolean; icon: string }> = ({ label, passed, icon }) => (
  <div className={`flex flex-col items-center gap-1 p-2 rounded-lg border ${
    passed ? 'bg-emerald-50 border-emerald-100 text-emerald-700' : 'bg-red-50 border-red-100 text-red-700'
  }`}>
    <span className="text-[10px] font-bold uppercase tracking-tighter opacity-70">{icon}</span>
    {passed ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
    <span className="text-[9px] font-bold">{label}</span>
  </div>
);

const SHAPBarChart: React.FC<{ data: SHAPExplanation[] }> = ({ data }) => {
  const chartData = data
    .sort((a, b) => Math.abs(b.shap_impact) - Math.abs(a.shap_impact))
    .map(exp => ({
      feature: exp.feature.replace(/_/g, ' ').toUpperCase(),
      impact: exp.shap_impact,
      displayImpact: Math.abs(exp.shap_impact),
    }));

  return (
    <div className="h-[300px] w-full mt-4">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} layout="vertical" margin={{ left: 100, right: 40 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke="#f1f5f9" />
          <XAxis type="number" hide />
          <YAxis 
            dataKey="feature" 
            type="category" 
            axisLine={false} 
            tickLine={false} 
            width={90}
            tick={{ fontSize: 10, fontWeight: 600, fill: '#64748b' }}
          />
          <RechartsTooltip 
            cursor={{ fill: '#f8fafc' }}
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const data = payload[0].payload;
                return (
                  <div className="bg-white border border-slate-200 shadow-xl rounded-lg p-3 text-xs">
                    <p className="font-bold text-slate-900 mb-1">{data.feature}</p>
                    <p className={`font-mono font-bold ${data.impact > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                      Impact: {data.impact > 0 ? '+' : ''}{data.impact.toFixed(4)}
                    </p>
                  </div>
                );
              }
              return null;
            }}
          />
          <Bar dataKey="displayImpact" radius={[0, 4, 4, 0]} barSize={20}>
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.impact > 0 ? '#ef4444' : '#10b981'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export const StudentProfilePage: React.FC = () => {
  const { student_id } = useParams<{ student_id: string }>();
  const navigate = useNavigate();

  // 1. Fetch Student Profile & History
  const { data: profile, isLoading: isProfileLoading, isError: isProfileError } = useQuery<StudentProfile>({
    queryKey: ['student-profile', student_id],
    queryFn: async () => {
      const response = await apiClient.get(`/students/${student_id}`);
      return response.data;
    },
    enabled: !!student_id,
  });

  // 2. Fetch Risk Analysis
  const { data: risk, isLoading: isRiskLoading } = useQuery<RiskPrediction>({
    queryKey: ['student-risk-deep', student_id],
    queryFn: async () => {
      const response = await apiClient.post(`/analytics/predict/risk/${student_id}`);
      return response.data;
    },
    enabled: !!student_id,
  });

  if (isProfileLoading || isRiskLoading) {
    return (
      <div className="flex h-[80vh] items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-slate-500">
          <Loader2 className="h-10 w-10 animate-spin text-indigo-600" />
          <p className="font-medium">Synthesizing student telemetry profile...</p>
        </div>
      </div>
    );
  }

  if (isProfileError || !profile) {
    return (
      <div className="flex flex-col items-center justify-center h-[70vh] gap-4">
        <AlertCircle className="h-12 w-12 text-red-500" />
        <h2 className="text-xl font-bold text-slate-900">Student Identity Not Found</h2>
        <p className="text-slate-500 text-center max-w-md">
          The requested student ID does not resolve to an active campus record. 
          Please verify the roll number or return to the roster.
        </p>
        <Button onClick={() => navigate('/faculty/analytics')} variant="outline" className="mt-4">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Roster
        </Button>
      </div>
    );
  }

  const { personal_details: details, attendance_history: history } = profile;

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => navigate(-1)}
            className="flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white shadow-sm hover:bg-slate-50 transition-colors"
          >
            <ArrowLeft className="h-5 w-5 text-slate-600" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{details.name}</h1>
            <p className="text-sm font-medium text-slate-500">Student Forensics & Analytics Profile</p>
          </div>
        </div>
        <div className={`flex items-center gap-2 rounded-full px-4 py-1.5 border font-bold text-sm ${
          risk && risk.risk_probability > 0.5 
            ? 'bg-red-50 border-red-200 text-red-700' 
            : 'bg-emerald-50 border-emerald-200 text-emerald-700'
        }`}>
          <Activity className="h-4 w-4" />
          Live Risk Score: {((risk?.risk_probability ?? 0) * 100).toFixed(1)}%
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Column: Personal Details */}
        <div className="lg:col-span-1 space-y-6">
          <div className="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-sm">
            <div className="flex h-16 w-16 items-center justify-center rounded-3xl bg-indigo-50 text-indigo-600 mb-6">
              <User className="h-8 w-8" />
            </div>
            <h3 className="text-xl font-bold text-slate-900 mb-6">Personal Details</h3>
            
            <div className="space-y-6">
              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-50 text-slate-500">
                  <Hash className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-xs font-bold uppercase tracking-widest text-slate-400">Roll Number</p>
                  <p className="text-base font-semibold text-slate-900">{details.roll_number}</p>
                </div>
              </div>

              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-50 text-slate-500">
                  <Phone className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-xs font-bold uppercase tracking-widest text-slate-400">Guardian Contact</p>
                  <p className="text-base font-semibold text-slate-900">{details.parents_contact}</p>
                </div>
              </div>

              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-50 text-slate-500">
                  <MapPin className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-xs font-bold uppercase tracking-widest text-slate-400">Primary Residence</p>
                  <p className="text-base font-semibold text-slate-900 leading-relaxed">{details.address}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-[2rem] border border-slate-200 bg-slate-900 p-8 text-white shadow-xl shadow-indigo-900/10">
            <div className="flex items-center gap-3 mb-4">
              <ShieldCheck className="h-6 w-6 text-indigo-400" />
              <h3 className="text-lg font-bold">Zero-Trust Identity</h3>
            </div>
            <p className="text-sm text-indigo-100/70 leading-relaxed">
              Identity verified via campus-local WebAuthn biometric gates. No biometric data leaves this campus node.
            </p>
          </div>
        </div>

        {/* Right Column: Risk Analysis & Attendance */}
        <div className="lg:col-span-2 space-y-6">
          {/* Risk Analysis Card */}
          <div className="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-sm">
            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-50 text-amber-600">
                  <AlertTriangle className="h-5 w-5" />
                </div>
                <h3 className="text-xl font-bold text-slate-900">XGBoost Risk Inference (SHAP)</h3>
              </div>
              <span className="text-xs font-mono font-bold text-slate-400">V1.4.2-PROD</span>
            </div>

            <div className="grid gap-8 md:grid-cols-2">
              <div className="space-y-4">
                <p className="text-sm text-slate-600 leading-relaxed">
                  The model analyzes {risk?.shap_explanations.length ?? 0} features to predict the probability of academic disengagement or attendance spoofing.
                </p>
                <div className="rounded-2xl bg-slate-50 p-6 border border-slate-100">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Rolling Risk ($r_{i,t}$)</span>
                    <span className={`text-2xl font-bold ${risk && risk.risk_probability > 0.5 ? 'text-red-600' : 'text-emerald-600'}`}>
                      {((risk?.risk_probability ?? 0) * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="h-3 w-full rounded-full bg-slate-200 overflow-hidden">
                    <div 
                      className={`h-full transition-all duration-1000 ${risk && risk.risk_probability > 0.5 ? 'bg-red-500' : 'bg-emerald-500'}`}
                      style={{ width: `${(risk?.risk_probability ?? 0) * 100}%` }}
                    />
                  </div>
                </div>
              </div>

              <div>
                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Feature Impact (SHAP Values)</p>
                {risk && <SHAPBarChart data={risk.shap_explanations} />}
              </div>
            </div>
          </div>

          {/* Attendance History */}
          <div className="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-sm overflow-hidden">
            <div className="flex items-center gap-3 mb-8">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
                <Clock className="h-5 w-5" />
              </div>
              <h3 className="text-xl font-bold text-slate-900">Attendance Audit Trail</h3>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-slate-100">
                    <th className="pb-4 text-xs font-bold text-slate-400 uppercase tracking-widest">Session</th>
                    <th className="pb-4 text-xs font-bold text-slate-400 uppercase tracking-widest">Timestamp</th>
                    <th className="pb-4 text-xs font-bold text-slate-400 uppercase tracking-widest text-center">Zero-Trust Gates</th>
                    <th className="pb-4 text-xs font-bold text-slate-400 uppercase tracking-widest text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {history.map((record) => (
                    <tr key={record.id} className="group hover:bg-slate-50/50 transition-colors">
                      <td className="py-5 pr-4">
                        <p className="font-bold text-slate-900">{record.sessionTitle}</p>
                        <p className="text-xs text-slate-500 font-mono mt-1">{record.sessionId}</p>
                      </td>
                      <td className="py-5 text-sm text-slate-600">
                        {new Date(record.timestamp).toLocaleDateString('en-IN', {
                          day: '2-digit',
                          month: 'short',
                          year: 'numeric'
                        })}
                        <br />
                        <span className="text-xs text-slate-400">
                          {new Date(record.timestamp).toLocaleTimeString('en-IN', {
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </span>
                      </td>
                      <td className="py-5">
                        <div className="flex justify-center gap-1.5">
                          <GateIndicator label="Device" passed={record.gates.device} icon="Dₜ" />
                          <GateIndicator label="Kinematic" passed={record.gates.kinematic} icon="Kₜ" />
                          <GateIndicator label="Memory" passed={record.gates.memory} icon="Mₜ" />
                          <GateIndicator label="Network" passed={record.gates.network} icon="Nₜ" />
                          <GateIndicator label="Biometric" passed={record.gates.biometric} icon="Bₜ" />
                          <GateIndicator label="Spatial" passed={record.gates.geofence} icon="Gₜ" />
                        </div>
                      </td>
                      <td className="py-5 text-right">
                        <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold border ${
                          record.status === 'verified' 
                            ? 'bg-emerald-100 text-emerald-800 border-emerald-200' 
                            : 'bg-amber-100 text-amber-800 border-amber-200'
                        }`}>
                          {record.status === 'verified' ? (
                            <CheckCircle2 className="h-3.5 w-3.5" />
                          ) : (
                            <AlertTriangle className="h-3.5 w-3.5" />
                          )}
                          {record.status.toUpperCase()}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {history.length === 0 && (
                <div className="py-20 text-center text-slate-500">
                  <Activity className="h-12 w-12 mx-auto mb-4 opacity-20" />
                  <p className="font-medium">No historical attendance data available for this student.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
