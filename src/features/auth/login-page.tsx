import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { loginSchema, LoginFormData } from '@/schemas/auth-schema';
import { useAuth } from '@/hooks/use-auth';
import { useToast } from '@/hooks/use-toast';
import { parseApiError } from '@/lib/api-errors';
import { Input } from '@/components/ui/input';
import { Eye, EyeOff, Lock, Mail, ShieldAlert, Sparkles, User, Key, Wrench, Loader2 } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  // Pre-fill the email when we already know it: after registration
  // (`registeredEmail`) or when an account switch fell back to sign-in
  // (`email`), so the person only needs to type their password.
  const prefilledEmail =
    (location.state as any)?.registeredEmail ?? (location.state as any)?.email ?? '';

  const {
    register,
    handleSubmit,
    setValue,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: prefilledEmail,
      password: '',
    },
  });

  const onSubmit = async (data: LoginFormData) => {
    setServerError(null);
    try {
      const loggedUser = await login(data);
      toast.success(`Welcome back, ${loggedUser.fullName}!`);

      // Redirect according to role
      const from = (location.state as any)?.from?.pathname;
      if (from && !from.includes('/login')) {
        navigate(from, { replace: true });
        return;
      }

      switch (loggedUser.role) {
        case 'citizen':
          navigate('/citizen/dashboard', { replace: true });
          break;
        case 'admin':
          navigate('/admin/dashboard', { replace: true });
          break;
        case 'worker':
          navigate('/worker/dashboard', { replace: true });
          break;
        default:
          navigate('/dashboard', { replace: true });
      }
    } catch (err) {
      const parsed = parseApiError(err);

      // Surface field-specific server errors (e.g. invalid email format) on the
      // matching inputs in addition to the top-level banner.
      if (parsed.fieldErrors) {
        Object.entries(parsed.fieldErrors).forEach(([field, message]) => {
          if (['email', 'password'].includes(field)) {
            setError(field as keyof LoginFormData, { type: 'server', message });
          }
        });
      }

      setServerError(parsed.message);
      toast.error(parsed.message, 'Login Failed');
    }
  };

  const handleDemoFill = (email: string, roleName: string) => {
    setValue('email', email, { shouldValidate: true });
    setValue('password', 'Password123!', { shouldValidate: true });
    toast.info(`Filled credentials for ${roleName} demo user.`);
  };

  return (
    <div className="w-full max-w-4xl grid grid-cols-1 lg:grid-cols-12 rounded-[28px] overflow-hidden shadow-2xl shadow-slate-200/70 border border-slate-100 bg-white">
      {/* Visual Hero Panel (5 cols) */}
      <div className="hidden lg:flex lg:col-span-5 relative flex-col justify-between p-8 text-white overflow-hidden bg-ink-900 border-r border-teal-500/20">
        <img
          src="/images/auth/civic-city.jpg"
          alt="Civic city skyline"
          loading="lazy"
          onError={(e) => {
            (e.currentTarget as HTMLImageElement).style.display = 'none';
          }}
          className="absolute inset-0 h-full w-full object-cover object-center opacity-45 mix-blend-screen"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-teal-950 via-ink-900/80 to-teal-900/40" />

        <div className="relative z-10 space-y-2">
          <span className="inline-block px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-teal-500/20 text-teal-300 border border-teal-400/30">
            Municipal Operations
          </span>
          <h2 className="text-2xl font-black tracking-tight leading-tight">
            Building Safer, Cleaner Communities.
          </h2>
          <p className="text-xs text-teal-100/90 leading-relaxed pt-1">
            Real-time citizen reporting and rapid municipal maintenance dispatch for potholes, outages, and public safety.
          </p>
        </div>

        <div className="relative z-10 space-y-3 pt-6 border-t border-teal-800/40 text-xs text-teal-200">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>24/7 City Works Dispatch Active</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-teal-400" />
            <span>Over 1,200 local hazards resolved this month</span>
          </div>
        </div>
      </div>

      {/* Form Content (7 cols) */}
      <div className="lg:col-span-7 p-7 sm:p-10 flex flex-col justify-center bg-white">
        <div className="text-center pb-5">
          <h1 className="text-2xl sm:text-[26px] font-bold text-slate-900 tracking-tight">
            Sign in to{' '}
            <span className="bg-gradient-to-r from-teal-500 to-emerald-500 bg-clip-text text-transparent">
              CivicWatch
            </span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Enter your credentials to manage, track, or resolve neighborhood issues.
          </p>
        </div>

        <div className="space-y-4">
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
              label="Email address"
              type="email"
              placeholder="you@example.com"
              leftIcon={<Mail className="h-4 w-4 text-slate-400" />}
              className="border-teal-400 focus:border-teal-500 focus:ring-teal-500/20"
              hideRequiredAsterisk={true}
              error={errors.email?.message}
              required
              {...register('email')}
            />

            <div>
              <Input
                label="Password"
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                leftIcon={<Lock className="h-4 w-4 text-slate-400" />}
                className="border-slate-200 focus:border-teal-500 focus:ring-teal-500/20"
                hideRequiredAsterisk={true}
                rightIcon={
                  <button
                    type="button"
                    onClick={() => setShowPassword((prev) => !prev)}
                    className="text-slate-400 hover:text-slate-600 focus:outline-none cursor-pointer"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                }
                error={errors.password?.message}
                required
                {...register('password')}
              />
              <div className="mt-1 flex justify-end">
                <Link
                  to="/forgot-password"
                  className="text-xs font-medium text-teal-600 hover:text-teal-700 transition-colors"
                >
                  Forgot your password?
                </Link>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full h-11 rounded-xl bg-gradient-to-r from-teal-500 via-teal-600 to-emerald-500 hover:from-teal-600 hover:to-emerald-600 text-white font-semibold text-sm shadow-md shadow-teal-500/25 hover:shadow-lg hover:shadow-teal-500/35 active:scale-[0.99] transition-all flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
            >
              {isSubmitting ? (
                <Loader2 className="h-4 w-4 animate-spin shrink-0" />
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          {/* Quick Demo Fill Buttons */}
          <div className="rounded-2xl border border-slate-200/70 bg-[#edf5f6]/80 dark:bg-slate-50/60 p-3.5 text-xs mt-1">
            <div className="flex items-center gap-1.5 font-semibold text-slate-800 mb-2.5">
              <Sparkles className="h-3.5 w-3.5 text-teal-600" />
              <span>Demo Quick-Fill Personas:</span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => handleDemoFill('citizen@example.com', 'Citizen')}
                className="rounded-xl border border-teal-300 bg-white/95 py-2 px-2 text-xs font-medium text-slate-800 hover:bg-teal-50 hover:border-teal-500 transition-all shadow-xs flex items-center justify-center gap-1.5 cursor-pointer"
              >
                <User className="h-3.5 w-3.5 text-teal-600" />
                <span>Citizen</span>
              </button>
              <button
                type="button"
                onClick={() => handleDemoFill('admin@example.com', 'Admin')}
                className="rounded-xl border border-teal-300 bg-white/95 py-2 px-2 text-xs font-medium text-slate-800 hover:bg-teal-50 hover:border-teal-500 transition-all shadow-xs flex items-center justify-center gap-1.5 cursor-pointer"
              >
                <Key className="h-3.5 w-3.5 text-teal-600" />
                <span>Admin</span>
              </button>
              <button
                type="button"
                onClick={() => handleDemoFill('worker@example.com', 'Worker')}
                className="rounded-xl border border-teal-300 bg-white/95 py-2 px-2 text-xs font-medium text-slate-800 hover:bg-teal-50 hover:border-teal-500 transition-all shadow-xs flex items-center justify-center gap-1.5 cursor-pointer"
              >
                <Wrench className="h-3.5 w-3.5 text-teal-600" />
                <span>Worker</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
