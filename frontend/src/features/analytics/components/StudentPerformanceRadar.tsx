/**
 * StudentPerformanceRadar - Radar chart showing performance metrics
 * Displays: Attendance Rate, Curriculum Engagement, Risk Score (inverted)
 * Uses recharts for visualization
 */

import React, { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from 'recharts';
import { Shield, AlertCircle, Loader2 } from 'lucide-react';
import { analyticsAPI } from '@/api/studentAPI';
import type { StudentPerformanceMetrics } from '@/types/dashboard';
import { cn } from '@/lib/utils';
import {
  DEMO_STUDENT_PERFORMANCE_SNAPSHOT,
  normalizeStudentPerformanceSnapshot,
} from '../lib/studentPerformance';

interface StudentPerformanceRadarProps {
  mockMode?: boolean; // For demo/testing
}

export const StudentPerformanceRadar: React.FC<StudentPerformanceRadarProps> =
  ({ mockMode = false }) => {
    // Fetch real metrics from API (unless in mock mode)
    const { data: metrics, isLoading, error } = useQuery({
      queryKey: ['analytics', 'performance'],
      queryFn: analyticsAPI.getPerformanceMetrics,
      enabled: !mockMode,
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    });

    // Use mock data if API fails or in mock mode
    const displayMetrics = useMemo(() => {
      if (mockMode || error || !metrics) {
        return DEMO_STUDENT_PERFORMANCE_SNAPSHOT;
      }
      return normalizeStudentPerformanceSnapshot(metrics as StudentPerformanceMetrics);
    }, [metrics, error, mockMode]);

    // Prepare chart data
    const chartData = useMemo(() => {
      return [
        {
          metric: 'Attendance',
          value: displayMetrics.attendanceRate,
          fullMark: 100,
        },
        {
          metric: 'Curriculum',
          value: displayMetrics.curriculumEngagement,
          fullMark: 100,
        },
        {
          metric: 'Safety Score',
          value: displayMetrics.safetyScore,
          fullMark: 100,
        },
      ];
    }, [displayMetrics]);

    // Determine status based on risk score
    const status = useMemo(() => {
      const safetyScore = displayMetrics.safetyScore;
      if (safetyScore >= 80) {
        return {
          label: 'Safe',
          color: 'text-green-600',
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200',
          badge: 'bg-green-100 text-green-700',
        };
      } else if (safetyScore >= 50) {
        return {
          label: 'Moderate',
          color: 'text-amber-600',
          bgColor: 'bg-amber-50',
          borderColor: 'border-amber-200',
          badge: 'bg-amber-100 text-amber-700',
        };
      } else {
        return {
          label: 'At-Risk',
          color: 'text-red-600',
          bgColor: 'bg-red-50',
          borderColor: 'border-red-200',
          badge: 'bg-red-100 text-red-700',
        };
      }
    }, [displayMetrics.safetyScore]);

    if (isLoading && !mockMode && !displayMetrics) {
      return (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
          </div>
        </div>
      );
    }

    return (
      <div className={cn(
        'rounded-2xl border p-6 shadow-sm transition-colors',
        status.borderColor,
        status.bgColor
      )}>
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              Performance Analysis
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              Your current attendance and curriculum engagement metrics
            </p>
          </div>
          <div className={cn(
            'inline-flex items-center gap-2 rounded-full px-3 py-1.5 font-semibold',
            status.badge
          )}>
            <Shield className="h-4 w-4" />
            {status.label}
          </div>
        </div>

        {/* Radar Chart */}
        <div className="flex justify-center pb-6">
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart
              data={chartData}
              margin={{ top: 20, right: 40, bottom: 20, left: 40 }}
            >
              <PolarGrid
                stroke="#e2e8f0"
                strokeWidth={1.5}
                style={{ opacity: 0.6 }}
              />
              <PolarAngleAxis
                dataKey="metric"
                stroke="#64748b"
                style={{ fontSize: '12px', fontWeight: 500 }}
              />
              <PolarRadiusAxis
                angle={90}
                domain={[0, 100]}
                stroke="#cbd5e1"
                style={{ fontSize: '12px' }}
              />
              <Radar
                name="Score"
                dataKey="value"
                stroke="#4f46e5"
                fill="#4f46e5"
                fillOpacity={0.6}
                dot={{ fill: '#4f46e5', r: 5 }}
                activeDot={{ r: 7, fillOpacity: 1 }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#fff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '0.5rem',
                  padding: '8px 12px',
                  fontSize: '12px',
                }}
                formatter={(value) => `${value}%`}
                labelStyle={{ color: '#1e293b', fontWeight: 600 }}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* Metrics breakdown */}
        <div className="grid grid-cols-3 gap-3">
          <MetricCard
            label="Attendance"
            value={displayMetrics.attendanceRate}
            icon="📋"
          />
          <MetricCard
            label="Engagement"
            value={displayMetrics.curriculumEngagement}
            icon="📚"
          />
          <MetricCard
            label="Safety"
            value={displayMetrics.safetyScore}
            icon="🛡️"
            helper={`Risk: ${displayMetrics.riskScore}%`}
          />
        </div>

        {/* Last updated */}
        <div className="mt-4 text-xs text-slate-600">
          Last updated:{' '}
          {new Date(displayMetrics.lastUpdated).toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          })}
        </div>

        {/* Error state */}
        {error && !mockMode && (
          <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-4 w-4 flex-shrink-0 text-amber-600 mt-0.5" />
              <div className="text-xs text-amber-700">
                Could not load live metrics. Showing recent data.
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

/**
 * Individual metric card
 */
interface MetricCardProps {
  label: string;
  value: number;
  icon: string;
  helper?: string;
}

const MetricCard: React.FC<MetricCardProps> = ({ label, value, icon, helper }) => {
  const getValueColor = (val: number) => {
    if (val >= 80) return 'text-green-600';
    if (val >= 50) return 'text-amber-600';
    return 'text-red-600';
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 text-center">
      <p className="text-2xl">{icon}</p>
      <p className="mt-1 text-xs font-semibold uppercase tracking-widest text-slate-600">
        {label}
      </p>
      <p className={cn('mt-1 text-2xl font-bold', getValueColor(value))}>
        {value}%
      </p>
      {helper && <p className="mt-1 text-xs font-medium text-slate-500">{helper}</p>}
    </div>
  );
};
