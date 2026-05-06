import { useEffect, useRef, useState } from 'react';
import {
  CheckCircle2,
  Download,
  FileText,
  Link as LinkIcon,
  Loader2,
  PlayCircle,
  Sparkles,
  X,
} from 'lucide-react';
import { Button } from '@/shared/ui/Button';

interface UnlockedResourcesModalProps {
  isOpen: boolean;
  onClose: () => void;
  variant?: 'sheet' | 'page';
}

type ResourceType = 'pdf' | 'video' | 'link';
type DownloadState = 'idle' | 'loading' | 'downloaded';

interface VaultResource {
  id: string;
  title: string;
  type: ResourceType;
  description: string;
  meta: string;
  isNew?: boolean;
}

const CS101_RESOURCES: VaultResource[] = [
  {
    id: 'cs101-week4-slides',
    title: 'CS101 Week 4 Lecture Slides',
    type: 'pdf',
    description: 'Control flow patterns, branching practice, and annotated examples.',
    meta: 'PDF · 3.2 MB',
    isNew: true,
  },
  {
    id: 'cs101-week4-recording',
    title: 'CS101 Week 4 Classroom Recording',
    type: 'video',
    description: 'Full in-class walkthrough with live debugging and Q&A recap.',
    meta: 'Video · 42 min',
    isNew: true,
  },
  {
    id: 'cs101-assignment4',
    title: 'CS101 Assignment 4 Brief',
    type: 'link',
    description: 'Problem set specification and submission rubric for Module 4.',
    meta: 'Link · Due Friday',
  },
  {
    id: 'cs101-lab-sheet4',
    title: 'CS101 Lab Sheet: Iteration Drills',
    type: 'pdf',
    description: 'Hands-on worksheet to master loops, ranges, and loop invariants.',
    meta: 'PDF · 1.1 MB',
  },
  {
    id: 'cs101-office-hours',
    title: 'CS101 Office Hour Solutions',
    type: 'video',
    description: 'Instructor-led solution discussion from this week office hours.',
    meta: 'Video · 18 min',
  },
];

const getResourceAccent = (type: ResourceType) => {
  switch (type) {
    case 'pdf':
      return {
        badge: 'bg-red-50 text-red-700 border-red-200',
        iconClass: 'text-red-600',
        label: 'Slides',
      };
    case 'video':
      return {
        badge: 'bg-violet-50 text-violet-700 border-violet-200',
        iconClass: 'text-violet-600',
        label: 'Recording',
      };
    default:
      return {
        badge: 'bg-cyan-50 text-cyan-700 border-cyan-200',
        iconClass: 'text-cyan-600',
        label: 'Assignment',
      };
  }
};

const getResourceIcon = (type: ResourceType) => {
  if (type === 'pdf') return FileText;
  if (type === 'video') return PlayCircle;
  return LinkIcon;
};

const UnlockedResourcesContent = ({
  isOpen,
  onClose,
  variant = 'sheet',
}: {
  isOpen: boolean;
  onClose: () => void;
  variant?: 'sheet' | 'page';
}) => {
  const [downloadStates, setDownloadStates] = useState<Record<string, DownloadState>>({});
  const timersRef = useRef<number[]>([]);

  const clearTimers = () => {
    timersRef.current.forEach((id) => window.clearTimeout(id));
    timersRef.current = [];
  };

  useEffect(() => {
    return () => {
      clearTimers();
    };
  }, []);

  useEffect(() => {
    if (!isOpen) {
      clearTimers();
      setDownloadStates({});
    }
  }, [isOpen]);

  const handleDownload = (resourceId: string) => {
    const currentState = downloadStates[resourceId] ?? 'idle';
    if (currentState !== 'idle') {
      return;
    }

    setDownloadStates((prev) => ({ ...prev, [resourceId]: 'loading' }));

    const loadingTimer = window.setTimeout(() => {
      setDownloadStates((prev) => ({ ...prev, [resourceId]: 'downloaded' }));

      const resetTimer = window.setTimeout(() => {
        setDownloadStates((prev) => ({ ...prev, [resourceId]: 'idle' }));
      }, 1200);

      timersRef.current.push(resetTimer);
    }, 1000);

    timersRef.current.push(loadingTimer);
  };

  return (
    <>
      <header className={variant === 'page' ? 'border-b border-slate-200 bg-white px-6 py-4' : 'sticky top-0 z-10 border-b border-slate-200 bg-white/95 px-6 py-4 backdrop-blur'}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Unlocked Resources</p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-900">CS101 Digital Vault</h2>
            <p className="mt-1 text-sm text-slate-600">Resources unlocked from your latest attendance verification.</p>
          </div>
          <button
            type="button"
            className="rounded-xl border border-slate-200 p-2 text-slate-500 transition hover:bg-slate-50"
            onClick={onClose}
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </header>

      <div className="px-6 py-6">
          <div className="grid gap-4 sm:grid-cols-2">
            {CS101_RESOURCES.map((resource) => {
              const Icon = getResourceIcon(resource.type);
              const accent = getResourceAccent(resource.type);
              const state = downloadStates[resource.id] ?? 'idle';

              return (
                <article key={resource.id} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <div className="rounded-xl border border-slate-200 bg-slate-50 p-2.5">
                        <Icon className={`h-5 w-5 ${accent.iconClass}`} />
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold text-slate-900">{resource.title}</h3>
                        <p className="mt-1 text-xs text-slate-500">{resource.meta}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${accent.badge}`}>
                        {accent.label}
                      </span>
                      {resource.isNew && (
                        <span className="inline-flex animate-pulse items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-700">
                          <Sparkles className="h-3 w-3" />
                          NEW
                        </span>
                      )}
                    </div>
                  </div>

                  <p className="mt-4 text-sm leading-6 text-slate-600">{resource.description}</p>

                  <Button
                    type="button"
                    variant={state === 'downloaded' ? 'secondary' : 'outline'}
                    className="mt-5"
                    onClick={() => handleDownload(resource.id)}
                    disabled={state === 'loading'}
                  >
                    {state === 'loading' && (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Downloading...
                      </>
                    )}
                    {state === 'downloaded' && (
                      <>
                        <CheckCircle2 className="mr-2 h-4 w-4 text-emerald-600" />
                        Downloaded
                      </>
                    )}
                    {state === 'idle' && (
                      <>
                        <Download className="mr-2 h-4 w-4" />
                        Download
                      </>
                    )}
                  </Button>
                </article>
              );
            })}
          </div>
      </div>
    </>
  );
};

export const UnlockedResourcesModal = ({ isOpen, onClose, variant = 'sheet' }: UnlockedResourcesModalProps) => {
  if (!isOpen) {
    return null;
  }

  if (variant === 'page') {
    return (
      <section className="overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-sm">
        <UnlockedResourcesContent isOpen={isOpen} onClose={onClose} variant={variant} />
      </section>
    );
  }

  return (
    <div className="fixed inset-0 z-50">
      <button
        type="button"
        className="absolute inset-0 bg-slate-900/40"
        onClick={onClose}
        aria-label="Close unlocked resources panel"
      />

      <aside className="absolute right-0 top-0 h-full w-full max-w-3xl overflow-y-auto border-l border-slate-200 bg-white shadow-2xl">
        <UnlockedResourcesContent isOpen={isOpen} onClose={onClose} variant={variant} />
      </aside>
    </div>
  );
};