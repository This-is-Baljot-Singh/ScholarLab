import React, { useState, useEffect, useRef } from 'react';
import { 
  Terminal, 
  ShieldCheck, 
  AlertCircle, 
  Lock, 
  Download,
  Trash2,
  Database,
  Cpu,
  RefreshCw
} from 'lucide-react';
import { Button } from '@/shared/ui/Button';

interface AuditLog {
  id: string;
  timestamp: string;
  level: 'INFO' | 'WARN' | 'CRITICAL' | 'SECURITY';
  service: string;
  event: string;
  payload: string;
}

const INITIAL_LOGS: AuditLog[] = [
  { id: '1', timestamp: '2024-05-06 05:40:12.443', level: 'INFO', service: 'AUTH-SVC', event: 'JWT_ISSUE_SUCCESS', payload: 'user_id: adm-001, scope: system_admin' },
  { id: '2', timestamp: '2024-05-06 05:40:15.102', level: 'SECURITY', service: 'GEO-VAL', event: 'FENCE_OVERRIDE_AUTH', payload: 'actor: faculty-004, target: session-202' },
  { id: '3', timestamp: '2024-05-06 05:41:02.887', level: 'WARN', service: 'BIO-MET', event: 'LIVENESS_REJECT', payload: 'confidence: 0.22, client_ip: 192.168.1.45' },
  { id: '4', timestamp: '2024-05-06 05:41:30.551', level: 'CRITICAL', service: 'DB-ENCLAVE', event: 'TAMPER_CHECK_PASS', payload: 'merkle_root: 0x77ab...ef01, depth: 12' },
  { id: '5', timestamp: '2024-05-06 05:42:05.112', level: 'INFO', service: 'CORE-API', event: 'RBAC_UPDATE', payload: 'target: user-102, old_role: student, new_role: faculty' },
];

const LOG_LEVEL_COLORS = {
  INFO: 'text-emerald-400',
  WARN: 'text-amber-400',
  CRITICAL: 'text-rose-500 font-bold',
  SECURITY: 'text-indigo-400',
};

export const AuditLogViewer = () => {
  const [logs, setLogs] = useState<AuditLog[]>(INITIAL_LOGS);
  const [isLive, setIsLive] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isLive) {
      const interval = setInterval(() => {
        const newLog: AuditLog = {
          id: Date.now().toString(),
          timestamp: new Date().toISOString().replace('T', ' ').slice(0, 23),
          level: Math.random() > 0.8 ? (Math.random() > 0.5 ? 'SECURITY' : 'WARN') : 'INFO',
          service: ['AUTH-SVC', 'GEO-VAL', 'BIO-MET', 'CORE-API', 'ANALYTICS'][Math.floor(Math.random() * 5)],
          event: ['ACCESS_GRANTED', 'FENCE_ENTRY', 'WEBAUTHN_VERIFY', 'HEARTBEAT_PULSE', 'ENCLAVE_SYNC'][Math.floor(Math.random() * 5)],
          payload: `trace_id: 0x${Math.random().toString(16).slice(2, 10)}, status: 200 OK`,
        };
        setLogs((prev) => [...prev.slice(-49), newLog]);
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [isLive]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] gap-4 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-slate-900 rounded-xl shadow-lg">
            <Terminal className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">Immutable Audit Trail</h2>
            <p className="text-xs text-slate-500 font-medium">Secured by Cryptographic Hashing (SHA-256)</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
           <Button 
            variant="outline" 
            size="sm" 
            className={`rounded-xl border-slate-200 transition-all ${isLive ? 'bg-emerald-50 text-emerald-600 border-emerald-100' : ''}`}
            onClick={() => setIsLive(!isLive)}
           >
            <RefreshCw className={`w-3.5 h-3.5 mr-2 ${isLive ? 'animate-spin' : ''}`} />
            {isLive ? 'Live Stream' : 'Paused'}
          </Button>
          <Button variant="outline" size="sm" className="rounded-xl border-slate-200">
            <Download className="w-3.5 h-3.5 mr-2" /> Export JSON
          </Button>
          <Button variant="outline" size="sm" className="rounded-xl border-slate-200 text-rose-500 hover:bg-rose-50">
            <Trash2 className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>

      <div className="flex-1 bg-slate-950 rounded-[2rem] border border-slate-800 shadow-2xl flex flex-col overflow-hidden relative">
        {/* Terminal Header */}
        <div className="px-6 py-3 bg-slate-900/50 border-b border-slate-800 flex items-center justify-between">
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-rose-500/80" />
            <div className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
          </div>
          <div className="flex items-center gap-4 text-[10px] font-mono text-slate-500 uppercase tracking-widest">
            <span className="flex items-center gap-1"><Cpu className="w-3 h-3" /> System: Stable</span>
            <span className="flex items-center gap-1"><Database className="w-3 h-3" /> Storage: 12.4GB / 500GB</span>
            <span className="flex items-center gap-1 text-indigo-400 font-bold"><Lock className="w-3 h-3" /> Encrypted</span>
          </div>
        </div>

        {/* Terminal Content */}
        <div 
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-6 font-mono text-sm space-y-1.5 custom-scrollbar"
        >
          {logs.map((log) => (
            <div key={log.id} className="flex gap-3 group">
              <span className="text-slate-600 select-none whitespace-nowrap">[{log.timestamp}]</span>
              <span className={`w-20 inline-block uppercase font-bold text-xs select-none ${LOG_LEVEL_COLORS[log.level]}`}>
                {log.level}
              </span>
              <span className="text-indigo-400 select-none">{log.service}:</span>
              <span className="text-slate-300">
                <span className="font-bold text-slate-100">{log.event}</span>
                <span className="text-slate-500 ml-3 group-hover:text-slate-400 transition-colors">{log.payload}</span>
              </span>
            </div>
          ))}
          <div className="flex items-center gap-2 text-indigo-500 animate-pulse mt-2">
            <span className="w-2 h-4 bg-indigo-500" />
            <span className="text-xs uppercase tracking-tighter font-bold">Waiting for system signals...</span>
          </div>
        </div>

        {/* Technical Sidebar Overlays */}
        <div className="absolute right-6 top-16 bottom-6 w-48 pointer-events-none opacity-20 hidden lg:flex flex-col justify-between py-4 border-l border-slate-800 pl-4">
           <div className="space-y-4">
              <div className="space-y-1">
                 <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Auth Success Rate</p>
                 <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-500 w-[98%]" />
                 </div>
              </div>
              <div className="space-y-1">
                 <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Geo Validation</p>
                 <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-indigo-500 w-[94%]" />
                 </div>
              </div>
           </div>
           <div className="space-y-2">
              <div className="flex items-center gap-2 text-emerald-400 text-[10px] font-bold">
                 <ShieldCheck className="w-3 h-3" /> INTEGRITY_OK
              </div>
              <div className="flex items-center gap-2 text-amber-400 text-[10px] font-bold">
                 <AlertCircle className="w-3 h-3" /> NO_LEAKS_DET
              </div>
           </div>
        </div>
      </div>
      
      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: #020617;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #1e293b;
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #334155;
        }
      `}</style>
    </div>
  );
};
