import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { resetPasswordSchema, ResetPasswordFormData } from '@/schemas/auth-schema';
import { authService } from '@/services/auth-service';
import { useToast } from '@/hooks/use-toast';
import { parseApiError } from '@/lib/api-errors';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Eye, EyeOff, Lock, LockKeyhole, ShieldAlert } from 'lucide-react';

export const ResetPasswordPage: React.FC = () => {
  const { toast } = useToast();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';

  const [serverError, setServerError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordFormData>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { newPassword: '', confirmPassword: '' },
  });

  const onSubmit = async (data: ResetPasswordFormData) => {
    setServerError(null);
    try {
      await authService.resetPassword(token, data.newPassword);
      toast.success('Your password has been reset. Please sign in.');
      navigate('/login', { replace: true });
    } catch (err) {
      const parsed = parseApiError(err);
      setServerError(parsed.message);
      toast.error(parsed.message, 'Reset Failed');
    }
  };

  return (
    <div className="w-full max-w-md rounded-3xl overflow-hidden shadow-2xl border border-slate-200/90 bg-white">
      <div className="p-6 sm:p-8 flex flex-col justify-center space-y-4">
        <div>
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-teal-50 text-teal-600 mb-3 border border-teal-200">
            <LockKeyhole className="h-5 w-5" />
          </div>
          <h3 className="text-xl font-bold text-slate-900">Set a new password</h3>
          <p className="text-xs text-slate-500 mt-1">
            Choose a strong password you don't use anywhere else.
          </p>
        </div>

        {!token ? (
          <>
            <div
              role="alert"
              className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800"
            >
              <ShieldAlert className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
              <span>
                This reset link is missing or malformed. Please request a new one from the
                "Forgot password" page.
              </span>
            </div>
            <Link to="/forgot-password">
              <Button variant="outline" className="w-full">
                Request a new link
              </Button>
            </Link>
          </>
        ) : (
          <>
            {serverError && (
              <div
                role="alert"
                className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800"
              >
                <ShieldAlert className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
                <span>{serverError}</span>
              </div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <Input
                label="New Password"
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                leftIcon={<Lock className="h-4 w-4" />}
                rightIcon={
                  <button
                    type="button"
                    onClick={() => setShowPassword((prev) => !prev)}
                    className="text-slate-400 hover:text-slate-600 focus:outline-none"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                }
                helperText="At least 8 characters."
                error={errors.newPassword?.message}
                required
                {...register('newPassword')}
              />

              <Input
                label="Confirm New Password"
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                leftIcon={<Lock className="h-4 w-4" />}
                error={errors.confirmPassword?.message}
                required
                {...register('confirmPassword')}
              />

              <Button type="submit" className="w-full" isLoading={isSubmitting}>
                Reset password
              </Button>
            </form>
          </>
        )}

        <div className="pt-1">
          <Link to="/login">
            <Button
              variant="ghost"
              className="w-full"
              leftIcon={<ArrowLeft className="h-4 w-4" />}
            >
              Return to Login
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
};
