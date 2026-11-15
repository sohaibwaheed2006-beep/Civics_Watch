import React, { useEffect, useRef, useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate } from 'react-router-dom';
import { createReportSchema, CreateReportFormData } from '@/schemas/report-schema';
import { useAuth } from '@/hooks/use-auth';
import { useToast } from '@/hooks/use-toast';
import { reportService } from '@/services/report-service';
import { geocodingService } from '@/services/geocoding-service';
import { aiService } from '@/services/ai-service';
import { parseApiError } from '@/lib/api-errors';
import { prepareImageForUpload } from '@/lib/image';
import { CATEGORY_DETAILS } from '@/lib/constants';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { LocationPicker } from '@/components/maps/location-picker';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import {
  UploadCloud,
  AlertTriangle,
  Send,
  CheckCircle2,
  Loader2,
  Sparkles,
  Camera,
  ShieldAlert,
  ArrowLeft,
  MapPin,
  X,
  RefreshCw,
} from 'lucide-react';
import { ReportCategory } from '@/types/report';

type WizardStep = 'upload' | 'confirm';

const MAX_SIZE = 5 * 1024 * 1024; // 5 MB
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

export const CreateReportPage: React.FC = () => {
  const { user } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();

  const [step, setStep] = useState<WizardStep>('upload');
  const [photo, setPhoto] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);

  const [analyzing, setAnalyzing] = useState(false);
  const [analysisNote, setAnalysisNote] = useState<string | null>(null);
  // Why the last photo did not get the citizen to Step 2:
  //   retake      - the photo itself was rejected (unreadable / no issue seen)
  //   unavailable - the AI service failed; the same photo can be retried
  const [photoProblem, setPhotoProblem] = useState<{
    kind: 'retake' | 'unavailable';
    reason: string;
  } | null>(null);
  // Consecutive "service unavailable" results; the manual-entry escape hatch
  // only appears once a retry has also failed.
  const [unavailableCount, setUnavailableCount] = useState(0);
  const lastCoordsRef = useRef<{ lat: number; lng: number; accuracy: number } | null>(null);
  const [aiConfidence, setAiConfidence] = useState<number | null>(null);
  const [locating, setLocating] = useState(false);

  // Live in-browser camera capture (getUserMedia). Works on desktop (webcam)
  // and mobile (rear camera), showing a live feed with a shutter button.
  const [cameraOpen, setCameraOpen] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [cameraStarting, setCameraStarting] = useState(false);
  const [facingMode, setFacingMode] = useState<'environment' | 'user'>('environment');
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Values resolved on Step 1 (upload) but applied on Step 2 after the inputs
  // mount. react-hook-form's `register` fields don't exist while we're still
  // on the upload step, so calling setValue there never reaches the DOM.
  const [pendingFill, setPendingFill] = useState<Partial<CreateReportFormData> | null>(null);

  const {
    register,
    handleSubmit,
    control,
    watch,
    setValue,
    reset,
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

  const latitudeValue = watch('latitude');
  const longitudeValue = watch('longitude');

  // Clean up object URLs.
  useEffect(() => {
    return () => {
      if (photoPreview) URL.revokeObjectURL(photoPreview);
    };
  }, [photoPreview]);

  // --- Live camera capture -----------------------------------------------
  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) videoRef.current.srcObject = null;
  };

  const startCamera = async (mode: 'environment' | 'user' = facingMode) => {
    setCameraError(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError('Your browser does not support live camera capture. Use "Upload a photo" instead.');
      return;
    }
    setCameraStarting(true);
    setCameraOpen(true);
    stopCamera();
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: mode },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => undefined);
      }
    } catch {
      setCameraError('Could not access the camera. Please allow camera permission, or use "Upload a photo" instead.');
      setCameraOpen(false);
      stopCamera();
    } finally {
      setCameraStarting(false);
    }
  };

  const flipCamera = () => {
    const next = facingMode === 'environment' ? 'user' : 'environment';
    setFacingMode(next);
    void startCamera(next);
  };

  const closeCamera = () => {
    stopCamera();
    setCameraOpen(false);
    setCameraError(null);
  };

  const capturePhoto = () => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        const file = new File([blob], `camera-${Date.now()}.jpg`, { type: 'image/jpeg' });
        closeCamera();
        void processPhoto(file);
      },
      'image/jpeg',
      0.92
    );
  };

  // Make sure the camera is released if the user leaves the page mid-capture.
  useEffect(() => stopCamera, []);

  // --- Browser geolocation ------------------------------------------------
  // `maximumAge: 0` forces a fresh fix so we never reuse a cached position from
  // an earlier page/location. `accuracy` is the radius in metres the browser
  // reports; a large radius means an IP/Wi-Fi estimate rather than true GPS.
  const detectLocation = (): Promise<{ lat: number; lng: number; accuracy: number } | null> =>
    new Promise((resolve) => {
      if (!('geolocation' in navigator)) {
        resolve(null);
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) =>
          resolve({
            lat: pos.coords.latitude,
            lng: pos.coords.longitude,
            accuracy: pos.coords.accuracy,
          }),
        () => resolve(null),
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
      );
    });

  // --- The core photo-first pipeline --------------------------------------
  const processPhoto = async (original: File) => {
    setUploadError(null);
    setPhotoProblem(null);
    setServerError(null);

    // Shrink big phone photos (and convert HEIC where the browser can) so the
    // upload is fast on mobile data and stays under the size limit.
    const file = await prepareImageForUpload(original);

    if (!ALLOWED_TYPES.includes(file.type)) {
      setUploadError('Only JPG, PNG, and WebP images are supported.');
      return;
    }
    if (file.size > MAX_SIZE) {
      setUploadError(`"${file.name}" exceeds the 5MB limit.`);
      return;
    }

    // Re-analysing the same file (the "Try again" path) keeps its preview.
    const preview =
      file === photo && photoPreview ? photoPreview : URL.createObjectURL(file);
    setPhoto(file);
    setPhotoPreview(preview);
    setAnalyzing(true);
    setLocating(true);
    setAnalysisNote('Looking at your photo and detecting the issue…');

    // If the server was asleep the first analysis can take up to a minute;
    // say so instead of leaving the user staring at a spinner.
    const slowNote = window.setTimeout(
      () =>
        setAnalysisNote(
          'Still working. The server may be waking up, this can take up to a minute the first time…'
        ),
      8000
    );

    // Kick off AI analysis and GPS in parallel.
    const [analysis, coords] = await Promise.all([
      aiService.analyzePhoto(file),
      detectLocation(),
    ]);
    window.clearTimeout(slowNote);
    setLocating(false);
    lastCoordsRef.current = coords;

    // The wizard only advances when the AI actually detected an issue. Any
    // other outcome keeps the citizen on this step with a clear next action:
    // retake the photo, or retry the analysis if the service was down.
    if (analysis.status !== 'detected') {
      setAnalyzing(false);
      setAnalysisNote(null);
      if (analysis.status === 'unavailable') {
        setUnavailableCount((n) => n + 1);
      }
      setPhotoProblem({ kind: analysis.status, reason: analysis.reason });
      return;
    }

    const result = analysis.data;
    setUnavailableCount(0);
    setAiConfidence(result.confidence);
    setAnalysisNote(
      `Detected: ${CATEGORY_DETAILS[result.category]?.label || result.category} · ${result.priority} priority`
    );
    const fill: Partial<CreateReportFormData> = {
      category: result.category,
      title: result.title,
      description: result.description,
      ...(await buildLocationFill(coords, result.locationHint)),
    };

    setPendingFill(fill);
    setAnalyzing(false);
    setStep('confirm');
  };

  // Apply detected coordinates and reverse-geocode them to a street address.
  const buildLocationFill = async (
    coords: { lat: number; lng: number; accuracy: number } | null,
    locationHint: string | null
  ): Promise<Partial<CreateReportFormData>> => {
    const fill: Partial<CreateReportFormData> = {};
    if (coords) {
      fill.latitude = coords.lat;
      fill.longitude = coords.lng;
      const address = await geocodingService.reverseGeocode(coords.lat, coords.lng);
      if (address) {
        fill.address = address;
      }
    } else {
      // No device fix: leave the pin unset so the citizen must place it on the
      // map rather than silently submitting the default map center.
      if (locationHint) {
        fill.address = locationHint;
      }
    }
    return fill;
  };

  // Last resort when the AI service itself stays down after a retry: let the
  // citizen fill the form by hand. Never offered for a rejected photo.
  const continueManually = async () => {
    setPhotoProblem(null);
    setAiConfidence(null);
    setAnalysisNote(
      'Automatic detection was unavailable. Please describe the issue below.'
    );
    setPendingFill(await buildLocationFill(lastCoordsRef.current, null));
    setStep('confirm');
  };

  // Drop the rejected photo so the citizen can take or pick another one.
  const discardPhoto = () => {
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    setPhoto(null);
    setPhotoPreview(null);
    setPhotoProblem(null);
  };

  // Once Step 2 is on screen and its inputs are mounted, push the detected
  // values into the form so the uncontrolled Title/Description fields show them.
  useEffect(() => {
    if (step !== 'confirm' || !pendingFill) return;
    (Object.entries(pendingFill) as [keyof CreateReportFormData, unknown][]).forEach(
      ([key, value]) => {
        if (value !== undefined && value !== null) {
          setValue(key, value as never, { shouldValidate: true });
        }
      }
    );
    setPendingFill(null);
  }, [step, pendingFill, setValue]);

  const handlePhotoInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) void processPhoto(file);
    // Reset the input so re-selecting the same file re-triggers change.
    e.target.value = '';
  };

  const startOver = () => {
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    closeCamera();
    setPhoto(null);
    setPhotoPreview(null);
    setStep('upload');
    setPhotoProblem(null);
    setUnavailableCount(0);
    lastCoordsRef.current = null;
    setUploadError(null);
    setServerError(null);
    setCameraError(null);
    setAnalysisNote(null);
    setAiConfidence(null);
    setPendingFill(null);
    reset();
  };

  // Map pin manual adjustment on the confirm step. A manual placement is
  // authoritative, so we treat the location as set and drop the GPS-accuracy
  // warning.
  const handleLocationChange = async (lat: number, lng: number) => {
    setValue('latitude', lat, { shouldValidate: true });
    setValue('longitude', lng, { shouldValidate: true });
    const address = await geocodingService.reverseGeocode(lat, lng);
    if (address) setValue('address', address, { shouldValidate: true });
  };

  const onSubmit = async (data: CreateReportFormData) => {
    if (!user) {
      toast.error('You must be logged in to submit a report.');
      return;
    }
    setServerError(null);

    // Title and description are optional on the form. When left blank, derive
    // defaults so the report still carries a readable label (the photo is the
    // primary evidence). The backend requires non-empty values.
    const categoryLabel = CATEGORY_DETAILS[data.category]?.label || 'Issue';
    const title = (data.title || '').trim() || `${categoryLabel} reported from photo`;
    const description =
      (data.description || '').trim() ||
      'Submitted from a photo. Please see the attached image for details.';

    try {
      const created = await reportService.createReport(
        { ...data, title, description, photos: photo ? [photo] : [] },
        user
      );
      toast.success('Report submitted! Municipal crews have been notified.');
      navigate(`/citizen/reports/${created.id}`);
    } catch (err) {
      const parsed = parseApiError(err);
      setServerError(parsed.message);
      toast.error(parsed.message, 'Failed to Submit Report');
    }
  };

  return (
    <div className="space-y-6 max-w-3xl mx-auto pb-12">
      <Breadcrumbs
        items={[
          { label: 'Citizen Portal', href: '/citizen/dashboard' },
          { label: 'Report an Issue' },
        ]}
      />

      <div className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Report a Neighborhood Issue
        </h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Just snap a photo. Our AI detects the issue, writes the details, and
          pins the location — you only confirm.
        </p>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-3 text-xs font-semibold">
        <div className={`flex items-center gap-1.5 ${step === 'upload' ? 'text-teal-700' : 'text-slate-400'}`}>
          <span className={`h-6 w-6 rounded-full flex items-center justify-center ${step === 'upload' ? 'bg-teal-600 text-white' : 'bg-slate-200 text-slate-500'}`}>
            {step === 'confirm' ? <CheckCircle2 className="h-4 w-4" /> : '1'}
          </span>
          <span>Upload photo</span>
        </div>
        <div className="h-px w-8 bg-slate-200" />
        <div className={`flex items-center gap-1.5 ${step === 'confirm' ? 'text-teal-700' : 'text-slate-400'}`}>
          <span className={`h-6 w-6 rounded-full flex items-center justify-center ${step === 'confirm' ? 'bg-teal-600 text-white' : 'bg-slate-200 text-slate-500'}`}>
            2
          </span>
          <span>Review & confirm</span>
        </div>
      </div>

      {/* ---------------- STEP 1: UPLOAD ---------------- */}
      {step === 'upload' && (
        <Card className="border-slate-200/90 shadow-sm">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Camera className="h-4 w-4 text-teal-600" />
              <span>Take or upload a photo of the issue</span>
            </CardTitle>
            <CardDescription>
              A clear photo is all we need. The AI handles the category, title,
              description, and location automatically.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {uploadError && (
              <p className="text-xs text-rose-600 font-medium">{uploadError}</p>
            )}

            {photoProblem?.kind === 'retake' && !analyzing && !cameraOpen && (
              <div
                role="alert"
                className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-900"
              >
                {photoPreview ? (
                  <img
                    src={photoPreview}
                    alt="The photo that was not accepted"
                    className="h-16 w-16 shrink-0 rounded-lg object-cover border border-rose-200"
                  />
                ) : (
                  <ShieldAlert className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
                )}
                <div className="space-y-1">
                  <p className="font-bold">
                    We couldn't detect an issue in this photo — please retake it
                  </p>
                  <p>{photoProblem.reason}</p>
                  <p className="text-rose-800">
                    Take a clear, well-lit photo with the problem (road damage,
                    streetlight, water leak, garbage, etc.) filling the frame,
                    then try again below.
                  </p>
                </div>
              </div>
            )}

            {photoProblem?.kind === 'unavailable' && !analyzing && !cameraOpen && (
              <div
                role="alert"
                className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs text-amber-900"
              >
                <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
                <div className="space-y-2.5">
                  <div className="space-y-1">
                    <p className="font-bold">We couldn't analyze your photo just now</p>
                    <p>{photoProblem.reason}</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {photo && (
                      <Button
                        type="button"
                        size="sm"
                        onClick={() => void processPhoto(photo)}
                        leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
                      >
                        Try again
                      </Button>
                    )}
                    <Button type="button" size="sm" variant="outline" onClick={discardPhoto}>
                      Use a different photo
                    </Button>
                    {unavailableCount >= 2 && (
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        onClick={() => void continueManually()}
                      >
                        Fill in the details myself
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            )}

            {cameraError && (
              <p className="text-xs text-rose-600 font-medium">{cameraError}</p>
            )}

            {cameraOpen ? (
              /* Live camera view: in-browser feed + shutter. */
              <div className="space-y-3">
                <div className="relative mx-auto max-w-md overflow-hidden rounded-xl border border-slate-800 bg-black aspect-[4/3]">
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    className="h-full w-full object-cover"
                  />
                  {cameraStarting && (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/60 text-white text-sm gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Starting camera…</span>
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={closeCamera}
                    aria-label="Close camera"
                    className="absolute top-2 right-2 h-8 w-8 rounded-full bg-black/60 text-white flex items-center justify-center hover:bg-black/80"
                  >
                    <X className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={flipCamera}
                    aria-label="Switch camera"
                    className="absolute top-2 left-2 h-8 w-8 rounded-full bg-black/60 text-white flex items-center justify-center hover:bg-black/80"
                  >
                    <RefreshCw className="h-4 w-4" />
                  </button>
                </div>
                <div className="flex items-center justify-center gap-3">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={closeCamera}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="button"
                    onClick={capturePhoto}
                    disabled={cameraStarting}
                    leftIcon={<Camera className="h-4 w-4" />}
                  >
                    Capture photo
                  </Button>
                </div>
              </div>
            ) : !analyzing ? (
              <div className="space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {/* Take a live photo - opens the in-browser camera feed
                      (webcam on desktop, rear camera on mobile). */}
                  <button
                    type="button"
                    onClick={() => void startCamera()}
                    className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-teal-300 bg-teal-50/40 p-8 text-center cursor-pointer hover:border-teal-500 hover:bg-teal-50 transition-colors"
                  >
                    <Camera className="h-9 w-9 text-teal-600 mb-2.5" />
                    <p className="text-sm font-semibold text-slate-800">
                      {photoProblem?.kind === 'retake' ? 'Retake the photo' : 'Take a photo'}
                    </p>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      Capture live from your camera
                    </p>
                  </button>

                  {/* Upload an existing photo - no `capture`, so mobile opens
                      the gallery / file chooser instead of the camera. */}
                  <label className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 p-8 text-center cursor-pointer hover:border-teal-500 hover:bg-slate-50/50 transition-colors">
                    <UploadCloud className="h-9 w-9 text-teal-600 mb-2.5" />
                    <p className="text-sm font-semibold text-slate-800">
                      Upload a photo
                    </p>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      Choose from your device
                    </p>
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      onChange={handlePhotoInput}
                      className="hidden"
                    />
                  </label>
                </div>
                <p className="text-center text-[11px] text-slate-400">
                  JPG, PNG, or WebP up to 5MB
                </p>
              </div>
            ) : (
              <div className="rounded-xl border border-teal-200 bg-teal-50/60 p-6 space-y-4">
                {photoPreview && (
                  <div className="max-w-xs mx-auto aspect-video rounded-lg overflow-hidden border border-teal-200">
                    <img src={photoPreview} alt="Your upload" className="h-full w-full object-cover" />
                  </div>
                )}
                <div className="flex items-center justify-center gap-2 text-sm font-medium text-teal-900">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>{analysisNote || 'Analyzing…'}</span>
                </div>
                <div className="flex items-center justify-center gap-4 text-[11px] text-teal-700">
                  <span className="flex items-center gap-1">
                    <Sparkles className="h-3 w-3" /> Detecting issue
                  </span>
                  <span className="flex items-center gap-1">
                    <MapPin className="h-3 w-3" />
                    {locating ? 'Locating…' : 'Location found'}
                  </span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ---------------- STEP 2: CONFIRM ---------------- */}
      {step === 'confirm' && (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {serverError && (
            <div
              role="alert"
              className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-800"
            >
              <AlertTriangle className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{serverError}</span>
            </div>
          )}

          {aiConfidence !== null ? (
            <div className="flex items-start gap-2.5 rounded-xl border border-teal-200 bg-teal-50/70 p-3.5 text-xs text-teal-900">
              <Sparkles className="h-4 w-4 text-teal-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">
                  AI has pre-filled this report for you
                  <span className="font-normal text-teal-700">
                    {' '}
                    ({Math.round(aiConfidence * 100)}% confident)
                  </span>
                </p>
                <p className="text-teal-800 mt-0.5">
                  Review everything below and edit anything that looks off, then
                  confirm to submit.
                </p>
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50/70 p-3.5 text-xs text-amber-900">
              <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Automatic detection didn't run</p>
                <p className="text-amber-800 mt-0.5">
                  {analysisNote ||
                    'Please fill in the issue details and check the location below before submitting.'}
                </p>
              </div>
            </div>
          )}

          {/* Photo + category */}
          <Card className="border-slate-200/90 shadow-sm">
            <CardHeader>
              <CardTitle className="text-base">1. Issue & photo</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              {photoPreview && (
                <div className="max-w-sm aspect-video rounded-xl overflow-hidden border border-slate-200">
                  <img src={photoPreview} alt="Your upload" className="h-full w-full object-cover" />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Detected Category <span className="text-rose-500">*</span>
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
                              <span className={`text-xs font-semibold ${isSelected ? 'text-teal-900' : 'text-slate-800'}`}>
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
                  <p className="text-xs text-rose-600 font-medium mt-1.5">{errors.category.message}</p>
                )}
              </div>

              <Input
                label="Title (optional)"
                placeholder="AI fills this from your photo — edit if needed"
                error={errors.title?.message}
                {...register('title')}
              />

              <Textarea
                label="Description (optional)"
                rows={4}
                placeholder="AI fills this from your photo — edit if needed"
                error={errors.description?.message}
                {...register('description')}
              />
            </CardContent>
          </Card>

          {/* Location */}
          <Card className="border-slate-200/90 shadow-sm">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <MapPin className="h-4 w-4 text-teal-600" />
                <span>2. Detected location</span>
              </CardTitle>
              <CardDescription>
                Auto-detected from your device. Drag the pin if it's not quite
                right.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {(() => {
                const hasPin =
                  typeof latitudeValue === 'number' && typeof longitudeValue === 'number';
                if (!hasPin) {
                  return (
                    <div className="flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50/70 p-3.5 text-xs text-amber-900">
                      <MapPin className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
                      <p>
                        We couldn't detect your location automatically. Click the
                        map or drag the pin to the exact spot of the issue before
                        submitting.
                      </p>
                    </div>
                  );
                }
                // A detected location needs no banner: the pin on the map
                // already shows it.
                return null;
              })()}

              <LocationPicker
                latitude={latitudeValue}
                longitude={longitudeValue}
                onChange={handleLocationChange}
                error={errors.latitude?.message || errors.longitude?.message}
              />
              <Input
                label="Street Address or Landmark"
                error={errors.address?.message}
                {...register('address')}
              />
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex items-center justify-between gap-3 pt-4 border-t border-slate-200">
            <Button
              type="button"
              variant="outline"
              onClick={startOver}
              disabled={isSubmitting}
              leftIcon={<ArrowLeft className="h-4 w-4" />}
            >
              Start over
            </Button>
            <Button
              type="submit"
              size="lg"
              isLoading={isSubmitting}
              leftIcon={<Send className="h-4 w-4" />}
            >
              Confirm & Submit Report
            </Button>
          </div>
        </form>
      )}
    </div>
  );
};
