import React, { useState, useRef } from 'react';
import { Upload, FileAudio, ShieldCheck, Loader2, CheckCircle2, AlertCircle, Trash2 } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Button } from '@/shared/ui/Button';
import { toast } from 'sonner';
import type { CurriculumAudioResponse } from '@/types/faculty';

interface LectureAudioUploadProps {
  sessionId: string;
  courseId: string;
  onSuccess?: (response: CurriculumAudioResponse) => void;
}

export const LectureAudioUpload: React.FC<LectureAudioUploadProps> = ({
  sessionId,
  courseId,
  onSuccess,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (selectedFile.size > 100 * 1024 * 1024) {
        toast.error('File too large', { description: 'Lecture audio must be under 100MB.' });
        return;
      }
      setFile(selectedFile);
    }
  };

  const handleUpload = async () => {
    if (!file || !sessionId || !courseId) return;

    setIsUploading(true);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append('audio', file);

    try {
      // Note: Backend expects session_id and course_id as query params or path params
      // Based on my implementation: /api/curriculum/sessions/{session_id}/process-audio?course_id={course_id}
      const response = await apiClient.post<CurriculumAudioResponse>(
        `/curriculum/sessions/${sessionId}/process-audio?course_id=${courseId}`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total ?? 1));
            setUploadProgress(percentCompleted);
          },
        }
      );

      toast.success('Audio uploaded successfully', {
        description: 'Local-LLM curriculum pipeline started.',
      });
      
      setFile(null);
      if (onSuccess) onSuccess(response.data);
    } catch (error: any) {
      toast.error('Upload failed', {
        description: error.response?.data?.detail || error.message || 'Check connection to campus network.',
      });
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center gap-3 mb-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
          <Upload className="h-5 w-5" />
        </div>
        <div>
          <h3 className="text-lg font-bold text-slate-900">Process Lecture Recording</h3>
          <p className="text-sm text-slate-500">Sync physical teaching with the digital curriculum graph.</p>
        </div>
      </div>

      {!file ? (
        <div 
          onClick={() => fileInputRef.current?.click()}
          className="group relative cursor-pointer rounded-2xl border-2 border-dashed border-slate-200 p-10 transition-all hover:border-indigo-400 hover:bg-indigo-50/30"
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept="audio/*"
            className="hidden"
          />
          <div className="flex flex-col items-center justify-center text-center">
            <div className="mb-4 rounded-full bg-slate-50 p-4 group-hover:bg-white transition-colors">
              <FileAudio className="h-10 w-10 text-slate-400 group-hover:text-indigo-500" />
            </div>
            <p className="text-sm font-semibold text-slate-900">Click to upload lecture audio</p>
            <p className="mt-1 text-xs text-slate-500">WAV, MP3, or M4A (Max 100MB)</p>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white shadow-sm">
                <FileAudio className="h-5 w-5 text-indigo-600" />
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-slate-900">{file.name}</p>
                <p className="text-xs text-slate-500">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
              </div>
            </div>
            {!isUploading && (
              <button 
                onClick={() => setFile(null)}
                className="rounded-lg p-2 text-slate-400 hover:bg-white hover:text-red-500 transition-all"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
          </div>

          {isUploading && (
            <div className="mt-4 space-y-2">
              <div className="flex justify-between text-xs font-bold text-indigo-600 uppercase">
                <span>Uploading...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="h-2 w-full rounded-full bg-slate-200 overflow-hidden">
                <div 
                  className="h-full bg-indigo-600 transition-all duration-300" 
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {!isUploading && (
            <div className="mt-6 flex gap-2">
              <Button 
                onClick={handleUpload} 
                className="w-full bg-indigo-600 hover:bg-indigo-700"
              >
                Start Processing
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Privacy Guarantee Block */}
      <div className="mt-6 flex items-start gap-3 rounded-xl border border-emerald-100 bg-emerald-50/50 p-4">
        <ShieldCheck className="mt-0.5 h-5 w-5 flex-shrink-0 text-emerald-600" />
        <div>
          <p className="text-xs font-bold text-emerald-800 uppercase tracking-widest">Privacy Guarantee</p>
          <p className="mt-1 text-xs leading-relaxed text-emerald-700">
            This audio is processed <strong>locally via Ollama/MinIO</strong> and never leaves the campus boundary.
            No cloud APIs are used. Raw audio is ephemerally stored and deleted after transcription.
          </p>
        </div>
      </div>
    </div>
  );
};
