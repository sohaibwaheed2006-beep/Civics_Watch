import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/use-auth';
import { Card, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { ShieldAlert, Home, Shield, Wrench, LogOut, Sparkles } from 'lucide-react';
import { Avatar } from '@/components/ui/avatar';

export const UnauthorizedPage: React.FC = () => {
  const { user, login, logout } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [switchingRole, setSwitchingRole] = useState<string | null>(null);

  const getHomeRoute = () => {
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

  const handleQuickSwitch = async (email: string, targetRoute: string, roleName: string) => {
    setSwitchingRole(roleName);
    try {
      const loggedUser = await login({ email, password: 'password123' });
      toast.success(`Switched account to ${loggedUser.fullName} (${roleName}).`);
      navigate(targetRoute, { replace: true });
    } catch {
      toast.error(`Failed to switch to ${roleName} account.`);
    } finally {
      setSwitchingRole(null);
    }
  };

  const handleSignOut = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="w-full max-w-lg mx-auto my-8 px-4">
      <Card className="shadow-2xl border-rose-200/80 text-center overflow-hidden">
        {/* Header Ribbon */}
        <div className="bg-rose-50 border-b border-rose-100 py-6 px-6">
          <div className="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-2xl bg-rose-100 text-rose-600 shadow-inner">
            <ShieldAlert className="h-9 w-9" />
          </div>
          <CardTitle className="text-2xl font-extrabold text-rose-900">403 — Access Restricted</CardTitle>
          <CardDescription className="text-xs text-rose-700/80 mt-1 max-w-sm mx-auto">
            You do not have the required administrative or worker permissions to view this section.
          </CardDescription>
        </div>

        <CardContent className="space-y-5 p-6">
          {/* Current User Badge */}
          <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-3.5 flex items-center justify-between text-left">
            <div className="flex items-center gap-3">
              <Avatar
                alt={user?.fullName || 'User'}
                fallback={user?.fullName || 'U'}
                role={user?.role}
                size="md"
              />
              <div>
                <p className="text-xs font-bold text-slate-900">{user?.fullName || 'Guest User'}</p>
                <p className="text-[11px] text-slate-500">{user?.email || 'Not logged in'}</p>
              </div>
            </div>
            <span className="text-[11px] font-bold px-2.5 py-1 rounded-full border bg-white shadow-2xs capitalize text-slate-700">
              Role: <span className="text-teal-700">{user?.role || 'None'}</span>
            </span>
          </div>

          {/* Quick Demo Switcher Panel */}
          <div className="rounded-2xl border border-teal-100 bg-gradient-to-br from-teal-50/60 to-slate-50/60 p-4 text-left">
            <div className="flex items-center gap-1.5 font-bold text-teal-950 text-xs mb-1">
              <Sparkles className="h-4 w-4 text-teal-600" />
              <span>Need Access to This Page? Switch Persona Instantly:</span>
            </div>
            <p className="text-[11px] text-slate-600 leading-relaxed mb-3">
              This demo includes pre-configured personas. Click below to switch into an authorized role with one tap:
            </p>

            <div className="space-y-2">
              <button
                type="button"
                onClick={() => handleQuickSwitch('admin@example.com', '/admin/dashboard', 'Administrator')}
                disabled={Boolean(switchingRole)}
                className="w-full flex items-center justify-between p-2.5 rounded-xl border border-indigo-200 bg-white hover:bg-indigo-50/80 transition-all text-xs font-semibold text-indigo-950 shadow-2xs group"
              >
                <div className="flex items-center gap-2.5">
                  <div className="h-7 w-7 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center">
                    <Shield className="h-4 w-4" />
                  </div>
                  <div className="text-left">
                    <p className="text-xs font-bold text-slate-900 group-hover:text-indigo-950">
                      Switch to Administrator (Marcus Vance)
                    </p>
                    <p className="text-[10px] text-slate-500 font-normal">Full municipal access, SLAs, departments & issue dispatch</p>
                  </div>
                </div>
                <span className="text-[11px] text-indigo-600 font-bold group-hover:translate-x-0.5 transition-transform">&rarr;</span>
              </button>

              <button
                type="button"
                onClick={() => handleQuickSwitch('worker@example.com', '/worker/dashboard', 'Field Technician')}
                disabled={Boolean(switchingRole)}
                className="w-full flex items-center justify-between p-2.5 rounded-xl border border-amber-200 bg-white hover:bg-amber-50/80 transition-all text-xs font-semibold text-amber-950 shadow-2xs group"
              >
                <div className="flex items-center gap-2.5">
                  <div className="h-7 w-7 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center">
                    <Wrench className="h-4 w-4" />
                  </div>
                  <div className="text-left">
                    <p className="text-xs font-bold text-slate-900 group-hover:text-amber-950">
                      Switch to Field Technician (Dave Miller)
                    </p>
                    <p className="text-[10px] text-slate-500 font-normal">Public Works work orders, resolution logs & field map</p>
                  </div>
                </div>
                <span className="text-[11px] text-amber-600 font-bold group-hover:translate-x-0.5 transition-transform">&rarr;</span>
              </button>
            </div>
          </div>

          {/* Fallback actions */}
          <div className="pt-2 flex flex-col sm:flex-row gap-2 justify-center">
            <Link to={getHomeRoute()} className="w-full sm:w-auto">
              <Button leftIcon={<Home className="h-4 w-4" />} className="w-full sm:w-auto font-semibold">
                Back to My Dashboard
              </Button>
            </Link>
            <Button
              variant="outline"
              onClick={handleSignOut}
              leftIcon={<LogOut className="h-4 w-4" />}
              className="w-full sm:w-auto text-slate-600 hover:text-rose-600"
            >
              Sign Out
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
