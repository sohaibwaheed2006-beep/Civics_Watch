import { z } from 'zod';

export const createWorkerSchema = z.object({
  fullName: z.string().min(2, 'Name must be at least 2 characters').max(100),
  email: z.string().email('Valid email address required'),
  password: z.string().min(6, 'Temporary password must be at least 6 characters'),
  phone: z.string().optional().or(z.literal('')),
  departmentId: z.string().min(1, 'Please assign a department'),
});

export type CreateWorkerFormData = z.infer<typeof createWorkerSchema>;

export const updateUserSchema = z.object({
  fullName: z.string().min(2, 'Name must be at least 2 characters').max(100),
  phone: z.string().optional().or(z.literal('')),
  role: z.enum(['citizen', 'admin', 'worker']),
  departmentId: z.string().optional().or(z.literal('')),
  isActive: z.boolean(),
});

export type UpdateUserFormData = z.infer<typeof updateUserSchema>;
