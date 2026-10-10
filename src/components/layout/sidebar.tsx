import React from 'react';
import { NavLink, Link } from 'react-router-dom';
import { useAuth } from '@/hooks/use-auth';
import {
  LayoutDashboard,
  FileText,
  PlusCircle,
  Map,
  Users,
  Building,
  BarChart3,
  Settings,
  Bell,
  User,
  ClipboardList,
  CheckCircle,
  Shield,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export interface SidebarProps {
  isCollapsed: boolean;
  onCloseMobile?: () => void;
}

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  badge?: string;
  isSpecial?: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({ isCollapsed, onCloseMobile }) => {
  const { user } = useAuth();

  const getNavItems = (): NavItem[] => {
    if (!user) return [];

    switch (user.role) {
      case 'citizen':
        return [
          {
            label: 'Dashboard',
            href: '/citizen/dashboard',
            icon: <LayoutDashboard className="h-4 w-4" />,
          },
          {
            label: 'Report an Issue',
            href: '/citizen/reports/new',
            icon: <PlusCircle className="h-4 w-4 text-teal-600" />,
            isSpecial: true,
          },
          {
            label: 'My Reports',
            href: '/citizen/reports',
            icon: <FileText className="h-4 w-4" />,
          },
          {
            label: 'Issue Map',
            href: '/citizen/map',
            icon: <Map className="h-4 w-4" />,
          },
          {
            label: 'Notifications',
            href: '/citizen/notifications',
            icon: <Bell className="h-4 w-4" />,
          },
          {
            label: 'My Profile',
            href: '/citizen/profile',
            icon: <User className="h-4 w-4" />,
          },
        ];

      case 'admin':
        return [
          {
            label: 'Dashboard',
            href: '/admin/dashboard',
            icon: <LayoutDashboard className="h-4 w-4" />,
          },
          {
            label: 'Report Management',
            href: '/admin/reports',
            icon: <FileText className="h-4 w-4" />,
          },
          {
            label: 'Issue Map',
            href: '/admin/map',
            icon: <Map className="h-4 w-4" />,
          },
          {
            label: 'Assignments',
            href: '/admin/assignments',
            icon: <ClipboardList className="h-4 w-4" />,
          },
          {
            label: 'Departments',
            href: '/admin/departments',
            icon: <Building className="h-4 w-4" />,
          },
          {
            label: 'User Directory',
            href: '/admin/users',
            icon: <Users className="h-4 w-4" />,
          },
          {
            label: 'Analytics & SLA',
            href: '/admin/analytics',
            icon: <BarChart3 className="h-4 w-4" />,
          },
          {
            label: 'Notifications',
            href: '/admin/notifications',
            icon: <Bell className="h-4 w-4" />,
          },
          {
            label: 'Settings',
            href: '/admin/settings',
            icon: <Settings className="h-4 w-4" />,
          },
        ];

      case 'worker':
        return [
          {
            label: 'Field Dashboard',
            href: '/worker/dashboard',
            icon: <LayoutDashboard className="h-4 w-4" />,
          },
          {
            label: 'My Work Orders',
            href: '/worker/assignments',
            icon: <CheckCircle className="h-4 w-4" />,
          },
          {
            label: 'Field Map',
            href: '/worker/map',
            icon: <Map className="h-4 w-4" />,
          },
          {
            label: 'Notifications',
            href: '/worker/notifications',
            icon: <Bell className="h-4 w-4" />,
          },
          {
            label: 'Profile',
            href: '/worker/profile',
            icon: <User className="h-4 w-4" />,
          },
        ];
    }
  };

  const navItems = getNavItems();

  return (
    <aside
      className={cn(
        'flex flex-col border-r border-slate-200 bg-white transition-all duration-300 z-40',
        isCollapsed ? 'w-20' : 'w-64'
      )}
    >
      {/* Brand logo header */}
      <div className="flex h-16 items-center px-5 border-b border-slate-100">
        <Link to="/dashboard" className="flex items-center gap-2.5 overflow-hidden">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-teal-600 text-white shadow-md shadow-teal-600/20">
            <Shield className="h-5 w-5" />
          </div>
          {!isCollapsed && (
            <div className="leading-none">
              <span className="font-bold text-slate-900 text-sm tracking-tight">CivicWatch</span>
              <p className="text-[10px] text-teal-700 font-semibold mt-0.5">Issue Reporter</p>
            </div>
          )}
        </Link>
      </div>

      {/* Navigation links */}
      <nav className="flex-1 space-y-1.5 p-3 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.href}
            to={item.href}
            onClick={onCloseMobile}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-xl px-3 py-2.5 text-xs font-medium transition-all group',
                isActive
                  ? 'bg-teal-50 text-teal-800 font-semibold border border-teal-200/80 shadow-sm'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
                item.isSpecial &&
                  !isActive &&
                  'bg-teal-600/10 text-teal-800 hover:bg-teal-600/20 font-semibold'
              )
            }
            title={isCollapsed ? item.label : undefined}
          >
            <div className="shrink-0">{item.icon}</div>
            {!isCollapsed && <span className="truncate">{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Footer Role Card */}
      {!isCollapsed && user && (
        <div className="p-3 border-t border-slate-100">
          <div className="rounded-xl bg-slate-50 border border-slate-200/80 p-3">
            <p className="text-xs font-semibold text-slate-800 truncate">{user.fullName}</p>
            <p className="text-[11px] text-slate-500 capitalize">{user.role} role</p>
            {user.departmentName && (
              <p className="text-[10px] text-teal-700 font-medium truncate mt-1">
                {user.departmentName}
              </p>
            )}
          </div>
        </div>
      )}
    </aside>
  );
};
