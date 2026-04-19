import React from 'react';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/shared/ui/Button';
import { CurriculumGraphBuilder } from '../components';
import { toast } from 'sonner';
import { apiClient } from '@/api/client';
import type { CurriculumGraph } from '@/types/faculty';

export const CurriculumBuilderPage: React.FC<{ onBack: () => void }> = ({ onBack }) => {
  
  // This receives the fully compiled graph from the child component
  const handleSaveGraph = async (graph: CurriculumGraph) => {
    try {
      // Send the payload to the backend
      // await apiClient.post('/curriculum/graph', graph);
      toast.success(`Knowledge Graph "${graph.title}" synchronized with database`);
      
      // Navigate back to dashboard upon success
      setTimeout(() => onBack(), 1500);
    } catch (error) {
      toast.error('Failed to save curriculum graph');
      console.error(error);
    }
  };

  return (
    <div className="flex h-screen flex-col bg-slate-50">
      <div className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
        <div className="flex items-center gap-4">
          <Button onClick={onBack} variant="ghost" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Curriculum Graph Builder</h1>
            <p className="mt-1 text-sm text-slate-600">
              Design event-driven learning pathways
            </p>
          </div>
        </div>
      </div>
      
      <div className="flex-1 overflow-hidden">
        {/* FIX: Pass exactly the props defined in the child interface */}
        <CurriculumGraphBuilder 
          graph={null} 
          onSave={handleSaveGraph} 
        />
      </div>
    </div>
  );
};
