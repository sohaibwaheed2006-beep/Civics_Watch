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
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Eye, EyeOff, Lock, Mail, ShieldAlert, Sparkles } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
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
      setServerError(parsed.message);
      toast.error(parsed.message, 'Login Failed');
    }
  };

  const handleDemoFill = (email: string, roleName: string) => {
    setValue('email', email, { shouldValidate: true });
    setValue('password', 'password123', { shouldValidate: true });
    toast.info(`Filled credentials for ${roleName} demo user.`);
  };

  return (
    <div className="w-full max-w-md">
      <Card className="shadow-xl border-slate-200">
        <CardHeader className="text-center pb-2">
          <CardTitle className="text-xl">Sign in to CivicWatch</CardTitle>
          <CardDescription>
            Enter your credentials to manage, track, or resolve neighborhood issues.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-5">
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

          <div className="text-center text-xs text-slate-500">
            Don't have an account?{' '}
            <Link to="/register" className="font-semibold text-teal-600 hover:text-teal-800">
              Register as a citizen
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
