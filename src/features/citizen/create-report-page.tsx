import React, { useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate } from 'react-router-dom';
import { createReportSchema, CreateReportFormData } from '@/schemas/report-schema';
import { useAuth } from '@/hooks/use-auth';
import { useToast } from '@/hooks/use-toast';
import { reportService } from '@/services/report-service';
import { parseApiError } from '@/lib/api-errors';
import { CATEGORY_DETAILS } from '@/lib/constants';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { LocationPicker } from '@/components/maps/location-picker';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import {
  UploadCloud,
  X,
  AlertTriangle,
  Send,
  Info,
  CheckCircle2,
} from 'lucide-react';
import { ReportCategory } from '@/types/report';

export const CreateReportPage: React.FC = () => {
  const { user } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();

  const [photos, setPhotos] = useState<File[]>([]);
  const [photoPreviews, setPhotoPreviews] = useState<string[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<CreateReportFormData>({
    resolver: zodResolver(createReportSchema),
    defaultValues: {
      title: '',
      description: '',
      category: 'road_damage',
      latitude: undefined,
      longitude: undefined,
      address: '',
    },
  });

  const enteredTitle = watch('title');

  // Handle Photo File selection
  const handlePhotoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUploadError(null);
    if (!e.target.files) return;

    const files = Array.from(e.target.files);
    const validFiles: File[] = [];
    const validPreviews: string[] = [];

    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
    const maxSize = 5 * 1024 * 1024; // 5 MB

    for (const file of files) {
      if (!allowedTypes.includes(file.type)) {
        setUploadError('Only JPG, PNG, and WebP images are supported.');
        return;
      }
      if (file.size > maxSize) {
        setUploadError(`File "${file.name}" exceeds maximum allowed size of 5MB.`);
        return;
      }
      validFiles.push(file);
      validPreviews.push(URL.createObjectURL(file));
    }

    if (photos.length + validFiles.length > 5) {
      setUploadError('You can upload a maximum of 5 photos per report.');
      return;
    }

    setPhotos((prev) => [...prev, ...validFiles]);
    setPhotoPreviews((prev) => [...prev, ...validPreviews]);
  };

  const handleRemovePhoto = (index: number) => {
    URL.revokeObjectURL(photoPreviews[index]);
    setPhotos((prev) => prev.filter((_, i) => i !== index));
    setPhotoPreviews((prev) => prev.filter((_, i) => i !== index));
  };

  // Submit report
  const onSubmit = async (data: CreateReportFormData) => {
    if (!user) {
      toast.error('You must be logged in to submit a report.');
      return;
    }

    setServerError(null);
    try {
      const created = await reportService.createReport(
        {
          ...data,
          photos,
        },
        user
      );

      toast.success('Your report was submitted successfully! Municipal crews have been notified.');
      navigate(`/citizen/reports/${created.id}`);
    } catch (err) {
      const parsed = parseApiError(err);
      setServerError(parsed.message);
      toast.error(parsed.message, 'Failed to Submit Report');
    }
  };

  // Duplicate warning detection
  const isPotentialDuplicate =
    enteredTitle &&
    ['pothole', '5th ave', 'water leak', 'street light', 'streetlight'].some((k) =>
      enteredTitle.toLowerCase().includes(k)
    );

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      <Breadcrumbs
        items={[
          { label: 'Citizen Portal', href: '/citizen/dashboard' },
          { label: 'Create New Report' },
        ]}
      />

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Report a Neighborhood Issue
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Provide the details, precise location, and photos so the appropriate department can take action.
          </p>
        </div>
      </div>

      {serverError && (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-800"
        >
          <AlertTriangle className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
          <span>{serverError}</span>
        </div>
      )}

      {isPotentialDuplicate && (
        <div className="flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs text-amber-900">
          <Info className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Possible Existing Report</p>
            <p className="text-amber-800 mt-0.5">
              Similar issues have been recently filed in this area. You can still submit this report,
              or check the{' '}
              <a href="/citizen/map" className="underline font-medium text-amber-950">
                Community Issue Map
              </a>{' '}
              to upvote an existing report.
            </p>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Section 1: Problem Details */}
        <Card className="border-slate-200/90 shadow-sm">
          <CardHeader>
            <CardTitle className="text-base">1. Problem Classification & Description</CardTitle>
            <CardDescription>
              Select the category that best describes the issue and describe what you observe.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            {/* Category Cards Picker */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Problem Category <span className="text-rose-500">*</span>
              </label>
              <Controller
                control={control}
                name="category"
                render={({ field }) => (
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2.5">
                    {(Object.keys(CATEGORY_DETAILS) as ReportCategory[]).map((catKey) => {
                      const details = CATEGORY_DETAILS[catKey];
                      const isSelected = field.value === catKey;
                      return (
                        <button
                          key={catKey}
                          type="button"
                          onClick={() => field.onChange(catKey)}
                          className={`flex flex-col items-start p-3 rounded-xl border text-left transition-all ${
                            isSelected
                              ? 'border-teal-600 bg-teal-50/80 ring-2 ring-teal-500/20 shadow-xs'
                              : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                          }`}
                        >
                          <div className="flex items-center justify-between w-full mb-1.5">
                            <span
                              className={`text-xs font-semibold ${
                                isSelected ? 'text-teal-900' : 'text-slate-800'
                              }`}
                            >
                              {details.label}
                            </span>
                            {isSelected && <CheckCircle2 className="h-4 w-4 text-teal-600 shrink-0" />}
                          </div>
                          <p className="text-[11px] text-slate-500 line-clamp-2 leading-relaxed">
                            {details.description}
                          </p>
                        </button>
                      );
                    })}
                  </div>
                )}
              />
              {errors.category && (
                <p className="text-xs text-rose-600 font-medium mt-1.5">
                  {errors.category.message}
                </p>
              )}
            </div>

            <Input
              label="Issue Summary Title"
              placeholder="e.g. Hazardous deep pothole causing vehicle damage"
              error={errors.title?.message}
              required
              {...register('title')}
            />

            <Textarea
              label="Detailed Description"
              rows={4}
              placeholder="Provide exact details such as size, severity, when it started, safety risks, and landmarks nearby..."
              error={errors.description?.message}
              required
              {...register('description')}
            />
          </CardContent>
        </Card>

        {/* Section 2: Location Map Picker */}
        <Card className="border-slate-200/90 shadow-sm">
          <CardHeader>
            <CardTitle className="text-base">2. Incident Location & Map Pin</CardTitle>
            <CardDescription>
              Drop a pin on the exact location of the issue or click "Use My GPS Location".
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Controller
              control={control}
              name="latitude"
              render={({ field: latField }) => (
                <Controller
                  control={control}
                  name="longitude"
                  render={({ field: lngField }) => (
                    <LocationPicker
                      latitude={latField.value}
                      longitude={lngField.value}
                      onChange={(lat, lng) => {
                        latField.onChange(lat);
                        lngField.onChange(lng);
                      }}
                      error={errors.latitude?.message || errors.longitude?.message}
                    />
                  )}
                />
              )}
            />

            <Input
              label="Street Address or Landmark Description (Optional)"
              placeholder="e.g. Corner of 5th Ave and 34th St, near the subway entrance"
              helperText="Helps repair crews navigate directly to the spot."
              error={errors.address?.message}
              {...register('address')}
            />
          </CardContent>
        </Card>

        {/* Section 3: Photo Attachments */}
        <Card className="border-slate-200/90 shadow-sm">
          <CardHeader>
            <CardTitle className="text-base">3. Photo Evidence</CardTitle>
            <CardDescription>
              Upload up to 5 photos showing the severity and context of the problem (max 5MB each).
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {uploadError && (
              <p className="text-xs text-rose-600 font-medium">{uploadError}</p>
            )}

            {/* Dropzone */}
            <label className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 p-6 text-center cursor-pointer hover:border-teal-500 hover:bg-slate-50/50 transition-colors">
              <UploadCloud className="h-8 w-8 text-teal-600 mb-2" />
              <p className="text-xs font-semibold text-slate-800">
                Click or drag photos here to upload
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5">JPG, PNG, or WebP up to 5MB</p>
              <input
                type="file"
                multiple
                accept="image/jpeg,image/png,image/webp"
                onChange={handlePhotoSelect}
                className="hidden"
                disabled={photos.length >= 5}
              />
            </label>

            {/* Selected photo previews */}
            {photoPreviews.length > 0 && (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3 pt-2">
                {photoPreviews.map((url, index) => (
                  <div
                    key={index}
                    className="relative aspect-square rounded-xl overflow-hidden border border-slate-200 bg-slate-100 group shadow-xs"
                  >
                    <img src={url} alt="Preview" className="h-full w-full object-cover" />
                    <button
                      type="button"
                      onClick={() => handleRemovePhoto(index)}
                      className="absolute top-1 right-1 h-6 w-6 rounded-full bg-slate-900/80 text-white flex items-center justify-center hover:bg-rose-600 transition-colors"
                      aria-label="Remove photo"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                    <div className="absolute bottom-0 inset-x-0 bg-slate-900/70 p-1 text-[9px] text-white truncate text-center">
                      {photos[index]?.name}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Submit Actions */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate('/citizen/dashboard')}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            size="lg"
            isLoading={isSubmitting}
            leftIcon={<Send className="h-4 w-4" />}
          >
            Submit Incident Report
          </Button>
        </div>
      </form>
    </div>
  );
};
