import React from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/hooks/use-auth';
import { Role } from '@/types/auth';

// Layouts
import { AppLayout } from '@/components/layout/app-layout';
import { PublicLayout } from '@/components/layout/public-layout';

// Auth Pages
import { LoginPage } from '@/features/auth/login-page';
import { RegisterPage } from '@/features/auth/register-page';
import { ForgotPasswordPage } from '@/features/auth/forgot-password-page';
import { ResetPasswordPage } from '@/features/auth/reset-password-page';
import { UnauthorizedPage } from '@/features/auth/unauthorized-page';

// Citizen Pages
import { CitizenDashboard } from '@/features/citizen/citizen-dashboard';
import { CreateReportPage } from '@/features/citizen/create-report-page';
import { CitizenReportsPage } from '@/features/citizen/citizen-reports-page';
import { CitizenReportDetailPage } from '@/features/citizen/citizen-report-detail-page';
import { CitizenMapPage } from '@/features/citizen/citizen-map-page';
import { CitizenProfilePage } from '@/features/citizen/citizen-profile-page';

// Admin Pages
import { AdminDashboard } from '@/features/admin/admin-dashboard';
import { AdminReportsPage } from '@/features/admin/admin-reports-page';
import { AdminReportDetailPage } from '@/features/admin/admin-report-detail-page';
import { AdminMapPage } from '@/features/admin/admin-map-page';
import { AdminAssignmentsPage } from '@/features/admin/admin-assignments-page';
import { AdminDepartmentsPage } from '@/features/admin/admin-departments-page';
import { AdminUsersPage } from '@/features/admin/admin-users-page';
import { AdminAnalyticsPage } from '@/features/admin/admin-analytics-page';
import { AdminSettingsPage } from '@/features/admin/admin-settings-page';

// Worker Pages
import { WorkerDashboard } from '@/features/worker/worker-dashboard';
import { WorkerAssignmentsPage } from '@/features/worker/worker-assignments-page';
import { WorkerAssignmentDetailPage } from '@/features/worker/worker-assignment-detail-page';
import { WorkerMapPage } from '@/features/worker/worker-map-page';
import { WorkerProfilePage } from '@/features/worker/worker-profile-page';

// Shared Pages
import { NotificationsPage } from '@/features/notifications/notifications-page';

// Route Guards
const RequireAuth: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="h-screen w-screen flex flex-col items-center justify-center p-6 bg-slate-50 space-y-4">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-teal-600 border-t-transparent" />
        <p className="text-xs font-medium text-slate-500">Checking credentials...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

const RequireRole: React.FC<{ allowedRoles: Role[]; children: React.ReactNode }> = ({
  allowedRoles,
  children,
}) => {
  const { user, isLoading } = useAuth();

  if (isLoading) return null;

  if (!user || !allowedRoles.includes(user.role)) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <>{children}</>;
};

// Smart Dashboard Redirect
const DashboardRedirect: React.FC = () => {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-slate-50">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal-600 border-t-transparent" />
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  switch (user.role) {
    case 'citizen':
      return <Navigate to="/citizen/dashboard" replace />;
    case 'admin':
      return <Navigate to="/admin/dashboard" replace />;
    case 'worker':
      return <Navigate to="/worker/dashboard" replace />;
    default:
      return <Navigate to="/login" replace />;
  }
};

export const AppRouter: React.FC = () => {
  return (
    <Routes>
      {/* Root / Dashboard Redirect */}
      <Route path="/" element={<DashboardRedirect />} />
      <Route path="/dashboard" element={<DashboardRedirect />} />

      {/* Public Pages Layout */}
      <Route element={<PublicLayout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/unauthorized" element={<UnauthorizedPage />} />
      </Route>

      {/* Authenticated Citizen Routes */}
      <Route
        path="/citizen"
        element={
          <RequireAuth>
            <RequireRole allowedRoles={['citizen']}>
              <AppLayout />
            </RequireRole>
          </RequireAuth>
        }
      >
        <Route path="dashboard" element={<CitizenDashboard />} />
        <Route path="reports" element={<CitizenReportsPage />} />
        <Route path="reports/new" element={<CreateReportPage />} />
        <Route path="reports/:id" element={<CitizenReportDetailPage />} />
        <Route path="map" element={<CitizenMapPage />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="profile" element={<CitizenProfilePage />} />
      </Route>

      {/* Authenticated Administrator Routes */}
      <Route
        path="/admin"
        element={
          <RequireAuth>
            <RequireRole allowedRoles={['admin']}>
              <AppLayout />
            </RequireRole>
          </RequireAuth>
        }
      >
        <Route path="dashboard" element={<AdminDashboard />} />
        <Route path="reports" element={<AdminReportsPage />} />
        <Route path="reports/:id" element={<AdminReportDetailPage />} />
        <Route path="map" element={<AdminMapPage />} />
        <Route path="assignments" element={<AdminAssignmentsPage />} />
        <Route path="departments" element={<AdminDepartmentsPage />} />
        <Route path="users" element={<AdminUsersPage />} />
        <Route path="analytics" element={<AdminAnalyticsPage />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="settings" element={<AdminSettingsPage />} />
      </Route>

      {/* Authenticated Field Worker Routes */}
      <Route
        path="/worker"
        element={
          <RequireAuth>
            <RequireRole allowedRoles={['worker']}>
              <AppLayout />
            </RequireRole>
          </RequireAuth>
        }
      >
        <Route path="dashboard" element={<WorkerDashboard />} />
        <Route path="assignments" element={<WorkerAssignmentsPage />} />
        <Route path="assignments/:id" element={<WorkerAssignmentDetailPage />} />
        <Route path="map" element={<WorkerMapPage />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="profile" element={<WorkerProfilePage />} />
      </Route>

      {/* 404 Fallback */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
};
