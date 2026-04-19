import React, { useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell,
} from 'recharts';
import { Users, AlertTriangle, ShieldAlert, TrendingUp, Loader2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444'];

export const PredictiveAnalyticsDashboard: React.FC = () => {
  // 1. Fetch ML Analytics Data
  const { data: analytics, isLoading, isError } = useQuery({
    queryKey: ['ml-analytics-overview'],
    queryFn: async () => {
      const response = await apiClient.get('/analytics/overview');
      return response.data;
    },
    // Refresh data every 5 minutes in production
    refetchInterval: 300000, 
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

  // Mock data for charts based on campus aggregates
  const attendanceTrends = [
    { date: 'Mon', rate: 92 }, { date: 'Tue', rate: 89 },
    { date: 'Wed', rate: 85 }, { date: 'Thu', rate: campus_aggregate.current_attendance_rate },
  ];

  const riskDistribution = [
    { name: 'Safe', value: campus_aggregate.total_students_tracked - campus_aggregate.students_at_risk },
    { name: 'At Risk', value: campus_aggregate.students_at_risk },
  ];
  return (
    <div className="space-y-6">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-slate-900">Predictive Analytics Engine</h2>
        <p className="text-sm text-slate-500">Powered by XGBoost & Spatial Telemetry</p>
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
        {/* Risk Distribution Chart */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-semibold text-slate-800">Campus Risk Distribution</h3>
          <div className="h-[300px]">
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
                  {riskDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={index === 0 ? '#10b981' : '#ef4444'} />
                  ))}
                </Pie>
                <RechartsTooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

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
      </div>
    </div>
  );
};

// Simple Stat Card Component
const StatCard = ({ title, value, icon: Icon, color, bgColor }: any) => (
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
