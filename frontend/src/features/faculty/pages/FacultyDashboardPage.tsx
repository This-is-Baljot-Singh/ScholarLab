import React, { useState } from 'react';
import { Map, Zap, Play, BarChart3, Menu, X } from 'lucide-react';
import { Button } from '@/shared/ui/Button';

type PageType = 'dashboard' | 'geofence' | 'curriculum' | 'session' | 'analytics';

interface FacultyDashboardPageProps {
  onNavigate: (page: PageType) => void;
  currentPage: PageType;
}

export const FacultyDashboardPage: React.FC<FacultyDashboardPageProps> = ({
  onNavigate,
  currentPage,
}) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const menuItems: Array<{
    id: PageType;
    label: string;
    icon: React.ReactNode;
    description: string;
  }> = [
    {
      id: 'geofence',
      label: 'Geofence Manager',
      icon: <Map className="w-5 h-5" />,
      description: 'Create and manage campus geofences',
    },
    {
      id: 'curriculum',
      label: 'Curriculum Builder',
      icon: <Zap className="w-5 h-5" />,
      description: 'Build interactive curriculum graphs',
    },
    {
      id: 'session',
      label: 'Session Control',
      icon: <Play className="w-5 h-5" />,
      description: 'Start and manage live sessions',
    },
    {
      id: 'analytics',
      label: 'Analytics Dashboard',
      icon: <BarChart3 className="w-5 h-5" />,
      description: 'Predictive analytics & SHAP insights',
    },
  ];

  return (
    <div className="h-screen bg-slate-50 flex">
      {/* Sidebar */}
      <div
        className={`${
          sidebarOpen ? 'w-80' : 'w-20'
        } bg-white border-r border-slate-200 transition-all duration-300 flex flex-col`}
      >
        {/* Logo */}
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          {sidebarOpen && <h1 className="text-xl font-bold text-indigo-600">ScholarLab</h1>}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1 hover:bg-slate-100 rounded transition-colors"
          >
            {sidebarOpen ? (
              <X className="w-5 h-5 text-slate-600" />
            ) : (
              <Menu className="w-5 h-5 text-slate-600" />
            )}
          </button>
        </div>

        {/* Navigation */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {menuItems.map((item) => (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`w-full flex items-start gap-3 p-3 rounded-lg transition-all ${
                currentPage === item.id
                  ? 'bg-indigo-100 text-indigo-900 border border-indigo-300'
                  : 'text-slate-700 hover:bg-slate-100'
              }`}
            >
              <span className="mt-0.5 flex-shrink-0">{item.icon}</span>
              {sidebarOpen && (
                <div className="text-left">
                  <p className="font-semibold text-sm">{item.label}</p>
                  <p className="text-xs text-current opacity-75 line-clamp-1">
                    {item.description}
                  </p>
                </div>
              )}
            </button>
          ))}
        </div>

        {/* User Info */}
        {sidebarOpen && (
          <div className="border-t border-slate-200 p-4">
            <div className="bg-indigo-50 rounded-lg p-3 text-sm">
              <p className="font-semibold text-slate-900">Dr. Sarah Chen</p>
              <p className="text-xs text-slate-600 mt-0.5">Faculty Member</p>
            </div>
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Top Bar */}
        <div className="bg-white border-b border-slate-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-slate-900">Faculty Command Center</h2>
              <p className="text-slate-600 text-sm mt-1">
                Manage geofences, build curricula, and track student engagement
              </p>
            </div>
          </div>
        </div>

        {/* Dashboard View */}
        <div className="flex-1 overflow-hidden p-6">
          <div className="max-w-7xl mx-auto h-full">
            {currentPage === 'dashboard' && (
              <div className="grid grid-cols-2 gap-6 h-full">
                {/* Welcome Card */}
                <div className="col-span-2 bg-gradient-to-br from-indigo-600 to-indigo-700 rounded-lg p-6 text-white shadow-lg">
                  <h3 className="text-xl font-bold mb-2">Welcome to ScholarLab Faculty Portal</h3>
                  <p className="opacity-90">
                    Manage your courses with advanced geofencing, curriculum design, and AI-powered student analytics.
                  </p>
                </div>

                {/* Feature Cards */}
                {menuItems.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => onNavigate(item.id)}
                    className="bg-white rounded-lg border border-slate-200 p-6 text-left hover:shadow-lg transition-shadow group"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="p-3 bg-indigo-50 rounded-lg group-hover:bg-indigo-100 transition-colors text-indigo-600">
                        {item.icon}
                      </div>
                    </div>
                    <h4 className="font-semibold text-slate-900 text-lg mb-2">{item.label}</h4>
                    <p className="text-slate-600 text-sm mb-4">{item.description}</p>
                    <div className="text-indigo-600 font-semibold text-sm group-hover:translate-x-1 transition-transform">
                      Open →
                    </div>
                  </button>
                ))}

                {/* Quick Stats */}
                <div className="col-span-2 grid grid-cols-4 gap-4">
                  <div className="bg-white rounded-lg border border-slate-200 p-4">
                    <p className="text-xs font-medium text-slate-600 uppercase mb-2">Active Sessions</p>
                    <p className="text-3xl font-bold text-slate-900">3</p>
                  </div>
                  <div className="bg-white rounded-lg border border-slate-200 p-4">
                    <p className="text-xs font-medium text-slate-600 uppercase mb-2">Geofences</p>
                    <p className="text-3xl font-bold text-slate-900">8</p>
                  </div>
                  <div className="bg-white rounded-lg border border-slate-200 p-4">
                    <p className="text-xs font-medium text-slate-600 uppercase mb-2">At-Risk Students</p>
                    <p className="text-3xl font-bold text-red-600">5</p>
                  </div>
                  <div className="bg-white rounded-lg border border-slate-200 p-4">
                    <p className="text-xs font-medium text-slate-600 uppercase mb-2">Curriculum Graphs</p>
                    <p className="text-3xl font-bold text-slate-900">2</p>
                  </div>
                </div>
              </div>
            )}

            {currentPage !== 'dashboard' && (
              <div className="text-center py-12">
                <p className="text-slate-600 text-lg mb-4">
                  Navigate using the sidebar to view this section
                </p>
                <Button onClick={() => onNavigate('dashboard')}>Back to Dashboard</Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
