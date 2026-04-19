import React, { useState } from 'react';
import { TopAppBar, Sidebar } from './TopAppBar';
import { Menu } from 'lucide-react';

interface MainLayoutProps {
  children: React.ReactNode;
}

export const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen flex-col bg-slate-50">
      <TopAppBar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        <main className="flex-1 overflow-y-auto">
          <div className="container mx-auto px-4 py-8 sm:px-6 lg:px-8">
            {/* Mobile menu toggle */}
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="mb-4 inline-flex md:hidden items-center justify-center rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-100"
            >
              <Menu className="h-5 w-5" />
            </button>
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

export const AuthLayout: React.FC<MainLayoutProps> = ({ children }) => {
  return (
    <div className="flex h-screen items-center justify-center bg-gradient-to-br from-indigo-50 to-slate-100">
      <div className="w-full max-w-md">{children}</div>
    </div>
  );
};
