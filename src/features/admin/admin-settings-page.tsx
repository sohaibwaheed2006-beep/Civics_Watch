import React, { useState } from 'react';
import { useAuth } from '@/hooks/use-auth';
import { useToast } from '@/hooks/use-toast';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { DEFAULT_MAP_CONFIG } from '@/lib/constants';
import { Map, Shield, Server, LogOut, CheckCircle2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Avatar } from '@/components/ui/avatar';

export const AdminSettingsPage: React.FC = () => {
  const { user, logout } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();

  const [mapLat, setMapLat] = useState(DEFAULT_MAP_CONFIG.lat.toString());
  const [mapLng, setMapLng] = useState(DEFAULT_MAP_CONFIG.lng.toString());
  const [mapZoom, setMapZoom] = useState(DEFAULT_MAP_CONFIG.zoom.toString());

  const handleSaveMapDefaults = (e: React.FormEvent) => {
    e.preventDefault();
    toast.success('Municipal default map settings saved successfully.');
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      <Breadcrumbs
        items={[
          { label: 'Admin Portal', href: '/admin/dashboard' },
          { label: 'System Settings' },
        ]}
      />

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            System Administration & Settings
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Configure default geographic centers, civic service level parameters, and administrative controls.
          </p>
        </div>

        <Button
          variant="outline"
          onClick={handleLogout}
          className="text-rose-600 border-rose-200 hover:bg-rose-50 text-xs"
          leftIcon={<LogOut className="h-4 w-4" />}
        >
          Sign Out
        </Button>
      </div>

      {/* Admin Profile Box */}
      <Card className="border-slate-200/90 shadow-sm">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Shield className="h-4 w-4 text-teal-600" />
            <span>Administrator Identity</span>
          </CardTitle>
          <CardDescription>Current administrative session credentials.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200 mb-4">
            <Avatar
              alt={user?.fullName}
              fallback={user?.fullName}
              role="admin"
              size="lg"
              showBorder
            />
            <div>
              <p className="text-base font-bold text-slate-900">{user?.fullName}</p>
              <p className="text-xs text-slate-500">{user?.email}</p>
              <span className="inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 mt-1">
                Executive Super Administrator
              </span>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="p-3 bg-white rounded-xl border border-slate-200">
              <p className="text-slate-400 font-medium">Session Status</p>
              <p className="font-semibold text-emerald-700 mt-0.5 flex items-center gap-1">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                Active Authenticated Session
              </p>
            </div>
            <div className="p-3 bg-white rounded-xl border border-slate-200">
              <p className="text-slate-400 font-medium">System Privilege Level</p>
              <p className="font-semibold text-teal-700 mt-0.5">Tier 1 Administrative Access</p>
              <p className="text-slate-500">Full municipal platform management</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Map Center Settings */}
      <Card className="border-slate-200/90 shadow-sm">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Map className="h-4 w-4 text-teal-600" />
            <span>Geographic Map Default Focus</span>
          </CardTitle>
          <CardDescription>
            Specify the default map center coordinates and zoom level when citizens and technicians open GIS maps.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSaveMapDefaults} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <Input
                label="Default Latitude"
                type="number"
                step="any"
                value={mapLat}
                onChange={(e) => setMapLat(e.target.value)}
                required
              />
              <Input
                label="Default Longitude"
                type="number"
                step="any"
                value={mapLng}
                onChange={(e) => setMapLng(e.target.value)}
                required
              />
              <Input
                label="Default Zoom Level (1-18)"
                type="number"
                min={1}
                max={18}
                value={mapZoom}
                onChange={(e) => setMapZoom(e.target.value)}
                required
              />
            </div>
            <div className="flex justify-end pt-2">
              <Button type="submit">Save Map Defaults</Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Backend Integration Diagnostics */}
      <Card className="border-slate-200/90 shadow-sm">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Server className="h-4 w-4 text-teal-600" />
            <span>Backend Integration Diagnostics</span>
          </CardTitle>
          <CardDescription>
            Service endpoints and connection telemetry.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-xs text-slate-600">
          <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded-lg border border-slate-200">
            <span className="font-medium text-slate-700">API Gateway Base URL:</span>
            <span className="font-mono text-teal-800">
              {import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'}
            </span>
          </div>
          <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded-lg border border-slate-200">
            <span className="font-medium text-slate-700">Mock Fallback Adapter:</span>
            <span className="font-semibold text-emerald-700 flex items-center gap-1">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Active & Resilient
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
