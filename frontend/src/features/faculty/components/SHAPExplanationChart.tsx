import React, { useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip,
  ResponsiveContainer, Cell
} from 'recharts';
import { AlertTriangle, CheckCircle2 } from 'lucide-react';

interface SHAPExplanation {
  feature: string;
  value: number;
  shap_impact: number;
  human_readable: string;
}

interface SHAPExplanationChartProps {
  explanations: SHAPExplanation[];
  riskProbability?: number;
}

export const SHAPExplanationChart: React.FC<SHAPExplanationChartProps> = ({
  explanations,
  riskProbability = 0
}) => {
  // Transform SHAP values for horizontal bar chart
  // Negative values push risk lower (green), positive values push risk higher (red)
  const chartData = useMemo(() => {
    return explanations
      .sort((a, b) => Math.abs(b.shap_impact) - Math.abs(a.shap_impact))
      .map((exp) => ({
        feature: exp.feature.replace(/_/g, ' ').toUpperCase(),
        impact: Math.abs(exp.shap_impact),
        rawImpact: exp.shap_impact, // Preserve sign for color coding
        value: exp.value,
        explanation: exp.human_readable,
      }));
  }, [explanations]);

  const getBarColor = (rawImpact: number) => {
    // Red: increases risk (positive), Green: decreases risk (negative)
    return rawImpact > 0 ? '#ef4444' : '#10b981';
  };

  return (
    <div className="space-y-6">
      {/* Risk Probability Indicator */}
      <div className="rounded-lg border border-slate-200 bg-gradient-to-r from-slate-50 to-white p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-600">Overall Risk Probability</p>
            <p className="text-2xl font-bold text-slate-900">
              {(riskProbability * 100).toFixed(1)}%
            </p>
          </div>
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-white shadow-sm">
            {riskProbability > 0.5 ? (
              <AlertTriangle className="h-8 w-8 text-red-600" />
            ) : (
              <CheckCircle2 className="h-8 w-8 text-emerald-600" />
            )}
          </div>
        </div>
      </div>

      {/* SHAP Feature Impact Chart */}
      <div className="rounded-lg border border-slate-200 bg-white p-6">
        <h4 className="mb-2 text-lg font-semibold text-slate-800">Feature Impact on Risk Score</h4>
        <p className="mb-4 text-sm text-slate-600">
          <span className="inline-block mr-4">
            <span className="inline-block h-3 w-3 rounded-sm bg-red-500 mr-2"></span>
            <span>Increases Risk</span>
          </span>
          <span className="inline-block">
            <span className="inline-block h-3 w-3 rounded-sm bg-emerald-500 mr-2"></span>
            <span>Decreases Risk</span>
          </span>
        </p>

        {chartData.length === 0 ? (
          <div className="flex h-[200px] items-center justify-center text-slate-500">
            No feature impact data available
          </div>
        ) : (
          <div className="h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                layout="vertical"
                margin={{ top: 5, right: 30, left: 150, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" tick={{ fontSize: 12 }} />
                <YAxis
                  dataKey="feature"
                  type="category"
                  tick={{ fontSize: 11 }}
                  width={140}
                />
                <RechartsTooltip
                  contentStyle={{
                    backgroundColor: '#f8fafc',
                    border: '1px solid #e2e8f0',
                    borderRadius: '0.5rem'
                  }}
                  formatter={(value: any) => {
                    if (typeof value === 'number') {
                      return [value.toFixed(4), 'Absolute Impact'];
                    }
                    return value;
                  }}
                  labelFormatter={(label) => `${label}`}
                />
                <Bar dataKey="impact" radius={[0, 8, 8, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={getBarColor(entry.rawImpact)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Detailed Explanations */}
        <div className="mt-6 space-y-3 border-t border-slate-200 pt-4">
          <p className="text-sm font-semibold text-slate-700">Detailed Explanations</p>
          {chartData.map((item, idx) => (
            <div
              key={idx}
              className="flex items-start gap-3 rounded-lg bg-slate-50 p-3 text-sm"
            >
              <div
                className={`mt-0.5 h-2 w-2 rounded-full flex-shrink-0 ${
                  item.rawImpact > 0 ? 'bg-red-500' : 'bg-emerald-500'
                }`}
              />
              <div>
                <p className="font-medium text-slate-800">
                  {item.feature} = {item.value.toFixed(2)}
                </p>
                <p className="text-xs text-slate-600 mt-1">{item.explanation}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
