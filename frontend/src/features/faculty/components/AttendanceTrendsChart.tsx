import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip,
  ResponsiveContainer, Legend
} from 'recharts';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { Loader2, AlertCircle } from 'lucide-react';

interface TrendData {
  date: string;
  count: number;
}

export const AttendanceTrendsChart: React.FC = () => {
  const { data: trends, isLoading, isError } = useQuery({
    queryKey: ['attendance-trends'],
    queryFn: async () => {
      const response = await apiClient.get('/analytics/dashboard/trends');
      return response.data as TrendData[];
    },
    refetchInterval: 60000, // Refresh every minute
  });

  if (isLoading) {
    return (
      <div className="flex h-[350px] items-center justify-center rounded-xl border border-slate-200 bg-white">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (isError || !trends || trends.length === 0) {
    return (
      <div className="flex h-[350px] items-center justify-center rounded-xl border border-slate-200 bg-white">
        <div className="flex items-center gap-3 text-amber-600">
          <AlertCircle className="h-5 w-5" />
          <span className="text-sm">No attendance data available</span>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="mb-4 text-lg font-semibold text-slate-800">Attendance Trends (30 Days)</h3>
      <div style={{ display: 'block', width: '100%', height: '300px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={trends}
            margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12 }}
              tickFormatter={(date) => {
                // Format YYYY-MM-DD to MM-DD for readability
                const [, month, day] = date.split('-');
                return `${month}/${day}`;
              }}
            />
            <YAxis
              tick={{ fontSize: 12 }}
              label={{ value: 'Verified Attendances', angle: -90, position: 'insideLeft' }}
            />
            <RechartsTooltip
              contentStyle={{
                backgroundColor: '#f8fafc',
                border: '1px solid #e2e8f0',
                borderRadius: '0.5rem'
              }}
              formatter={(value) => [value, 'Count']}
              labelFormatter={(date) => `Date: ${date}`}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="count"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ fill: '#3b82f6', r: 4 }}
              activeDot={{ r: 6 }}
              name="Attended"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
