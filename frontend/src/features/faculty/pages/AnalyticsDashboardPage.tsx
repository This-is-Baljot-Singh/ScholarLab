import React from 'react';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/shared/ui/Button';
import { PredictiveAnalyticsDashboard } from '../components';

interface AnalyticsDashboardPageProps {
  onBack: () => void;
}

export const AnalyticsDashboardPage: React.FC<AnalyticsDashboardPageProps> = ({ onBack }) => {

  return (
    <div className="h-screen flex flex-col bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-6 py-4 flex items-center gap-4">
        <Button onClick={onBack} variant="ghost" size="sm">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Predictive Analytics Dashboard</h1>
          <p className="text-slate-600 text-sm mt-1">
            ML-powered student risk assessment with SHAP model explanations
          </p>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto bg-slate-50">
        <PredictiveAnalyticsDashboard />
      </div>
    </div>
  );
};
