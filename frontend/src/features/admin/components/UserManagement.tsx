import React, { useState, useMemo } from 'react';
import { 
  Users, 
  Search, 
  Filter, 
  MoreVertical, 
  ShieldAlert, 
  Key, 
  UserPlus,
  ArrowUpDown,
  Mail,
  Calendar
} from 'lucide-react';
import { Button } from '@/shared/ui/Button';
import { toast } from 'sonner';

type UserRole = 'student' | 'faculty' | 'admin';

interface AdminUser {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  status: 'active' | 'suspended' | 'pending';
  lastSeen: string;
  joinDate: string;
}

// Generate Mock Data
const generateMockUsers = (): AdminUser[] => {
  const faculty: AdminUser[] = Array.from({ length: 10 }).map((_, i) => ({
    id: `fac-${i}`,
    name: `Dr. ${['Sarah Chen', 'Michael Ross', 'Elena Gilbert', 'James Wilson', 'Anita Desai', 'Robert Langdon', 'Maria Garcia', 'Thomas Muller', 'Linda Park', 'David Miller'][i]}`,
    email: `faculty.${i}@scholarlab.edu`,
    role: 'faculty',
    status: 'active',
    lastSeen: '10 mins ago',
    joinDate: '2023-09-15',
  }));

  const students: AdminUser[] = Array.from({ length: 50 }).map((_, i) => ({
    id: `stu-${i}`,
    name: `Student ${i + 1}`,
    email: `student.${i + 1}@scholarlab.edu`,
    role: 'student',
    status: i % 15 === 0 ? 'suspended' : 'active',
    lastSeen: `${Math.floor(Math.random() * 60)} mins ago`,
    joinDate: '2024-01-10',
  }));

  return [...faculty, ...students];
};

const ROLE_COLORS: Record<UserRole, string> = {
  admin: 'bg-slate-900 text-white',
  faculty: 'bg-indigo-100 text-indigo-700 border-indigo-200',
  student: 'bg-emerald-100 text-emerald-700 border-emerald-200',
};

export const UserManagement = () => {
  const [users, setUsers] = useState<AdminUser[]>(generateMockUsers());
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<UserRole | 'all'>('all');

  const filteredUsers = useMemo(() => {
    return users.filter((u) => {
      const matchesSearch = u.name.toLowerCase().includes(search.toLowerCase()) || 
                            u.email.toLowerCase().includes(search.toLowerCase());
      const matchesRole = roleFilter === 'all' || u.role === roleFilter;
      return matchesSearch && matchesRole;
    });
  }, [users, search, roleFilter]);

  const handleResetPassword = (email: string) => {
    toast.success(`Password reset link sent to ${email}`);
  };

  const handleChangeRole = (id: string, newRole: UserRole) => {
    setUsers((prev) => prev.map((u) => u.id === id ? { ...u, role: newRole } : u));
    toast.success('User role updated successfully');
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900">User Directory</h2>
          <p className="text-slate-500 text-sm">Manage access control and identity for the entire campus.</p>
        </div>
        <Button className="rounded-2xl shadow-lg shadow-indigo-100">
          <UserPlus className="w-4 h-4 mr-2" /> Invite Member
        </Button>
      </div>

      <div className="bg-white rounded-[2.5rem] border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-slate-100 flex flex-col sm:flex-row gap-4 items-center">
          <div className="relative flex-1 w-full">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by name or email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-11 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
            />
          </div>
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <div className="flex bg-slate-100 p-1 rounded-2xl">
              {(['all', 'admin', 'faculty', 'student'] as const).map((r) => (
                <button
                  key={r}
                  onClick={() => setRoleFilter(r)}
                  className={`px-4 py-1.5 rounded-xl text-xs font-semibold capitalize transition-all ${
                    roleFilter === r ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>
            <Button variant="outline" className="rounded-2xl h-11 px-4">
              <Filter className="w-4 h-4" />
            </Button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/50">
                <th className="px-6 py-4 text-xs font-bold uppercase tracking-widest text-slate-400 border-b border-slate-100">
                  <div className="flex items-center gap-2">User <ArrowUpDown className="w-3 h-3" /></div>
                </th>
                <th className="px-6 py-4 text-xs font-bold uppercase tracking-widest text-slate-400 border-b border-slate-100">Role</th>
                <th className="px-6 py-4 text-xs font-bold uppercase tracking-widest text-slate-400 border-b border-slate-100">Status</th>
                <th className="px-6 py-4 text-xs font-bold uppercase tracking-widest text-slate-400 border-b border-slate-100">Activity</th>
                <th className="px-6 py-4 text-xs font-bold uppercase tracking-widest text-slate-400 border-b border-slate-100 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {filteredUsers.map((user) => (
                <tr key={user.id} className="group hover:bg-slate-50/50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-indigo-500 to-slate-400 flex items-center justify-center text-white font-bold shadow-sm">
                        {user.name.charAt(0)}
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-slate-900">{user.name}</p>
                        <div className="flex items-center gap-1.5 text-xs text-slate-500 mt-0.5">
                          <Mail className="w-3 h-3" /> {user.email}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${ROLE_COLORS[user.role]}`}>
                      {user.role}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <div className={`w-1.5 h-1.5 rounded-full ${user.status === 'active' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-red-500'}`} />
                      <span className="text-xs font-medium text-slate-600 capitalize">{user.status}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-col gap-1">
                      <p className="text-xs text-slate-600 font-medium">Seen {user.lastSeen}</p>
                      <div className="flex items-center gap-1 text-[10px] text-slate-400">
                        <Calendar className="w-3 h-3" /> Joined {user.joinDate}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="inline-flex items-center gap-2">
                      <button 
                        onClick={() => handleResetPassword(user.email)}
                        className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-all"
                        title="Reset Password"
                      >
                        <Key className="w-4 h-4" />
                      </button>
                      <button 
                         onClick={() => handleChangeRole(user.id, user.role === 'student' ? 'faculty' : 'student')}
                         className="p-2 text-slate-400 hover:text-amber-600 hover:bg-amber-50 rounded-xl transition-all"
                         title="Elevate/Downgrade"
                      >
                        <ShieldAlert className="w-4 h-4" />
                      </button>
                      <button className="p-2 text-slate-400 hover:text-slate-900 hover:bg-slate-100 rounded-xl transition-all">
                        <MoreVertical className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        <div className="p-6 bg-slate-50/50 border-t border-slate-100 flex items-center justify-between">
          <p className="text-xs text-slate-500">Showing {filteredUsers.length} of {users.length} users</p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" className="rounded-xl" disabled>Previous</Button>
            <Button variant="outline" size="sm" className="rounded-xl">Next</Button>
          </div>
        </div>
      </div>
    </div>
  );
};
