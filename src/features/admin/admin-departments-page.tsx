import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { departmentService } from '@/services/department-service';
import { departmentSchema, DepartmentFormData } from '@/schemas/department-schema';
import { Department } from '@/types/department';
import { useToast } from '@/hooks/use-toast';
import { parseApiError } from '@/lib/api-errors';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Modal, ConfirmationDialog } from '@/components/ui/modal';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { TableSkeleton } from '@/components/ui/skeleton';
import { ErrorPanel } from '@/components/ui/error-panel';
import { EmptyState } from '@/components/ui/empty-state';
import { Building, Plus, Edit2, ShieldAlert, CheckCircle2, XCircle, Users, Clock } from 'lucide-react';

export const AdminDepartmentsPage: React.FC = () => {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingDept, setEditingDept] = useState<Department | null>(null);
  const [deactivatingDept, setDeactivatingDept] = useState<Department | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  // Load departments
  const { data: departments = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['departments-admin-list'],
    queryFn: () => departmentService.getDepartments(),
  });

  // Create Department form
  const {
    register: regCreate,
    handleSubmit: handleCreateSubmit,
    reset: resetCreate,
    formState: { errors: createErrors, isSubmitting: isCreating },
  } = useForm<DepartmentFormData>({
    resolver: zodResolver(departmentSchema),
    defaultValues: {
      name: '',
      description: '',
      defaultSlaHours: 24,
    },
  });

  // Edit Department form
  const {
    register: regEdit,
    handleSubmit: handleEditSubmit,
    reset: resetEdit,
    formState: { errors: editErrors, isSubmitting: isEditing },
  } = useForm<DepartmentFormData>({
    resolver: zodResolver(departmentSchema),
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: DepartmentFormData) => departmentService.createDepartment(data),
    onSuccess: (newDept) => {
      toast.success(`Department "${newDept.name}" created successfully.`);
      queryClient.invalidateQueries({ queryKey: ['departments-admin-list'] });
      setIsCreateOpen(false);
      resetCreate();
    },
    onError: (err) => {
      const parsed = parseApiError(err);
      setFormError(parsed.message);
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (data: DepartmentFormData) =>
      editingDept ? departmentService.updateDepartment(editingDept.id, data) : Promise.reject(),
    onSuccess: (updated) => {
      toast.success(`Department "${updated.name}" updated successfully.`);
      queryClient.invalidateQueries({ queryKey: ['departments-admin-list'] });
      setEditingDept(null);
    },
    onError: (err) => {
      const parsed = parseApiError(err);
      setFormError(parsed.message);
    },
  });

  // Deactivate mutation
  const toggleActiveMutation = useMutation({
    mutationFn: (dept: Department) =>
      departmentService.updateDepartment(dept.id, { isActive: !dept.isActive }),
    onSuccess: (dept) => {
      toast.success(`Department "${dept.name}" ${dept.isActive ? 'activated' : 'deactivated'}.`);
      queryClient.invalidateQueries({ queryKey: ['departments-admin-list'] });
      setDeactivatingDept(null);
    },
    onError: () => toast.error('Failed to change department status.'),
  });

  const onStartEdit = (dept: Department) => {
    setFormError(null);
    setEditingDept(dept);
    resetEdit({
      name: dept.name,
      description: dept.description,
      defaultSlaHours: dept.defaultSlaHours,
    });
  };

  return (
    <div className="space-y-6">
      <Breadcrumbs
        items={[
          { label: 'Admin Portal', href: '/admin/dashboard' },
          { label: 'Department Management' },
        ]}
      />

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Municipal Departments & SLAs
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Configure municipal departments, default response SLAs, and monitor worker capacity.
          </p>
        </div>

        <Button
          onClick={() => {
            setFormError(null);
            setIsCreateOpen(true);
          }}
          leftIcon={<Plus className="h-4 w-4" />}
        >
          Add Department
        </Button>
      </div>

      {/* Departments Table */}
      {isLoading ? (
        <TableSkeleton rows={5} />
      ) : isError ? (
        <ErrorPanel onRetry={refetch} message="Unable to load departments." />
      ) : departments.length === 0 ? (
        <EmptyState
          title="No departments found"
          description="Create your first municipal department to begin routing citizen issues."
          actionText="Create Department"
          onAction={() => setIsCreateOpen(true)}
        />
      ) : (
        <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Department Name</th>
                  <th className="py-3 px-4">Description</th>
                  <th className="py-3 px-4">Standard SLA</th>
                  <th className="py-3 px-4">Active Staff</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {departments.map((dept) => (
                  <tr key={dept.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4 font-semibold text-slate-900 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <Building className="h-4 w-4 text-teal-600" />
                        <span>{dept.name}</span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 max-w-sm text-slate-600 truncate">
                      {dept.description}
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <div className="flex items-center gap-1.5 font-medium text-slate-800">
                        <Clock className="h-3.5 w-3.5 text-slate-400" />
                        <span>{dept.defaultSlaHours} hours</span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <div className="flex items-center gap-1.5 font-medium text-slate-700">
                        <Users className="h-3.5 w-3.5 text-slate-400" />
                        <span>{dept.workerCount || 0} technicians</span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${
                          dept.isActive
                            ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                            : 'bg-slate-100 text-slate-600 border-slate-200'
                        }`}
                      >
                        {dept.isActive ? (
                          <>
                            <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                            <span>Active</span>
                          </>
                        ) : (
                          <>
                            <XCircle className="h-3 w-3 text-slate-400" />
                            <span>Inactive</span>
                          </>
                        )}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 text-right whitespace-nowrap space-x-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onStartEdit(dept)}
                        className="text-xs text-slate-600 hover:text-slate-900"
                      >
                        <Edit2 className="h-3.5 w-3.5 mr-1" />
                        Edit
                      </Button>

                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setDeactivatingDept(dept)}
                        className={`text-xs ${
                          dept.isActive
                            ? 'text-rose-600 hover:bg-rose-50'
                            : 'text-emerald-600 hover:bg-emerald-50'
                        }`}
                      >
                        {dept.isActive ? 'Deactivate' : 'Activate'}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal: Create Department */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Add Municipal Department"
        description="Establish a new department for managing specific categories of civic issues."
      >
        {formError && (
          <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800 flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-rose-600 shrink-0" />
            <span>{formError}</span>
          </div>
        )}

        <form onSubmit={handleCreateSubmit((d) => createMutation.mutate(d))} className="space-y-4">
          <Input
            label="Department Name"
            placeholder="e.g. Roads & Infrastructure"
            error={createErrors.name?.message}
            required
            {...regCreate('name')}
          />

          <Textarea
            label="Description & Jurisdiction"
            rows={3}
            placeholder="Types of infrastructure and services this department manages..."
            error={createErrors.description?.message}
            required
            {...regCreate('description')}
          />

          <Input
            label="Default SLA Target (Hours)"
            type="number"
            min={1}
            max={720}
            error={createErrors.defaultSlaHours?.message}
            required
            {...regCreate('defaultSlaHours', { valueAsNumber: true })}
          />

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
            <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isCreating}>
              Create Department
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Edit Department */}
      <Modal
        isOpen={Boolean(editingDept)}
        onClose={() => setEditingDept(null)}
        title="Edit Department"
        description="Modify department details and response service level targets."
      >
        {formError && (
          <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800 flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-rose-600 shrink-0" />
            <span>{formError}</span>
          </div>
        )}

        <form onSubmit={handleEditSubmit((d) => updateMutation.mutate(d))} className="space-y-4">
          <Input
            label="Department Name"
            error={editErrors.name?.message}
            required
            {...regEdit('name')}
          />

          <Textarea
            label="Description"
            rows={3}
            error={editErrors.description?.message}
            required
            {...regEdit('description')}
          />

          <Input
            label="Default SLA Target (Hours)"
            type="number"
            min={1}
            max={720}
            error={editErrors.defaultSlaHours?.message}
            required
            {...regEdit('defaultSlaHours', { valueAsNumber: true })}
          />

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
            <Button type="button" variant="outline" onClick={() => setEditingDept(null)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isEditing}>
              Save Changes
            </Button>
          </div>
        </form>
      </Modal>

      {/* Safe Deactivation Confirmation */}
      {deactivatingDept && (
        <ConfirmationDialog
          isOpen={Boolean(deactivatingDept)}
          onClose={() => setDeactivatingDept(null)}
          onConfirm={() => toggleActiveMutation.mutate(deactivatingDept)}
          title={deactivatingDept.isActive ? 'Deactivate Department?' : 'Reactivate Department?'}
          description={
            deactivatingDept.isActive
              ? `Are you sure you want to deactivate "${deactivatingDept.name}"? New reports cannot be assigned to inactive departments, but historical records will remain intact.`
              : `Reactivate "${deactivatingDept.name}" to allow new work orders and technician dispatch.`
          }
          confirmText={deactivatingDept.isActive ? 'Deactivate Department' : 'Activate Department'}
          variant={deactivatingDept.isActive ? 'danger' : 'primary'}
          isLoading={toggleActiveMutation.isPending}
        />
      )}
    </div>
  );
};
