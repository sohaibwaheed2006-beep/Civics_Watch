import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { loginSchema, LoginFormData } from '@/schemas/auth-schema';
import { useAuth } from '@/hooks/use-auth';
import { useToast } from '@/hooks/use-toast';
import { parseApiError } from '@/lib/api-errors';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Eye, EyeOff, Lock, Mail, ShieldAlert, Sparkles } from 'lucide-react';

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
    <div className="w-full max-w-4xl grid grid-cols-1 lg:grid-cols-12 rounded-3xl overflow-hidden shadow-2xl border border-slate-200/90 bg-white">
      {/* Visual Hero Panel (5 cols) */}
      <div className="hidden lg:flex lg:col-span-5 relative flex-col justify-between p-8 text-white overflow-hidden bg-slate-950">
        <img
          src="https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1200&q=80"
          alt="Civic City"
          onError={(e) => {
            const img = e.currentTarget as HTMLImageElement;
            if (!img.src.includes('/images/auth/civic-city.jpg')) {
              img.src = '/images/auth/civic-city.jpg';
            } else {
              img.style.display = 'none';
            }
          }}
          className="absolute inset-0 h-full w-full object-cover object-center opacity-40 mix-blend-screen"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-teal-950 via-slate-950/80 to-teal-900/40" />

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
      <div className="lg:col-span-7 p-6 sm:p-10 flex flex-col justify-center">
        <div className="text-center pb-5">
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Sign in to CivicWatch</h1>
          <p className="text-xs text-slate-500 mt-1">
            Enter your credentials to manage, track, or resolve neighborhood issues.
          </p>
        </div>

        <div className="space-y-5">
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
              leftIcon={<Mail className="h-4 w-4" />}
              error={errors.email?.message}
              required
              {...register('email')}
            />

            <div>
              <Input
                label="Password"
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
                error={errors.password?.message}
                required
                {...register('password')}
              />
              <div className="mt-1 flex justify-end">
                <Link
                  to="/forgot-password"
                  className="text-xs text-teal-600 hover:text-teal-800 transition-colors"
                >
                  Forgot your password?
                </Link>
              </div>
            </div>

            <Button type="submit" className="w-full" isLoading={isSubmitting}>
              Sign In
            </Button>
          </form>

          {/* Quick Demo Fill Buttons */}
          <div className="rounded-xl border border-teal-100 bg-teal-50/50 p-3 text-xs">
            <div className="flex items-center gap-1.5 font-semibold text-teal-900 mb-2">
              <Sparkles className="h-3.5 w-3.5 text-teal-600" />
              <span>Demo Quick-Fill Personas:</span>
            </div>
            <div className="grid grid-cols-3 gap-1.5">
              <button
                type="button"
                onClick={() => handleDemoFill('citizen@example.com', 'Citizen')}
                className="rounded-lg border border-teal-200 bg-white py-1.5 px-2 text-[11px] font-medium text-teal-800 hover:bg-teal-50 transition-colors shadow-2xs"
              >
                Citizen
              </button>
              <button
                type="button"
                onClick={() => handleDemoFill('admin@example.com', 'Admin')}
                className="rounded-lg border border-teal-200 bg-white py-1.5 px-2 text-[11px] font-medium text-teal-800 hover:bg-teal-50 transition-colors shadow-2xs"
              >
                Admin
              </button>
              <button
                type="button"
                onClick={() => handleDemoFill('worker@example.com', 'Worker')}
                className="rounded-lg border border-teal-200 bg-white py-1.5 px-2 text-[11px] font-medium text-teal-800 hover:bg-teal-50 transition-colors shadow-2xs"
              >
                Worker
              </button>
            </div>
          </div>

          <div className="text-center text-xs text-slate-500 pt-1">
            Don't have an account?{' '}
            <Link to="/register" className="font-semibold text-teal-600 hover:text-teal-800">
              Register as a citizen
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
