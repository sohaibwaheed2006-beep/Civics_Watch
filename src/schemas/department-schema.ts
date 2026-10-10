import { z } from 'zod';

export const departmentSchema = z.object({
  name: z
    .string()
    .min(2, 'Department name must be at least 2 characters')
    .max(80, 'Department name cannot exceed 80 characters'),
  description: z
    .string()
    .min(5, 'Description must be at least 5 characters')
    .max(500, 'Description cannot exceed 500 characters'),
  defaultSlaHours: z
    .number({ invalid_type_error: 'SLA hours must be a number' })
    .int('Must be a whole number')
    .positive('SLA hours must be greater than 0')
    .max(720, 'SLA cannot exceed 30 days (720 hours)'),
});

export type DepartmentFormData = z.infer<typeof departmentSchema>;
