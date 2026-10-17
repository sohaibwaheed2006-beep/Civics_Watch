import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate } from 'react-router-dom';
import { registerSchema, RegisterFormData } from '@/schemas/auth-schema';
import { useAuth } from '@/hooks/use-auth';
import { useToast } from '@/hooks/use-toast';
import { parseApiError } from '@/lib/api-errors';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Mail, Lock, User, Phone, ShieldCheck, ShieldAlert } from 'lucide-react';

export const RegisterPage: React.FC = () => {
  const { register: registerAuth } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();

  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      fullName: '',
      email: '',
      phone: '',
      password: '',
      confirmPassword: '',
      agreeToTerms: false,
    },
  });

  const onSubmit = async (data: RegisterFormData) => {
    setServerError(null);
    try {
      const user = await registerAuth({
        fullName: data.fullName,
        email: data.email,
        phone: data.phone || undefined,
        password: data.password,
      });

      // Registration does NOT log the user in. Send them to the sign-in page
      // so they authenticate explicitly, pre-filling the email for convenience.
      toast.success(`Account created for ${user.fullName}. Please sign in to continue.`);
      navigate('/login', { replace: true, state: { registeredEmail: data.email } });
    } catch (err) {
      const parsed = parseApiError(err);

      // Map any field-specific server errors back onto the matching inputs so
      // the person sees exactly what to fix (e.g. "email already registered").
      if (parsed.fieldErrors) {
        Object.entries(parsed.fieldErrors).forEach(([field, message]) => {
          if (['fullName', 'email', 'phone', 'password', 'confirmPassword'].includes(field)) {
            setError(field as keyof RegisterFormData, { type: 'server', message });
          }
        });
      }

      setServerError(parsed.message);
      toast.error(parsed.message, 'Registration Failed');
    }
  };

  return (
    <div className="w-full max-w-4xl grid grid-cols-1 lg:grid-cols-12 rounded-3xl overflow-hidden shadow-2xl border border-slate-200/90 bg-white my-6">
      {/* Visual Hero Panel (5 cols) */}
      <div className="hidden lg:flex lg:col-span-5 relative flex-col justify-between p-8 text-white overflow-hidden bg-slate-950">
        <img
          src="https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1200&q=80"
          alt="Community Neighborhood"
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
            Citizen Engagement
          </span>
          <h2 className="text-2xl font-black tracking-tight leading-tight">
            Make Your Neighborhood Heard.
          </h2>
          <p className="text-xs text-teal-100/90 leading-relaxed pt-1">
            Submit road hazards, water leaks, and street sanitation tickets directly to local city crews in seconds.
          </p>
        </div>

        <div className="relative z-10 space-y-3 pt-6 border-t border-teal-800/40 text-xs text-teal-200">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Live municipal dispatch system</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-teal-400" />
            <span>Direct photographic verification</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-cyan-400" />
            <span>Transparent resolution notifications</span>
          </div>
        </div>
      </div>

      {/* Form Panel (7 cols) */}
      <div className="lg:col-span-7 p-6 sm:p-8 flex flex-col justify-center">
        <div className="mb-4">
          <h3 className="text-xl font-bold text-slate-900">Citizen Registration</h3>
          <p className="text-xs text-slate-500 mt-1">
            Join your community to report local issues, track repairs, and make your neighborhood better.
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

          {/* Citizen role badge indicator */}
          <div className="rounded-xl border border-teal-100 bg-teal-50/50 p-3 flex items-center gap-3 text-xs text-teal-800">
            <ShieldCheck className="h-5 w-5 text-teal-600 shrink-0" />
            <div>
              <p className="font-semibold">Registering as a Community Citizen</p>
              <p className="text-[11px] text-teal-700">
                Staff accounts (Field Workers & Admins) are provisioned directly by municipal leadership.
              </p>
            </div>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-3.5">
            <Input
              label="Full Name"
              placeholder="Sarah Jenkins"
              leftIcon={<User className="h-4 w-4" />}
              error={errors.fullName?.message}
              required
              {...register('fullName')}
            />

            <Input
              label="Email Address"
              type="email"
              placeholder="citizen@example.com"
              leftIcon={<Mail className="h-4 w-4" />}
              error={errors.email?.message}
              required
              {...register('email')}
            />

            <Input
              label="Phone Number (Optional)"
              type="tel"
              placeholder="+1 (555) 000-0000"
              leftIcon={<Phone className="h-4 w-4" />}
              helperText="For urgent SMS updates about submitted neighborhood safety hazards."
              error={errors.phone?.message}
              {...register('phone')}
            />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Input
                label="Password"
                type="password"
                placeholder="••••••••"
                leftIcon={<Lock className="h-4 w-4" />}
                helperText="At least 8 characters."
                error={errors.password?.message}
                required
                {...register('password')}
              />

              <Input
                label="Confirm Password"
                type="password"
                placeholder="••••••••"
                leftIcon={<Lock className="h-4 w-4" />}
                error={errors.confirmPassword?.message}
                required
                {...register('confirmPassword')}
              />
            </div>

            <div className="pt-1">
              <label className="flex items-start gap-2.5 cursor-pointer text-xs text-slate-600">
                <input
                  type="checkbox"
                  className="mt-0.5 h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500"
                  {...register('agreeToTerms')}
                />
                <span>
                  I agree to submit accurate, good-faith civic reports and abide by the{' '}
                  <span className="text-teal-700 font-medium">Community Conduct Guidelines</span>.
                </span>
              </label>
              {errors.agreeToTerms && (
                <p className="text-xs text-rose-600 mt-1 font-medium">
                  {errors.agreeToTerms.message}
                </p>
              )}
            </div>

            <Button type="submit" className="w-full" isLoading={isSubmitting}>
              Create Citizen Account
            </Button>
          </form>

          <div className="text-center text-xs text-slate-500 border-t border-slate-100 pt-3">
            Already have an account?{' '}
            <Link to="/login" className="font-semibold text-teal-600 hover:text-teal-800">
              Sign in here
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
