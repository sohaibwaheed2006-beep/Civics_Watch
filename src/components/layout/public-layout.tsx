import React from 'react';
import { Outlet, Link, useNavigate } from 'react-router-dom';
import { Shield, LogOut, LayoutDashboard } from 'lucide-react';
import { ToastContainer } from '@/components/ui/toast';
import { useAuth } from '@/hooks/use-auth';
import { Avatar } from '@/components/ui/avatar';
import { ThemeToggle } from '@/components/theme/theme-toggle';
import { ROLE_DETAILS } from '@/lib/constants';

export const PublicLayout: React.FC = () => {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const getDashboardRoute = () => {
    if (!user) return '/login';
    switch (user.role) {
      case 'citizen':
        return '/citizen/dashboard';
      case 'admin':
        return '/admin/dashboard';
      case 'worker':
        return '/worker/dashboard';
      default:
        return '/dashboard';
    }
  };

  const handleSignOut = async () => {
    await logout();
    navigate('/login');
  };

  const roleInfo = user ? ROLE_DETAILS[user.role] : null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#eff8f7] via-[#f7fafb] to-[#ecf6f5] dark:from-[#07111a] dark:via-[#0a1722] dark:to-[#08201f] flex flex-col justify-between">
      {/* Public Header */}
      <header className="w-full border-b border-slate-200/60 bg-white/70 backdrop-blur-md px-6 py-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-teal-500 to-emerald-600 text-white shadow-btn-primary">
              <Shield className="h-5 w-5" />
            </div>
            <div>
              <span className="font-bold text-slate-900 text-base tracking-tight">CivicWatch</span>
              <p className="text-[10px] text-teal-700 font-semibold -mt-0.5">Neighborhood Issue Reporter</p>
            </div>
          </Link>

          <div className="flex items-center gap-4 text-sm font-medium text-slate-600">
            <ThemeToggle />
            {isAuthenticated && user ? (
              <div className="flex items-center gap-3">
                <div className="hidden sm:flex items-center gap-2 pr-2 border-r border-slate-200">
                  <Avatar
                    alt={user.fullName}
                    fallback={user.fullName}
                    role={user.role}
                    size="xs"
                  />
                  <div className="text-left">
                    <span className="font-semibold text-slate-800">{user.fullName}</span>
                    {roleInfo && (
                      <span className={`ml-1.5 text-[10px] font-bold px-1.5 py-0.2 rounded-full border ${roleInfo.badgeClass}`}>
                        {roleInfo.label}
                      </span>
                    )}
                  </div>
                </div>

                <Link
                  to={getDashboardRoute()}
                  className="rounded-xl bg-[#0d9488] px-3.5 py-1.5 text-white hover:bg-teal-700 transition-colors shadow-sm flex items-center gap-1.5 font-semibold"
                >
                  <LayoutDashboard className="h-3.5 w-3.5" />
                  <span>Dashboard</span>
                </Link>

                <button
                  onClick={handleSignOut}
                  className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-slate-600 hover:text-rose-600 hover:border-rose-200 hover:bg-rose-50 transition-colors flex items-center gap-1"
                  title="Sign Out"
                >
                  <LogOut className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">Sign Out</span>
                </button>
              </div>
            ) : (
              <>
                <Link to="/login" className="text-slate-700 hover:text-teal-700 font-medium text-sm transition-colors">
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="rounded-xl bg-[#0d9488] hover:bg-[#0f766e] px-4 py-2 text-white font-medium text-sm shadow-md shadow-teal-700/20 hover:shadow-teal-700/30 transition-all"
                >
                  Register as Citizen
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center p-4 sm:p-6">
        <Outlet />
      </main>

      {/* Public Footer */}
      <footer className="border-t border-slate-200/80 bg-white/60 py-6 text-center text-xs text-slate-400">
        <p>CivicWatch &copy; 2026. Empowering citizens and local government to build cleaner, safer neighborhoods.</p>
      </footer>

      <ToastContainer />
    </div>
  );
};
