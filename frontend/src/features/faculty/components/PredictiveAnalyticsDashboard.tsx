import React, { Suspense, lazy } from 'react';
import {
  PieChart, Pie, Cell, Tooltip as RechartsTooltip, ResponsiveContainer,
} from 'recharts';
import { Users, AlertTriangle, ShieldAlert, TrendingUp, Loader2, Wifi, WifiOff, RefreshCw } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { useFacultyWebSocket } from '@/hooks/useFacultyWebSocket';
import type { WSConnectionState } from '@/types/websocket';

const AttendanceTrendsChart = lazy(() =>
  import('./AttendanceTrendsChart').then((module) => ({
    default: module.AttendanceTrendsChart,
  }))
);

const AtRiskStudentsList = lazy(() =>
  import('./AtRiskStudentsList').then((module) => ({
    default: module.AtRiskStudentsList,
  }))
);

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface PredictiveAnalyticsDashboardProps {
  /** The active lecture session_id to subscribe the WS to. Null = no live feed. */
  sessionId?: string | null;
}

// ---------------------------------------------------------------------------
// WS connection status badge
// ---------------------------------------------------------------------------

const CONNECTION_CONFIG: Record<
  WSConnectionState,
  { label: string; dot: string; text: string }
> = {
  connected:    { label: 'Live',          dot: 'bg-emerald-500 animate-pulse', text: 'text-emerald-700' },
  connecting:   { label: 'Connecting…',   dot: 'bg-amber-400 animate-pulse',   text: 'text-amber-700'   },
  reconnecting: { label: 'Reconnecting…', dot: 'bg-amber-400 animate-pulse',   text: 'text-amber-700'   },
  failed:       { label: 'Disconnected',  dot: 'bg-red-500',                   text: 'text-red-700'     },
  closed:       { label: 'Offline',       dot: 'bg-slate-400',                 text: 'text-slate-500'   },
};

const WSStatusBadge: React.FC<{ state: WSConnectionState }> = ({ state }) => {
  const cfg = CONNECTION_CONFIG[state];
  const Icon = state === 'connected'
    ? Wifi
    : state === 'reconnecting' || state === 'connecting'
      ? RefreshCw
      : WifiOff;

  return (
    <div className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold ${cfg.text} border-current/20 bg-current/5`}>
      <span className={`h-2 w-2 rounded-full ${cfg.dot}`} />
      <Icon className="h-3 w-3" />
      {cfg.label}
    </div>
  );
};

const ChartChunkFallback = () => (
  <div className="flex h-[350px] items-center justify-center rounded-xl border border-slate-200 bg-white shadow-sm">
    <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
  </div>
);

const RosterChunkFallback = () => (
  <div className="flex h-[350px] items-center justify-center rounded-xl border border-slate-200 bg-white shadow-sm">
    <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
  </div>
);

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const PredictiveAnalyticsDashboard: React.FC<PredictiveAnalyticsDashboardProps> = ({
  sessionId = null,
}) => {
  // 1. WebSocket — real-time event stream
  const { connectionState } = useFacultyWebSocket({ sessionId });

  // 2. Fetch ML Analytics Data (polling removed — WS invalidations drive refresh)
  const { data: analytics, isLoading, isError } = useQuery({
    queryKey: ['ml-analytics-overview'],
    queryFn: async () => {
      const response = await apiClient.get('/analytics/overview');
      return response.data;
    },
    // Keep a gentle 5-minute background refresh as fallback if WS drops
    refetchInterval: 300_000,
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (isError || !analytics) {
    return (
      <div className="flex h-96 items-center justify-center text-red-500">
        Failed to load predictive analytics engine.
      </div>
    );
  }

  const { campus_aggregate, live_inference_demo } = analytics;

  // Format risk distribution data for pie chart
  const riskDistribution = [
    { name: 'Safe',    value: campus_aggregate.total_students_tracked - campus_aggregate.students_at_risk },
    { name: 'At Risk', value: campus_aggregate.students_at_risk },
  ];

  return (
    <div className="space-y-6 px-6 py-6">
      {/* Header row with live WS status badge */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Predictive Analytics Engine</h2>
          <p className="text-sm text-slate-500">Powered by XGBoost &amp; Spatial Telemetry</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <WSStatusBadge state={connectionState} />
          {sessionId && (
            <span className="text-xs text-slate-400 font-mono">
              session: {sessionId.slice(0, 8)}…
            </span>
          )}
          {!sessionId && (
            <span className="text-xs text-slate-400 italic">
              No active session — start a lecture to enable live feed
            </span>
          )}
        </div>
      </div>

      {/* Top Stats Row */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Active Students"
          value={campus_aggregate.total_students_tracked.toString()}
          icon={Users}
          color="text-blue-600"
          bgColor="bg-blue-100"
        />
        <StatCard
          title="Campus Attendance"
          value={`${campus_aggregate.current_attendance_rate}%`}
          icon={TrendingUp}
          color="text-emerald-600"
          bgColor="bg-emerald-100"
        />
        <StatCard
          title="Predicted At-Risk"
          value={campus_aggregate.students_at_risk.toString()}
          icon={AlertTriangle}
          color="text-amber-600"
          bgColor="bg-amber-100"
        />
        <StatCard
          title="Spoofing Attempts"
          value={campus_aggregate.recent_spoofing_attempts.toString()}
          icon={ShieldAlert}
          color="text-red-600"
          bgColor="bg-red-100"
        />
      </div>

      {/* Middle Row: Charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Attendance Trends Line Chart */}
        <Suspense fallback={<ChartChunkFallback />}>
          <AttendanceTrendsChart />
        </Suspense>

        {/* Risk Distribution Chart */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-semibold text-slate-800">Campus Risk Distribution</h3>
          <div style={{ display: 'block', width: '100%', height: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={riskDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {riskDistribution.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={index === 0 ? '#10b981' : '#ef4444'} />
                  ))}
                </Pie>
                <RechartsTooltip
                  formatter={(value: any, name: any) => [String(value), String(name)]}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Live Inference & At-Risk Students */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Live Inference Feed */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm flex flex-col">
           <h3 className="mb-4 text-lg font-semibold text-slate-800">Live Inference Demo</h3>
           <div className="flex-1 bg-slate-50 rounded-lg p-4 border border-slate-100">
             <div className="mb-4 flex items-center justify-between">
                <span className="text-sm font-medium text-slate-600">Sample Student Vector</span>
                <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                  live_inference_demo.classification === 'Safe' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {live_inference_demo.classification}
                </span>
             </div>

             <div className="space-y-3">
               <div>
                 <div className="flex justify-between text-xs mb-1">
                   <span className="text-slate-500">XGBoost Risk Score</span>
                   <span className="font-bold text-slate-700">{live_inference_demo.risk_score_percentage}%</span>
                 </div>
                 <div className="w-full bg-slate-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${live_inference_demo.risk_score_percentage > 50 ? 'bg-red-500' : 'bg-green-500'}`}
                      style={{ width: `${live_inference_demo.risk_score_percentage}%` }}
                    ></div>
                 </div>
               </div>

               <div className="grid grid-cols-2 gap-4 mt-6">
                 <div className="bg-white p-3 rounded shadow-sm text-center">
                    <span className="block text-xs text-slate-500">Attendance Rate</span>
                    <span className="block font-semibold text-slate-800">{(live_inference_demo.telemetry_used.attendance_rate * 100).toFixed(1)}%</span>
                 </div>
                 <div className="bg-white p-3 rounded shadow-sm text-center">
                    <span className="block text-xs text-slate-500">Curriculum Score</span>
                    <span className="block font-semibold text-slate-800">{live_inference_demo.telemetry_used.curriculum_engagement_score.toFixed(1)}</span>
                 </div>
               </div>
             </div>
           </div>
        </div>

        {/* At-Risk Students List */}
        <Suspense fallback={<RosterChunkFallback />}>
          <AtRiskStudentsList />
        </Suspense>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Simple Stat Card Component
// ---------------------------------------------------------------------------
const StatCard = ({ title, value, icon: Icon, color, bgColor }: {
  title: string;
  value: string;
  icon: React.ElementType;
  color: string;
  bgColor: string;
}) => (
  <div className="flex items-center rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md">
    <div className={`mr-4 flex h-12 w-12 items-center justify-center rounded-lg ${bgColor}`}>
      <Icon className={`h-6 w-6 ${color}`} />
    </div>
    <div>
      <p className="text-sm font-medium text-slate-500">{title}</p>
      <h4 className="text-2xl font-bold text-slate-900">{value}</h4>
    </div>
  </div>
);
