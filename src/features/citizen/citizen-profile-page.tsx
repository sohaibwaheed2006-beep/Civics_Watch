import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useAuth } from '@/hooks/use-auth';
import { useToast } from '@/hooks/use-toast';
import { authService } from '@/services/auth-service';
import { userService } from '@/services/user-service';
import { changePasswordSchema, ChangePasswordFormData } from '@/schemas/auth-schema';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { formatDate } from '@/lib/formatters';
import { User, Mail, Phone, Lock, LogOut, CheckCircle2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const CitizenProfilePage: React.FC = () => {
  const { user, updateCurrentUserState, logout } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();

  const [isUpdatingProfile, setIsUpdatingProfile] = useState(false);
  const [profileName, setProfileName] = useState(user?.fullName || '');
  const [profilePhone, setProfilePhone] = useState(user?.phone || '');

  const {
    register: registerPass,
    handleSubmit: handleSubmitPass,
    reset: resetPass,
    formState: { errors: passErrors, isSubmitting: isSubmittingPass },
  } = useForm<ChangePasswordFormData>({
    resolver: zodResolver(changePasswordSchema),
  });

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    setIsUpdatingProfile(true);
    try {
      const updated = await userService.updateUser(user.id, {
        fullName: profileName,
        phone: profilePhone,
      });
      updateCurrentUserState(updated);
      toast.success('Profile details updated successfully.');
    } catch {
      toast.error('Failed to update profile.');
    } finally {
      setIsUpdatingProfile(false);
    }
  };

  const onChangePassword = async (data: ChangePasswordFormData) => {
    try {
      await authService.changePassword({
        currentPassword: data.currentPassword,
        newPassword: data.newPassword,
      });
      toast.success('Your password has been changed successfully.');
      resetPass();
    } catch {
      toast.error('Failed to change password. Please check your current password.');
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
          { label: 'Citizen Portal', href: '/citizen/dashboard' },
          { label: 'Profile & Settings' },
        ]}
      />

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Account & Settings
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Manage your personal profile details, notification phone, and credentials.
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

      {/* Profile Overview Card */}
      <Card className="border-slate-200/90 shadow-sm">
        <CardHeader>
          <CardTitle className="text-base">Personal Information</CardTitle>
          <CardDescription>Update your display name and contact phone.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleUpdateProfile} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Full Name"
                value={profileName}
                onChange={(e) => setProfileName(e.target.value)}
                leftIcon={<User className="h-4 w-4" />}
                required
              />

              <Input
                label="Email Address (Registered)"
                value={user?.email || ''}
                leftIcon={<Mail className="h-4 w-4" />}
                disabled
                helperText="Email change requires administrative authorization."
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Contact Phone"
                value={profilePhone}
                onChange={(e) => setProfilePhone(e.target.value)}
                leftIcon={<Phone className="h-4 w-4" />}
                placeholder="+1 (555) 000-0000"
              />

              <div>
                <label className="block text-sm font-medium text-slate-700">Account Type</label>
                <div className="mt-1 flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-700">
                  <CheckCircle2 className="h-4 w-4 text-teal-600" />
                  <span className="font-semibold capitalize">{user?.role} Citizen Account</span>
                  <span className="text-slate-400 ml-auto">
                    Joined {formatDate(user?.createdAt)}
                  </span>
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button type="submit" isLoading={isUpdatingProfile}>
                Save Profile Changes
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Change Password Card */}
      <Card className="border-slate-200/90 shadow-sm">
        <CardHeader>
          <CardTitle className="text-base">Change Password</CardTitle>
          <CardDescription>
            Ensure your account is using a strong, secure password.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmitPass(onChangePassword)} className="space-y-4">
            <Input
              label="Current Password"
              type="password"
              placeholder="••••••••"
              leftIcon={<Lock className="h-4 w-4" />}
              error={passErrors.currentPassword?.message}
              required
              {...registerPass('currentPassword')}
            />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="New Password"
                type="password"
                placeholder="••••••••"
                leftIcon={<Lock className="h-4 w-4" />}
                error={passErrors.newPassword?.message}
                required
                {...registerPass('newPassword')}
              />

              <Input
                label="Confirm New Password"
                type="password"
                placeholder="••••••••"
                leftIcon={<Lock className="h-4 w-4" />}
                error={passErrors.confirmPassword?.message}
                required
                {...registerPass('confirmPassword')}
              />
            </div>

            <div className="flex justify-end pt-2">
              <Button type="submit" isLoading={isSubmittingPass}>
                Update Password
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};
