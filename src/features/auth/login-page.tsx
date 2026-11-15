import React, { useEffect, useState } from 'react';
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
  const { login, isAuthenticated, sessionVerified } = useAuth();
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

  // The free backend sleeps when idle; explain a slow first sign-in.
  const [slowLogin, setSlowLogin] = useState(false);
  useEffect(() => {
    if (!isSubmitting) {
      setSlowLogin(false);
      return;
    }
    const timer = window.setTimeout(() => setSlowLogin(true), 5000);
    return () => window.clearTimeout(timer);
  }, [isSubmitting]);

  // Already signed in (and confirmed by the server)? Skip the form and go to
  // the right dashboard. Not while a sign-in is in flight: onSubmit does its
  // own redirect (including back to the page the user came from).
  useEffect(() => {
    if (sessionVerified && isAuthenticated && !isSubmitting) {
      navigate('/dashboard', { replace: true });
    }
  }, [sessionVerified, isAuthenticated, isSubmitting, navigate]);

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
    <div className="w-full max-w-4xl grid grid-cols-1 lg:grid-cols-12 rounded-2xl overflow-hidden shadow-lg dark:shadow-none border border-slate-200 bg-white">
      {/* Visual Hero Panel (5 cols) */}
      <div className="hidden lg:flex lg:col-span-5 relative flex-col justify-between p-8 text-white overflow-hidden bg-ink-950 border-r border-white/10">
        <img
          src="/images/auth/civic-city.jpg"
          alt="Civic city skyline"
          loading="lazy"
          onError={(e) => {
            (e.currentTarget as HTMLImageElement).style.display = 'none';
          }}
          className="absolute inset-0 h-full w-full object-cover object-center opacity-40 grayscale"
        />
        {/* Plain dark scrim: keeps the photo as texture and the copy legible. */}
        <div className="absolute inset-0 bg-gradient-to-t from-ink-950 via-ink-950/80 to-ink-950/55" />

        <div className="relative z-10 space-y-2">
          <span className="inline-block px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-black/30 text-teal-300 border border-white/15">
            Municipal Operations
          </span>
          <h2 className="text-2xl font-bold tracking-tight leading-tight pt-1">
            Building Safer, Cleaner Communities.
          </h2>
          <p className="text-xs text-ink-200/85 leading-relaxed pt-1">
            Real-time citizen reporting and rapid municipal maintenance dispatch for potholes, outages, and public safety.
          </p>
        </div>

        <div className="relative z-10 space-y-3 pt-6 border-t border-white/10 text-xs text-ink-200/85">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-emerald-400" />
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
            <span className="text-teal-600">CivicWatch</span>
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
              className="dark:bg-ink-950"
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
                className="dark:bg-ink-950"
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
              className="w-full h-11 rounded-xl bg-teal-600 hover:bg-teal-700 active:bg-teal-800 text-white font-semibold text-sm active:scale-[0.99] transition-colors flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
            >
              {isSubmitting ? (
                <Loader2 className="h-4 w-4 animate-spin shrink-0" />
              ) : (
                'Sign In'
              )}
            </button>
            {isSubmitting && slowLogin && (
              <p className="text-center text-xs text-slate-500" role="status">
                Waking up the server, this can take up to a minute the first time…
              </p>
            )}
          </form>

          {/* Quick Demo Fill Buttons */}
          <div className="rounded-2xl border border-slate-200 bg-slate-50 dark:bg-black/20 p-3.5 text-xs mt-1">
            <div className="flex items-center gap-1.5 font-semibold text-slate-800 mb-2.5">
              <Sparkles className="h-3.5 w-3.5 text-teal-600" />
              <span>Demo Quick-Fill Personas:</span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => handleDemoFill('citizen@example.com', 'Citizen')}
                className="rounded-lg border border-slate-200 bg-white py-2 px-2 text-xs font-medium text-slate-800 hover:border-teal-500 hover:text-teal-700 transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
              >
                <User className="h-3.5 w-3.5 text-teal-600" />
                <span>Citizen</span>
              </button>
              <button
                type="button"
                onClick={() => handleDemoFill('admin@example.com', 'Admin')}
                className="rounded-lg border border-slate-200 bg-white py-2 px-2 text-xs font-medium text-slate-800 hover:border-teal-500 hover:text-teal-700 transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
              >
                <Key className="h-3.5 w-3.5 text-teal-600" />
                <span>Admin</span>
              </button>
              <button
                type="button"
                onClick={() => handleDemoFill('worker@example.com', 'Worker')}
                className="rounded-lg border border-slate-200 bg-white py-2 px-2 text-xs font-medium text-slate-800 hover:border-teal-500 hover:text-teal-700 transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
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
