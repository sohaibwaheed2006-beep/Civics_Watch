import { ReportCategory, ReportPriority, ReportStatus } from '@/types/report';
import { Role } from '@/types/auth';

export const APP_NAME = import.meta.env.VITE_APP_NAME || 'Neighborhood Issue Reporter';
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export const DEFAULT_MAP_CONFIG = {
  lat: Number(import.meta.env.VITE_MAP_DEFAULT_LAT) || 40.7128,
  lng: Number(import.meta.env.VITE_MAP_DEFAULT_LNG) || -74.006,
  zoom: Number(import.meta.env.VITE_MAP_DEFAULT_ZOOM) || 13,
};

export const CATEGORY_DETAILS: Record<
  ReportCategory,
  { label: string; description: string; iconName: string; color: string }
> = {
  road_damage: {
    label: 'Road Damage / Pothole',
    description: 'Potholes, cracked asphalt, missing manhole covers, unsafe road surfaces.',
    iconName: 'AlertTriangle',
    color: 'text-amber-600 bg-amber-50 border-amber-200',
  },
  streetlight: {
    label: 'Streetlight Outage',
    description: 'Broken, flickering, or non-functioning streetlights and public lighting.',
    iconName: 'Lightbulb',
    color: 'text-yellow-600 bg-yellow-50 border-yellow-200',
  },
  garbage_waste: {
    label: 'Garbage & Waste',
    description: 'Illegal dumping, uncollected municipal waste, overflowing public bins.',
    iconName: 'Trash2',
    color: 'text-rose-600 bg-rose-50 border-rose-200',
  },
  water_leak: {
    label: 'Water Main Leak',
    description: 'Burst pipes, pooling clean water, municipal main leaks.',
    iconName: 'Droplets',
    color: 'text-sky-600 bg-sky-50 border-sky-200',
  },
  drainage: {
    label: 'Blocked Drainage',
    description: 'Clogged storm drains, flooded culverts, stormwater backup.',
    iconName: 'Waves',
    color: 'text-indigo-600 bg-indigo-50 border-indigo-200',
  },
  public_property: {
    label: 'Damaged Public Property',
    description: 'Vandalism, broken park benches, damaged bus shelters, playground issues.',
    iconName: 'Building2',
    color: 'text-purple-600 bg-purple-50 border-purple-200',
  },
  other: {
    label: 'Other Infrastructure Issue',
    description: 'Miscellaneous civic hazards, overgrown public trees, obstructed sidewalks.',
    iconName: 'HelpCircle',
    color: 'text-slate-600 bg-slate-50 border-slate-200',
  },
};

export const STATUS_DETAILS: Record<
  ReportStatus,
  {
    label: string;
    description: string;
    bgClass: string;
    textClass: string;
    dotClass: string;
    borderClass: string;
  }
> = {
  submitted: {
    label: 'Submitted',
    description: 'Report created and queued for review.',
    bgClass: 'bg-slate-100',
    textClass: 'text-slate-700',
    dotClass: 'bg-slate-400',
    borderClass: 'border-slate-200',
  },
  under_review: {
    label: 'Under Review',
    description: 'Assigned to administration for assessment.',
    bgClass: 'bg-amber-100',
    textClass: 'text-amber-800',
    dotClass: 'bg-amber-500',
    borderClass: 'border-amber-300',
  },
  assigned: {
    label: 'Assigned',
    description: 'Dispatched to a designated department and worker.',
    bgClass: 'bg-blue-100',
    textClass: 'text-blue-800',
    dotClass: 'bg-blue-500',
    borderClass: 'border-blue-300',
  },
  in_progress: {
    label: 'In Progress',
    description: 'Field workers are actively addressing the problem.',
    bgClass: 'bg-teal-100',
    textClass: 'text-teal-800',
    dotClass: 'bg-teal-500',
    borderClass: 'border-teal-300',
  },
  resolved: {
    label: 'Resolved',
    description: 'Issue inspected and successfully remediated.',
    bgClass: 'bg-emerald-100',
    textClass: 'text-emerald-800',
    dotClass: 'bg-emerald-500',
    borderClass: 'border-emerald-300',
  },
  rejected: {
    label: 'Rejected',
    description: 'Determined duplicate, non-civic, or outside jurisdiction.',
    bgClass: 'bg-rose-100',
    textClass: 'text-rose-800',
    dotClass: 'bg-rose-500',
    borderClass: 'border-rose-300',
  },
  reopened: {
    label: 'Reopened',
    description: 'Reopened due to recurring issue or insufficient fix.',
    bgClass: 'bg-purple-100',
    textClass: 'text-purple-800',
    dotClass: 'bg-purple-500',
    borderClass: 'border-purple-300',
  },
};

export const PRIORITY_DETAILS: Record<
  ReportPriority,
  { label: string; bgClass: string; textClass: string; borderClass: string }
> = {
  low: {
    label: 'Low',
    bgClass: 'bg-slate-100',
    textClass: 'text-slate-700',
    borderClass: 'border-slate-200',
  },
  medium: {
    label: 'Medium',
    bgClass: 'bg-blue-100',
    textClass: 'text-blue-800',
    borderClass: 'border-blue-200',
  },
  high: {
    label: 'High',
    bgClass: 'bg-amber-100',
    textClass: 'text-amber-800',
    borderClass: 'border-amber-200',
  },
  urgent: {
    label: 'Urgent',
    bgClass: 'bg-red-100',
    textClass: 'text-red-800',
    borderClass: 'border-red-200',
  },
};

export const ROLE_DETAILS: Record<
  Role,
  { label: string; badgeClass: string; description: string }
> = {
  citizen: {
    label: 'Citizen',
    badgeClass: 'bg-teal-100 text-teal-800 border-teal-200',
    description: 'Community resident submitting and tracking reports',
  },
  admin: {
    label: 'Administrator',
    badgeClass: 'bg-indigo-100 text-indigo-800 border-indigo-200',
    description: 'Municipal official managing issues, departments and staff',
  },
  worker: {
    label: 'Field Worker',
    badgeClass: 'bg-amber-100 text-amber-800 border-amber-200',
    description: 'Field specialist handling repair assignments and resolution',
  },
};
