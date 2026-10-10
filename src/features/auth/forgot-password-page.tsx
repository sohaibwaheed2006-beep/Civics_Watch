import React from 'react';
import { Link } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Info, KeyRound } from 'lucide-react';

export const ForgotPasswordPage: React.FC = () => {
  return (
    <div className="w-full max-w-md">
      <Card className="shadow-xl border-slate-200">
        <CardHeader className="text-center pb-2">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-amber-50 text-amber-600">
            <KeyRound className="h-6 w-6" />
          </div>
          <CardTitle className="text-xl">Password Recovery Workflow</CardTitle>
          <CardDescription>
            Account recovery status and backend service configuration
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-4 text-xs text-amber-900 space-y-2">
            <div className="flex items-center gap-2 font-semibold">
              <Info className="h-4 w-4 text-amber-600 shrink-0" />
              <span>Automated Email Recovery Unavailable</span>
            </div>
            <p className="leading-relaxed text-amber-800">
              The municipal backend environment currently does not have an external SMTP email server
              configured. Automated password reset links cannot be dispatched by email at this stage.
            </p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-700 space-y-2">
            <h4 className="font-semibold text-slate-900">How to access your account:</h4>
            <ul className="list-disc pl-4 space-y-1 text-slate-600">
              <li>
                For testing and evaluation, all pre-seeded demo accounts use password:{' '}
                <strong className="text-slate-800 font-mono">password123</strong>.
              </li>
              <li>
                If you are a field worker or administrative staff member, contact your municipal
                administrator to reset your credentials.
              </li>
              <li>
                Citizens may also create a new test citizen profile on the registration screen.
              </li>
            </ul>
          </div>

          <div className="pt-2">
            <Link to="/login">
              <Button variant="outline" className="w-full" leftIcon={<ArrowLeft className="h-4 w-4" />}>
                Return to Login
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
