import React from 'react';
import { 
  Users, 
  Activity,
  BadgeCheck,
  AlertTriangle,
  ShieldCheck,
  Map as MapIcon,
  Database,
  Server,
  ChevronRight
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { Button } from '@/shared/ui/Button';
import { useNavigate } from 'react-router-dom';
import { getRolePath } from '@/shared/roleShell';

export const AdminDashboardPage = () => {
  const user = useAuthStore((state) => state.user);
  const navigate = useNavigate();

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700 pb-12">
      <div className="relative rounded-[2.5rem] bg-indigo-600 p-10 overflow-hidden shadow-2xl shadow-indigo-100">
        <div className="absolute top-0 right-0 w-[40%] h-full bg-gradient-to-l from-white/10 to-transparent pointer-events-none" />
        <div className="relative z-10 max-w-3xl space-y-4">
          <span className="px-4 py-1.5 bg-white/20 backdrop-blur-md rounded-full text-[10px] font-bold text-white uppercase tracking-[0.2em]">
            Privileged Workspace
          </span>
          <h1 className="text-4xl sm:text-5xl font-bold text-white tracking-tight leading-tight">
            Welcome back, {user?.name?.split(' ')[0] ?? 'Admin'}.
          </h1>
          <p className="text-indigo-100 text-lg max-w-xl font-medium opacity-90">
            Platform attendance signal is <span className="text-white font-bold underline decoration-emerald-400 underline-offset-4">stable</span>. 
            All zero-trust gates are currently processing requests within target latency.
          </p>
          <div className="flex gap-3 pt-4">
            <Button
              onClick={() => navigate(getRolePath('admin', 'geofences'))}
              className="rounded-2xl px-6 h-12 font-bold shadow-xl bg-white/10 backdrop-blur-md text-white border-2 border-white hover:bg-blue-600 hover:border-blue-600 transition-all"
            >
               Manage Campus Map
            </Button>
            <Button
              onClick={() => navigate(getRolePath('admin', 'audit-logs'))}
              className="rounded-2xl px-6 h-12 font-bold shadow-xl bg-white/10 backdrop-blur-md text-white border-2 border-white hover:bg-blue-600 hover:border-blue-600 transition-all"
            >
               View Security Logs
            </Button>
          </div>
        </div>
        
        {/* Abstract shapes */}
        <div className="absolute -right-20 -bottom-20 w-80 h-80 bg-white/5 rounded-full blur-3xl" />
        <div className="absolute right-20 top-10 w-40 h-40 bg-indigo-400/20 rounded-full blur-2xl" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard 
          label="Total Students" 
          value="1,284" 
          change="+12" 
          icon={Users} 
          color="indigo" 
        />
        <MetricCard 
          label="Avg. Attendance" 
          value="94.2%" 
          change="+2.4%" 
          icon={BadgeCheck} 
          color="emerald" 
        />
        <MetricCard 
          label="Active Sessions" 
          value="42" 
          change="Live" 
          icon={Activity} 
          color="amber" 
        />
        <MetricCard 
          label="Anomalies" 
          value="3" 
          change="-2" 
          icon={AlertTriangle} 
          color="rose" 
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 bg-white rounded-[2.5rem] border border-slate-200 p-8 shadow-sm">
          <div className="flex items-center justify-between mb-8">
            <div>
               <h3 className="text-lg font-bold text-slate-900">System Infrastructure</h3>
               <p className="text-sm text-slate-500 font-medium">Real-time status of critical services</p>
            </div>
            <Button variant="outline" size="sm" className="rounded-xl">Detailed View</Button>
          </div>
          
          <div className="space-y-4">
             <InfrastructureItem 
              name="Identity Enclave" 
              status="Healthy" 
              icon={ShieldCheck} 
              uptime="99.99%" 
              latency="42ms"
             />
             <InfrastructureItem 
              name="Spatial Verification" 
              status="Healthy" 
              icon={MapIcon} 
              uptime="99.95%" 
              latency="118ms"
             />
             <InfrastructureItem 
              name="Audit Ledger" 
              status="Healthy" 
              icon={Database} 
              uptime="100%" 
              latency="12ms"
             />
             <InfrastructureItem 
              name="Edge API Surface" 
              status="Congested" 
              icon={Server} 
              uptime="99.98%" 
              latency="450ms"
             />
          </div>
        </div>

        <div className="bg-white rounded-[2.5rem] border border-slate-200 p-8 shadow-sm flex flex-col">
          <h3 className="text-lg font-bold text-slate-900 mb-6">Recent Security Events</h3>
          <div className="space-y-6 flex-1">
             <SecurityEvent 
              event="New Faculty Role Assigned" 
              time="4m ago" 
              user="Sarah Chen"
              type="info"
             />
             <SecurityEvent 
              event="Geofence Override Request" 
              time="12m ago" 
              user="Michael Ross"
              type="warning"
             />
             <SecurityEvent 
              event="System Config Updated" 
              time="1h ago" 
              user="System Admin"
              type="info"
             />
             <SecurityEvent 
              event="Suspicious Login Attempt" 
              time="2h ago" 
              user="Unknown"
              type="critical"
             />
          </div>
          <Button 
            onClick={() => navigate(getRolePath('admin', 'audit-logs'))}
            variant="ghost" 
            className="w-full mt-6 text-indigo-600 font-bold hover:bg-indigo-50 rounded-2xl"
          >
             Open Audit Surface
          </Button>
        </div>
      </div>
    </div>
  );
};

const MetricCard = ({ label, value, change, icon: Icon, color }: any) => {
  const colorMap: any = {
    indigo: 'bg-indigo-50 text-indigo-600',
    emerald: 'bg-emerald-50 text-emerald-600',
    amber: 'bg-amber-50 text-amber-600',
    rose: 'bg-rose-50 text-rose-600',
  };

  return (
    <div className="bg-white p-6 rounded-[2rem] border border-slate-200 shadow-sm group hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-4">
        <div className={`p-3 rounded-2xl ${colorMap[color]}`}>
           <Icon className="w-6 h-6" />
        </div>
        <span className={`text-xs font-bold px-2 py-1 rounded-lg ${change.includes('+') ? 'bg-emerald-50 text-emerald-600' : change.includes('-') ? 'bg-rose-50 text-rose-600' : 'bg-slate-100 text-slate-600'}`}>
          {change}
        </span>
      </div>
      <p className="text-sm font-bold text-slate-400 uppercase tracking-widest">{label}</p>
      <p className="text-3xl font-bold text-slate-900 mt-1">{value}</p>
    </div>
  );
};

const InfrastructureItem = ({ name, status, icon: Icon, uptime, latency }: any) => (
  <div className="flex items-center justify-between p-4 bg-slate-50 rounded-2xl border border-slate-100 group hover:bg-white hover:border-indigo-100 transition-all">
    <div className="flex items-center gap-4">
       <div className="p-2.5 bg-white rounded-xl shadow-sm group-hover:bg-indigo-50 transition-colors">
          <Icon className="w-5 h-5 text-indigo-600" />
       </div>
       <div>
          <p className="text-sm font-bold text-slate-900">{name}</p>
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{uptime} Uptime</p>
       </div>
    </div>
    <div className="text-right">
       <p className={`text-xs font-bold ${status === 'Healthy' ? 'text-emerald-500' : 'text-amber-500'}`}>{status}</p>
       <p className="text-[10px] font-mono text-slate-400">{latency}</p>
    </div>
  </div>
);

const SecurityEvent = ({ event, time, user, type }: any) => {
  const typeColors: any = {
    info: 'bg-indigo-500',
    warning: 'bg-amber-500',
    critical: 'bg-rose-500',
  };

  return (
    <div className="flex gap-4 group">
       <div className="relative">
          <div className={`w-2.5 h-2.5 rounded-full ${typeColors[type]} mt-1.5`} />
          <div className="absolute top-4 bottom-[-24px] left-1 w-px bg-slate-100 group-last:hidden" />
       </div>
       <div>
          <p className="text-sm font-bold text-slate-900 leading-none">{event}</p>
          <p className="text-xs text-slate-500 mt-1.5 font-medium">
             <span className="text-indigo-600 font-bold">{user}</span> • {time}
          </p>
       </div>
    </div>
  );
};