import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useAuth } from '@/hooks/use-auth';
import { useToast } from '@/hooks/use-toast';
import { authService } from '@/services/auth-service';
import { changePasswordSchema, ChangePasswordFormData } from '@/schemas/auth-schema';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { formatDate } from '@/lib/formatters';
import { User, Lock, LogOut, Building, ShieldCheck } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Avatar } from '@/components/ui/avatar';

export const WorkerProfilePage: React.FC = () => {
  const { user, logout } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ChangePasswordFormData>({
    resolver: zodResolver(changePasswordSchema),
  });

  const onChangePassword = async (data: ChangePasswordFormData) => {
    try {
      await authService.changePassword({
        currentPassword: data.currentPassword,
        newPassword: data.newPassword,
      });
      toast.success('Your technician account password has been changed.');
      reset();
    } catch {
      toast.error('Failed to change password. Please verify your current password.');
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="space-y-6 max-w-3xl mx-auto pb-12">
      <Breadcrumbs
        items={[
          { label: 'Worker Portal', href: '/worker/dashboard' },
          { label: 'Technician Profile' },
        ]}
      />

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Technician Profile & Security
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            View assigned department credentials and manage authentication password.
          </p>
        </div>

        <Button
          variant="outline"
          onClick={handleLogout}
          className="text-rose-600 border-rose-200 hover:bg-rose-50 text-xs"
          leftIcon={<LogOut className="h-4 w-4" />}
        >
          Sign Out
        </Button>
      </div>

      {/* Technician Info Card */}
      <Card className="border-slate-200/90 shadow-sm">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <User className="h-4 w-4 text-amber-600" />
            <span>Technician Identification & Credentials</span>
          </CardTitle>
          <CardDescription>Verified municipal field operations personnel.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Technician Photo Header */}
          <div className="flex items-center gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200/80 mb-2">
            <Avatar
              alt={user?.fullName}
              fallback={user?.fullName}
              role="worker"
              size="xl"
              showBorder
            />
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-slate-900">{user?.fullName}</h2>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                  <ShieldCheck className="h-3 w-3 text-amber-600" />
                  Active Field Crew
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">{user?.email}</p>
              <p className="text-xs font-semibold text-teal-800 mt-1">
                {user?.departmentName || 'Public Infrastructure Department'}
              </p>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <p className="text-slate-400 font-medium">Full Name</p>
              <p className="font-semibold text-slate-900 text-sm mt-0.5">{user?.fullName}</p>
              <p className="text-slate-500">{user?.email}</p>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <p className="text-slate-400 font-medium">Assigned Department</p>
              <p className="font-semibold text-teal-800 text-sm mt-0.5 flex items-center gap-1.5">
                <Building className="h-4 w-4 text-teal-600" />
                <span>{user?.departmentName || 'Public Infrastructure'}</span>
              </p>
              <p className="text-slate-500">Authorized Field Crew</p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <p className="text-slate-400 font-medium">Contact Phone</p>
              <p className="font-semibold text-slate-900 mt-0.5">{user?.phone || 'Not recorded'}</p>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <p className="text-slate-400 font-medium">Account Created</p>
              <p className="font-semibold text-slate-900 mt-0.5">{formatDate(user?.createdAt)}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Change Password Card */}
      <Card className="border-slate-200/90 shadow-sm">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Lock className="h-4 w-4 text-teal-600" />
            <span>Change Security Password</span>
          </CardTitle>
          <CardDescription>
            Update password for field terminal and mobile device access.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onChangePassword)} className="space-y-4">
            <Input
              label="Current Password"
              type="password"
              placeholder="••••••••"
              error={errors.currentPassword?.message}
              required
              {...register('currentPassword')}
            />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="New Password"
                type="password"
                placeholder="••••••••"
                error={errors.newPassword?.message}
                required
                {...register('newPassword')}
              />

              <Input
                label="Confirm New Password"
                type="password"
                placeholder="••••••••"
                error={errors.confirmPassword?.message}
                required
                {...register('confirmPassword')}
              />
            </div>

            <div className="flex justify-end pt-2">
              <Button type="submit" isLoading={isSubmitting}>
                Update Password
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};
