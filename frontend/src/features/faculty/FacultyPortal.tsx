import React, { useState } from 'react';
import {
  FacultyDashboardPage,
  GeofenceManagementPage,
  CurriculumBuilderPage,
  SessionInitializationPage,
  AnalyticsDashboardPage,
} from './pages';

type PageType = 'dashboard' | 'geofence' | 'curriculum' | 'session' | 'analytics';

/**
 * Main Faculty Portal wrapper component that manages navigation between
 * all faculty features: geofence management, curriculum builder, session control,
 * and predictive analytics dashboard.
 */
export const FacultyPortal: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<PageType>('dashboard');

  const handleNavigate = (page: PageType) => {
    setCurrentPage(page);
  };

  const renderPage = () => {
    switch (currentPage) {
      case 'geofence':
        return <GeofenceManagementPage onBack={() => handleNavigate('dashboard')} />;
      case 'curriculum':
        return <CurriculumBuilderPage onBack={() => handleNavigate('dashboard')} />;
      case 'session':
        return <SessionInitializationPage onBack={() => handleNavigate('dashboard')} />;
      case 'analytics':
        return <AnalyticsDashboardPage onBack={() => handleNavigate('dashboard')} />;
      case 'dashboard':
      default:
        return <FacultyDashboardPage onNavigate={handleNavigate} currentPage={currentPage} />;
    }
  };

  return <div className="w-full h-screen overflow-hidden">{renderPage()}</div>;
};
