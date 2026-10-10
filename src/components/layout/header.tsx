import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/use-auth';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notificationService } from '@/services/notification-service';
import { ROLE_DETAILS } from '@/lib/constants';
import { Bell, Menu, User, LogOut, CheckCheck, ArrowRight, ShieldCheck } from 'lucide-react';
import { formatRelativeTime } from '@/lib/formatters';

export interface HeaderProps {
  onToggleSidebar: () => void;
  onToggleMobileMenu: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onToggleSidebar, onToggleMobileMenu }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  // Notifications query
  const { data: notifications = [] } = useQuery({
    queryKey: ['notifications', user?.id],
    queryFn: () => (user ? notificationService.getNotifications(user.id) : []),
    enabled: Boolean(user?.id),
    refetchInterval: 30000, // gentle background polling
  });

  const unreadCount = notifications.filter((n) => !n.isRead).length;

  // Mark all read mutation
  const markAllMutation = useMutation({
    mutationFn: () => (user ? notificationService.markAllAsRead(user.id) : Promise.resolve()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications', user?.id] });
    },
  });

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const roleInfo = user ? ROLE_DETAILS[user.role] : null;

  const getProfileRoute = () => {
    if (!user) return '/login';
    switch (user.role) {
      case 'citizen':
        return '/citizen/profile';
      case 'worker':
        return '/worker/profile';
      case 'admin':
        return '/admin/settings';
    }
  };

  const getNotificationsRoute = () => {
    if (!user) return '/login';
    switch (user.role) {
      case 'citizen':
        return '/citizen/notifications';
      case 'worker':
        return '/worker/notifications';
      case 'admin':
        return '/admin/notifications';
    }
  };

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-slate-200 bg-white/90 px-4 sm:px-6 backdrop-blur-md">
      {/* Left section: Hamburger & brand indicator */}
      <div className="flex items-center gap-3">
        {/* Mobile menu trigger */}
        <button
          onClick={onToggleMobileMenu}
          className="lg:hidden p-2 rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-800 transition-colors"
          aria-label="Open navigation menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* Desktop sidebar collapse trigger */}
        <button
          onClick={onToggleSidebar}
          className="hidden lg:flex p-2 rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-800 transition-colors"
          aria-label="Toggle sidebar collapse"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-slate-800 hidden sm:inline">
            Neighborhood Issue Reporter
          </span>
          {roleInfo && (
            <span
              className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${roleInfo.badgeClass}`}
            >
              {roleInfo.label}
            </span>
          )}
        </div>
      </div>

      {/* Right section: Notifications bell & user profile dropdown */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Notifications Popover */}
        <div className="relative">
          <button
            onClick={() => setIsNotifOpen((prev) => !prev)}
            className="relative p-2 rounded-full text-slate-500 hover:bg-slate-100 hover:text-slate-800 transition-colors"
            aria-label="Open notifications"
          >
            <Bell className="h-5 w-5" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 flex h-4 w-4 items-center justify-center rounded-full bg-teal-600 text-[10px] font-bold text-white shadow-sm ring-2 ring-white">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {isNotifOpen && (
            <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl border border-slate-200 bg-white shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2">
              <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3 bg-slate-50/50">
                <div className="flex items-center gap-2">
                  <h4 className="text-xs font-semibold text-slate-900">Notifications</h4>
                  {unreadCount > 0 && (
                    <span className="rounded-full bg-teal-100 px-1.5 py-0.2 text-[10px] font-semibold text-teal-800">
                      {unreadCount} new
                    </span>
                  )}
                </div>
                {unreadCount > 0 && (
                  <button
                    onClick={() => markAllMutation.mutate()}
                    className="text-[11px] font-medium text-teal-600 hover:text-teal-800 flex items-center gap-1"
                  >
                    <CheckCheck className="h-3 w-3" />
                    Mark all read
                  </button>
                )}
              </div>

              {/* Notification list */}
              <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
                {notifications.length === 0 ? (
                  <div className="p-6 text-center text-xs text-slate-400">
                    No notifications right now.
                  </div>
                ) : (
                  notifications.slice(0, 5).map((notif) => (
                    <div
                      key={notif.id}
                      className={`p-3.5 text-xs transition-colors hover:bg-slate-50 ${
                        !notif.isRead ? 'bg-teal-50/30' : ''
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <p className="font-semibold text-slate-800">{notif.title}</p>
                        <span className="text-[10px] text-slate-400">
                          {formatRelativeTime(notif.createdAt)}
                        </span>
                      </div>
                      <p className="mt-1 text-slate-600 leading-relaxed">{notif.message}</p>
                    </div>
                  ))
                )}
              </div>

              <div className="border-t border-slate-100 bg-slate-50/50 p-2 text-center">
                <Link
                  to={getNotificationsRoute()}
                  onClick={() => setIsNotifOpen(false)}
                  className="inline-flex items-center gap-1 text-xs font-medium text-teal-600 hover:text-teal-800"
                >
                  <span>View all notifications</span>
                  <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
            </div>
          )}
        </div>

        {/* User profile dropdown */}
        <div className="relative">
          <button
            onClick={() => setIsUserMenuOpen((prev) => !prev)}
            className="flex items-center gap-2 rounded-xl p-1.5 hover:bg-slate-100 transition-colors"
            aria-label="User profile menu"
          >
            <div className="h-8 w-8 rounded-full bg-teal-600 text-white flex items-center justify-center font-semibold text-xs shadow-sm ring-2 ring-teal-100">
              {user?.fullName ? user.fullName[0].toUpperCase() : 'U'}
            </div>
            <div className="text-left hidden md:block">
              <p className="text-xs font-semibold text-slate-800 leading-none">{user?.fullName}</p>
              <p className="text-[10px] text-slate-500 mt-0.5 leading-none">{user?.email}</p>
            </div>
          </button>

          {isUserMenuOpen && (
            <div className="absolute right-0 mt-2 w-56 rounded-xl border border-slate-200 bg-white shadow-xl z-50 py-1 animate-in fade-in slide-in-from-top-2">
              <div className="px-4 py-2.5 border-b border-slate-100">
                <p className="text-xs font-semibold text-slate-900">{user?.fullName}</p>
                <p className="text-[11px] text-slate-500 truncate">{user?.email}</p>
                <div className="mt-1.5 flex items-center gap-1 text-[11px] text-teal-700 font-medium">
                  <ShieldCheck className="h-3.5 w-3.5 text-teal-600" />
                  <span className="capitalize">{user?.role} Portal</span>
                </div>
              </div>

              <Link
                to={getProfileRoute()}
                onClick={() => setIsUserMenuOpen(false)}
                className="flex items-center gap-2 px-4 py-2 text-xs text-slate-700 hover:bg-slate-50 transition-colors"
              >
                <User className="h-3.5 w-3.5 text-slate-400" />
                <span>My Profile & Settings</span>
              </Link>

              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-4 py-2 text-xs text-rose-600 hover:bg-rose-50 transition-colors border-t border-slate-100"
              >
                <LogOut className="h-3.5 w-3.5 text-rose-500" />
                <span>Sign Out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
