import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/hooks/use-auth';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ShieldAlert, Home, ArrowLeft } from 'lucide-react';

export const UnauthorizedPage: React.FC = () => {
  const { user } = useAuth();

  const getHomeRoute = () => {
    if (!user) return '/login';
    switch (user.role) {
      case 'citizen':
        return '/citizen/dashboard';
      case 'admin':
        return '/admin/dashboard';
      case 'worker':
        return '/worker/dashboard';
      default:
        return '/dashboard';
    }
  };

  return (
    <div className="w-full max-w-md mx-auto my-12">
      <Card className="shadow-xl border-rose-200 text-center">
        <CardHeader className="pb-2">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-rose-100 text-rose-600">
            <ShieldAlert className="h-8 w-8" />
          </div>
          <CardTitle className="text-xl text-rose-900">403 — Access Restricted</CardTitle>
          <CardDescription>
            You do not have the required administrative or worker permissions to view this section.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4 pt-2">
          <p className="text-xs text-slate-600 leading-relaxed">
            Your current logged-in role is{' '}
            <span className="font-semibold text-slate-900 capitalize">
              {user?.role || 'Guest'}
            </span>
            . If you believe this is an error, please sign in with an authorized account or contact
            system administration.
          </p>

          <div className="flex flex-col sm:flex-row gap-2 pt-2 justify-center">
            <Link to={getHomeRoute()}>
              <Button leftIcon={<Home className="h-4 w-4" />} className="w-full sm:w-auto">
                Go to My Dashboard
              </Button>
            </Link>
            <Link to="/login">
              <Button variant="outline" leftIcon={<ArrowLeft className="h-4 w-4" />} className="w-full sm:w-auto">
                Switch Account
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
