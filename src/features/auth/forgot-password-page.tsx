import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link } from 'react-router-dom';
import { forgotPasswordSchema, ForgotPasswordFormData } from '@/schemas/auth-schema';
import { authService } from '@/services/auth-service';
import { useToast } from '@/hooks/use-toast';
import { parseApiError } from '@/lib/api-errors';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ArrowLeft, KeyRound, Mail, MailCheck, ShieldAlert } from 'lucide-react';

export const ForgotPasswordPage: React.FC = () => {
  const { toast } = useToast();
  const [serverError, setServerError] = useState<string | null>(null);
  const [submittedEmail, setSubmittedEmail] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordFormData>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: '' },
  });

  const onSubmit = async (data: ForgotPasswordFormData) => {
    setServerError(null);
    try {
      await authService.forgotPassword(data.email);
      // The backend returns the same response whether or not the email exists,
      // so we always move to the same confirmation state (no enumeration).
      setSubmittedEmail(data.email);
    } catch (err) {
      const parsed = parseApiError(err);
      setServerError(parsed.message);
      toast.error(parsed.message, 'Could Not Send Reset Link');
    }
  };

  return (
    <div className="w-full max-w-2xl rounded-3xl overflow-hidden shadow-2xl border border-slate-200/90 bg-white grid grid-cols-1 md:grid-cols-12">
      {/* Visual Accent Panel */}
      <div className="hidden md:flex md:col-span-5 relative flex-col justify-between p-6 text-white overflow-hidden bg-slate-950">
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
          className="absolute inset-0 h-full w-full object-cover opacity-35 mix-blend-screen"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-teal-950 via-slate-950/85 to-teal-900/40" />
        <div className="relative z-10 space-y-2">
          <span className="inline-block px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-400/30">
            Security & Support
          </span>
          <h3 className="text-xl font-bold tracking-tight text-white">
            Civic Account Help
          </h3>
          <p className="text-xs text-teal-100/80 leading-relaxed">
            Direct credential recovery assistance for municipal operations, technicians, and local citizens.
          </p>
        </div>
        <div className="relative z-10 text-[11px] text-teal-300/80 border-t border-teal-800/40 pt-3">
          Neighborhood Issue Reporter
        </div>
      </div>

      {/* Content */}
      <div className="md:col-span-7 p-6 sm:p-8 flex flex-col justify-center space-y-4">
        {submittedEmail ? (
          <>
            <div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600 mb-3 border border-emerald-200">
                <MailCheck className="h-5 w-5" />
              </div>
              <h3 className="text-xl font-bold text-slate-900">Check your inbox</h3>
              <p className="text-xs text-slate-500 mt-1">
                If an account exists for{' '}
                <strong className="text-slate-700">{submittedEmail}</strong>, we've sent a
                password-reset link to it. The link expires in 30 minutes.
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-3.5 text-xs text-slate-700 space-y-1.5">
              <p className="text-[11px] text-slate-600 leading-relaxed">
                Didn't get an email? Check your spam folder, make sure you entered the right
                address, or try again in a few minutes.
              </p>
            </div>

            <div className="flex flex-col gap-2 pt-1">
              <Button
                variant="outline"
                className="w-full"
                onClick={() => {
                  setSubmittedEmail(null);
                }}
              >
                Use a different email
              </Button>
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
          </>
        ) : (
          <>
            <div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber-50 text-amber-600 mb-3 border border-amber-200">
                <KeyRound className="h-5 w-5" />
              </div>
              <h3 className="text-xl font-bold text-slate-900">Reset your password</h3>
              <p className="text-xs text-slate-500 mt-1">
                Enter the email address for your account and we'll send you a secure link to
                set a new password.
              </p>
            </div>

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
                label="Email Address"
                type="email"
                placeholder="you@example.com"
                leftIcon={<Mail className="h-4 w-4" />}
                error={errors.email?.message}
                required
                {...register('email')}
              />

              <Button type="submit" className="w-full" isLoading={isSubmitting}>
                Send reset link
              </Button>
            </form>

            <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-3.5 text-xs text-slate-700 space-y-1.5">
              <h4 className="font-semibold text-slate-900 text-[11px] uppercase tracking-wider">
                Can't receive email?
              </h4>
              <ul className="list-disc pl-4 space-y-1 text-[11px] text-slate-600">
                <li>
                  Field workers and administrative staff can ask a municipal administrator to
                  reset their credentials directly.
                </li>
                <li>Citizens can also create a new profile from the registration screen.</li>
              </ul>
            </div>

            <div className="pt-1">
              <Link to="/login">
                <Button
                  variant="outline"
                  className="w-full"
                  leftIcon={<ArrowLeft className="h-4 w-4" />}
                >
                  Return to Login
                </Button>
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
