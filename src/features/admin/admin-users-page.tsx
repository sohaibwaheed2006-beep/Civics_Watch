import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { userService } from '@/services/user-service';
import { departmentService } from '@/services/department-service';
import { createWorkerSchema, CreateWorkerFormData } from '@/schemas/user-schema';
import { UserListItem } from '@/types/user';
import { useToast } from '@/hooks/use-toast';
import { parseApiError } from '@/lib/api-errors';
import { formatRole, formatDate } from '@/lib/formatters';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Modal, ConfirmationDialog } from '@/components/ui/modal';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { TableSkeleton } from '@/components/ui/skeleton';
import { ErrorPanel } from '@/components/ui/error-panel';
import { EmptyState } from '@/components/ui/empty-state';
import { Pagination } from '@/components/data-display/pagination';
import { useDebounce } from '@/hooks/use-debounce';
import { Avatar } from '@/components/ui/avatar';
import {
  UserPlus,
  ShieldAlert,
  Search,
  CheckCircle2,
  XCircle,
  Edit2,
  Mail,
  Lock,
  Phone,
} from 'lucide-react';

export const AdminUsersPage: React.FC = () => {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<'all' | 'citizen' | 'admin' | 'worker'>('all');
  const [page, setPage] = useState(1);

  const [isCreateWorkerOpen, setIsCreateWorkerOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<UserListItem | null>(null);
  const [deactivatingUser, setDeactivatingUser] = useState<UserListItem | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  // Edit fields
  const [editRole, setEditRole] = useState<'citizen' | 'admin' | 'worker'>('worker');
  const [editDeptId, setEditDeptId] = useState('');

  const debouncedSearch = useDebounce(search, 300);

  // Load departments
  const { data: departments = [] } = useQuery({
    queryKey: ['departments-list'],
    queryFn: () => departmentService.getDepartments(),
  });

  // Load users
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin-users-list', debouncedSearch, roleFilter, page],
    queryFn: () =>
      userService.getUsers({
        search: debouncedSearch,
        role: roleFilter,
        page,
        limit: 10,
      }),
  });

  const users = data?.data || [];
  const totalPages = data?.totalPages || 1;
  const totalItems = data?.total || 0;

  // Create Worker Form
  const {
    register: regWorker,
    handleSubmit: handleWorkerSubmit,
    reset: resetWorker,
    formState: { errors: workerErrors, isSubmitting: isCreatingWorker },
  } = useForm<CreateWorkerFormData>({
    resolver: zodResolver(createWorkerSchema),
  });

  // Create Worker Mutation
  const createWorkerMutation = useMutation({
    mutationFn: (formData: CreateWorkerFormData) => userService.createWorker(formData),
    onSuccess: (newWorker) => {
      toast.success(`Technician account created for "${newWorker.fullName}".`);
      queryClient.invalidateQueries({ queryKey: ['admin-users-list'] });
      // Refresh the department lists too so the new hire is reflected in the
      // department's "Active Staff" count immediately, without a manual reload.
      queryClient.invalidateQueries({ queryKey: ['departments-admin-list'] });
      queryClient.invalidateQueries({ queryKey: ['departments-list'] });
      setIsCreateWorkerOpen(false);
      resetWorker();
    },
    onError: (err) => {
      const parsed = parseApiError(err);
      setFormError(parsed.message);
    },
  });

  // Update User Mutation
  const updateUserMutation = useMutation({
    mutationFn: (updateData: any) =>
      editingUser ? userService.updateUser(editingUser.id, updateData) : Promise.reject(),
    onSuccess: () => {
      toast.success('User updated successfully.');
      queryClient.invalidateQueries({ queryKey: ['admin-users-list'] });
      setEditingUser(null);
    },
    onError: (err) => {
      const parsed = parseApiError(err);
      toast.error(parsed.message);
    },
  });

  // Toggle Active Mutation
  const toggleActiveMutation = useMutation({
    mutationFn: (targetUser: UserListItem) =>
      userService.updateUser(targetUser.id, { isActive: !targetUser.isActive }),
    onSuccess: (res) => {
      toast.success(`Account for "${res.fullName}" has been ${res.isActive ? 'activated' : 'deactivated'}.`);
      queryClient.invalidateQueries({ queryKey: ['admin-users-list'] });
      setDeactivatingUser(null);
    },
    onError: (err) => {
      const parsed = parseApiError(err);
      toast.error(parsed.message);
    },
  });

  const onStartEdit = (u: UserListItem) => {
    setEditingUser(u);
    setEditRole(u.role);
    setEditDeptId(u.departmentId || '');
  };

  return (
    <div className="space-y-6">
      <Breadcrumbs
        items={[
          { label: 'Admin Portal', href: '/admin/dashboard' },
          { label: 'User Directory' },
        ]}
      />

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            User Directory & Access Control
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Manage citizens, dispatch field technicians, and maintain role-based access.
          </p>
        </div>

        <Button
          onClick={() => {
            setFormError(null);
            setIsCreateWorkerOpen(true);
          }}
          leftIcon={<UserPlus className="h-4 w-4" />}
        >
          Provision Field Worker
        </Button>
      </div>

      {/* Filter toolbar */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative flex-1 w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search by name or email address..."
            className="w-full pl-9 pr-4 py-2 text-xs rounded-lg border border-slate-300 bg-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-teal-500"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <select
            value={roleFilter}
            onChange={(e) => {
              setRoleFilter(e.target.value as any);
              setPage(1);
            }}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-700 font-medium focus:ring-1 focus:ring-teal-500 w-full sm:w-auto"
          >
            <option value="all">All Roles</option>
            <option value="citizen">Citizens</option>
            <option value="worker">Field Workers</option>
            <option value="admin">Administrators</option>
          </select>
        </div>
      </div>

      {/* Users Table */}
      {isLoading ? (
        <TableSkeleton rows={8} />
      ) : isError ? (
        <ErrorPanel onRetry={refetch} message="Unable to load user accounts." />
      ) : users.length === 0 ? (
        <EmptyState
          title="No users match query"
          description="Try modifying your search or role filters."
        />
      ) : (
        <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">User</th>
                  <th className="py-3 px-4">Role</th>
                  <th className="py-3 px-4">Department</th>
                  <th className="py-3 px-4">Phone</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Joined Date</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <div className="flex items-center gap-2.5">
                        <Avatar
                          alt={u.fullName}
                          fallback={u.fullName}
                          role={u.role}
                          size="sm"
                        />
                        <div>
                          <p className="font-semibold text-slate-900">{u.fullName}</p>
                          <p className="text-[11px] text-slate-500">{u.email}</p>
                        </div>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span
                        className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${
                          u.role === 'admin'
                            ? 'bg-indigo-50 text-indigo-800 border-indigo-200'
                            : u.role === 'worker'
                            ? 'bg-amber-50 text-amber-800 border-amber-200'
                            : 'bg-teal-50 text-teal-800 border-teal-200'
                        }`}
                      >
                        {formatRole(u.role)}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap text-slate-700">
                      {u.departmentName || '—'}
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap text-slate-600">
                      {u.phone || '—'}
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${
                          u.isActive
                            ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                            : 'bg-rose-50 text-rose-800 border-rose-200'
                        }`}
                      >
                        {u.isActive ? (
                          <>
                            <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                            <span>Active</span>
                          </>
                        ) : (
                          <>
                            <XCircle className="h-3 w-3 text-rose-600" />
                            <span>Suspended</span>
                          </>
                        )}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap text-slate-500">
                      {formatDate(u.createdAt)}
                    </td>

                    <td className="py-3.5 px-4 text-right whitespace-nowrap space-x-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onStartEdit(u)}
                        className="text-xs text-slate-600 hover:text-slate-900"
                      >
                        <Edit2 className="h-3.5 w-3.5 mr-1" />
                        Edit
                      </Button>

                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setDeactivatingUser(u)}
                        className={`text-xs ${
                          u.isActive ? 'text-rose-600 hover:bg-rose-50' : 'text-emerald-600 hover:bg-emerald-50'
                        }`}
                      >
                        {u.isActive ? 'Deactivate' : 'Activate'}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pagination */}
      <Pagination
        currentPage={page}
        totalPages={totalPages}
        totalItems={totalItems}
        pageSize={10}
        onPageChange={setPage}
      />

      {/* Modal: Create Worker Account */}
      <Modal
        isOpen={isCreateWorkerOpen}
        onClose={() => setIsCreateWorkerOpen(false)}
        title="Provision Field Technician Account"
        description="Create an authorized field worker profile assigned to a municipal department."
      >
        {formError && (
          <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800 flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-rose-600 shrink-0" />
            <span>{formError}</span>
          </div>
        )}

        <form onSubmit={handleWorkerSubmit((d) => createWorkerMutation.mutate(d))} className="space-y-4">
          <Input
            label="Full Name"
            placeholder="Dave Miller"
            error={workerErrors.fullName?.message}
            required
            {...regWorker('fullName')}
          />

          <Input
            label="Email Address"
            type="email"
            placeholder="worker@example.com"
            leftIcon={<Mail className="h-4 w-4" />}
            error={workerErrors.email?.message}
            required
            {...regWorker('email')}
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              label="Temporary Password"
              type="password"
              placeholder="••••••••"
              leftIcon={<Lock className="h-4 w-4" />}
              error={workerErrors.password?.message}
              required
              {...regWorker('password')}
            />

            <Input
              label="Contact Phone"
              type="tel"
              placeholder="+1 (555) 000-0000"
              leftIcon={<Phone className="h-4 w-4" />}
              error={workerErrors.phone?.message}
              {...regWorker('phone')}
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Assigned Department <span className="text-rose-500">*</span>
            </label>
            <select
              className="w-full rounded-lg border border-slate-300 bg-white p-2.5 text-xs focus:ring-1 focus:ring-teal-500"
              {...regWorker('departmentId')}
            >
              <option value="">Select a department...</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
            {workerErrors.departmentId && (
              <p className="text-xs text-rose-600 mt-1">{workerErrors.departmentId.message}</p>
            )}
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
            <Button type="button" variant="outline" onClick={() => setIsCreateWorkerOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isCreatingWorker}>
              Provision Worker
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Edit User Role & Department */}
      <Modal
        isOpen={Boolean(editingUser)}
        onClose={() => setEditingUser(null)}
        title={`Edit User: ${editingUser?.fullName}`}
        description="Update role privileges or department association."
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">System Role</label>
            <select
              value={editRole}
              onChange={(e) => setEditRole(e.target.value as any)}
              className="w-full rounded-lg border border-slate-300 bg-white p-2.5 text-xs focus:ring-1 focus:ring-teal-500"
            >
              <option value="citizen">Citizen</option>
              <option value="worker">Field Worker</option>
              <option value="admin">Administrator</option>
            </select>
          </div>

          {editRole === 'worker' && (
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Assigned Department
              </label>
              <select
                value={editDeptId}
                onChange={(e) => setEditDeptId(e.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white p-2.5 text-xs focus:ring-1 focus:ring-teal-500"
              >
                <option value="">No Department</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
            <Button variant="outline" onClick={() => setEditingUser(null)}>
              Cancel
            </Button>
            <Button
              onClick={() =>
                updateUserMutation.mutate({
                  role: editRole,
                  departmentId: editRole === 'worker' ? editDeptId : undefined,
                })
              }
              isLoading={updateUserMutation.isPending}
            >
              Save Permissions
            </Button>
          </div>
        </div>
      </Modal>

      {/* Confirmation: Safe Deactivation */}
      {deactivatingUser && (
        <ConfirmationDialog
          isOpen={Boolean(deactivatingUser)}
          onClose={() => setDeactivatingUser(null)}
          onConfirm={() => toggleActiveMutation.mutate(deactivatingUser)}
          title={deactivatingUser.isActive ? 'Suspend User Account?' : 'Reactivate User Account?'}
          description={
            deactivatingUser.isActive
              ? `Are you sure you want to suspend "${deactivatingUser.fullName}" (${deactivatingUser.email})? Suspended users will not be able to log in.`
              : `Reactivate account for "${deactivatingUser.fullName}" to restore platform access.`
          }
          confirmText={deactivatingUser.isActive ? 'Suspend Account' : 'Reactivate Account'}
          variant={deactivatingUser.isActive ? 'danger' : 'primary'}
          isLoading={toggleActiveMutation.isPending}
        />
      )}
    </div>
  );
};
