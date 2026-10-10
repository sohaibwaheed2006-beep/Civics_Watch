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
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Mail, Lock, User, Phone, ShieldCheck, ShieldAlert } from 'lucide-react';

export const RegisterPage: React.FC = () => {
  const { register: registerAuth } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();

  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
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

      toast.success(`Account created! Welcome, ${user.fullName}.`);
      navigate('/citizen/dashboard', { replace: true });
    } catch (err) {
      const parsed = parseApiError(err);
      setServerError(parsed.message);
      toast.error(parsed.message, 'Registration Failed');
    }
  };

  return (
    <div className="w-full max-w-lg my-6">
      <Card className="shadow-xl border-slate-200">
        <CardHeader className="text-center pb-2">
          <CardTitle className="text-xl">Citizen Registration</CardTitle>
          <CardDescription>
            Join your community to report local issues, track repairs, and make your neighborhood better.
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

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
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

          <div className="text-center text-xs text-slate-500 border-t border-slate-100 pt-4">
            Already have an account?{' '}
            <Link to="/login" className="font-semibold text-teal-600 hover:text-teal-800">
              Sign in here
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
