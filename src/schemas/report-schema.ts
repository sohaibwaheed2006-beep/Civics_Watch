import { z } from 'zod';

export const reportCategories = [
  'road_damage',
  'streetlight',
  'garbage_waste',
  'water_leak',
  'drainage',
  'public_property',
  'other',
] as const;

export const reportStatuses = [
  'submitted',
  'under_review',
  'assigned',
  'in_progress',
  'resolved',
  'rejected',
  'reopened',
] as const;

export const reportPriorities = ['low', 'medium', 'high', 'urgent'] as const;

export const createReportSchema = z.object({
  title: z
    .string()
    .min(5, 'Title must be at least 5 characters')
    .max(100, 'Title cannot exceed 100 characters'),
  description: z
    .string()
    .min(15, 'Please provide more details (minimum 15 characters)')
    .max(2000, 'Description cannot exceed 2000 characters'),
  category: z.enum(reportCategories, {
    errorMap: () => ({ message: 'Please select a valid problem category' }),
  }),
  latitude: z
    .number({ invalid_type_error: 'Latitude is required. Click on the map or use GPS.' })
    .min(-90, 'Latitude must be between -90 and 90')
    .max(90, 'Latitude must be between -90 and 90'),
  longitude: z
    .number({ invalid_type_error: 'Longitude is required. Click on the map or use GPS.' })
    .min(-180, 'Longitude must be between -180 and 180')
    .max(180, 'Longitude must be between -180 and 180'),
  address: z.string().max(255, 'Address is too long').optional(),
});

export type CreateReportFormData = z.infer<typeof createReportSchema>;

export const updateReportStatusSchema = z.object({
  status: z.enum(reportStatuses, {
    errorMap: () => ({ message: 'Select a valid status' }),
  }),
  note: z.string().max(1000).optional(),
  resolutionEvidenceUrl: z.string().url('Invalid evidence URL').optional().or(z.literal('')),
});

export type UpdateReportStatusFormData = z.infer<typeof updateReportStatusSchema>;

export const assignReportSchema = z.object({
  workerId: z.string().min(1, 'Please select a field worker'),
  departmentId: z.string().min(1, 'Department is required'),
  priority: z.enum(reportPriorities).optional(),
  deadline: z.string().optional(),
  note: z.string().max(500).optional(),
});

export type AssignReportFormData = z.infer<typeof assignReportSchema>;
