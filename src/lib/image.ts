/**
 * Client-side photo preparation.
 *
 * Phone cameras produce 3-12 MB images. Uploading those over mobile data is
 * slow, can exceed the 5 MB server limit, and the extra resolution adds
 * nothing for issue detection. Before upload we downscale to a sensible size
 * and re-encode as JPEG. This also converts formats some phones produce
 * (e.g. HEIC on iOS, when the browser can decode it) into a JPEG the backend
 * accepts.
 *
 * If the browser cannot decode the image, the original file is returned
 * unchanged and the normal type/size validation applies.
 */

const MAX_DIMENSION = 1600;
const JPEG_QUALITY = 0.85;
/** Files already this small and within MAX_DIMENSION are left alone. */
const SKIP_BELOW_BYTES = 900 * 1024;

const prepared = new WeakSet<File>();

type Decoded = { source: CanvasImageSource; width: number; height: number; close: () => void };

async function decode(file: File): Promise<Decoded | null> {
  // createImageBitmap honours EXIF orientation, so portrait phone photos are
  // not rotated sideways.
  if (typeof createImageBitmap === 'function') {
    try {
      const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
      return {
        source: bitmap,
        width: bitmap.width,
        height: bitmap.height,
        close: () => bitmap.close(),
      };
    } catch {
      // Fall through to <img> decoding (older Safari, some formats).
    }
  }

  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise<HTMLImageElement>((resolve, reject) => {
      const el = new Image();
      el.onload = () => resolve(el);
      el.onerror = () => reject(new Error('decode failed'));
      el.src = url;
    });
    return {
      source: img,
      width: img.naturalWidth,
      height: img.naturalHeight,
      close: () => URL.revokeObjectURL(url),
    };
  } catch {
    URL.revokeObjectURL(url);
    return null;
  }
}

function toJpegName(name: string): string {
  const base = name.replace(/\.[^.]+$/, '') || 'photo';
  return `${base}.jpg`;
}

export async function prepareImageForUpload(file: File): Promise<File> {
  if (prepared.has(file)) return file;
  if (!file.type.startsWith('image/') && !/\.(heic|heif)$/i.test(file.name)) return file;

  const decoded = await decode(file);
  if (!decoded) return file;

  try {
    const { width, height } = decoded;
    if (!width || !height) return file;

    const alreadyFine =
      file.size <= SKIP_BELOW_BYTES &&
      Math.max(width, height) <= MAX_DIMENSION &&
      (file.type === 'image/jpeg' || file.type === 'image/png' || file.type === 'image/webp');
    if (alreadyFine) {
      prepared.add(file);
      return file;
    }

    const scale = Math.min(1, MAX_DIMENSION / Math.max(width, height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(width * scale);
    canvas.height = Math.round(height * scale);
    const ctx = canvas.getContext('2d');
    if (!ctx) return file;
    // JPEG has no alpha: paint white under transparent PNGs.
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(decoded.source, 0, 0, canvas.width, canvas.height);

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, 'image/jpeg', JPEG_QUALITY)
    );
    if (!blob) return file;
    // Keep the original if re-encoding somehow made it bigger and it was
    // already an accepted type.
    if (blob.size >= file.size && file.type === 'image/jpeg') {
      prepared.add(file);
      return file;
    }

    const out = new File([blob], toJpegName(file.name), {
      type: 'image/jpeg',
      lastModified: Date.now(),
    });
    prepared.add(out);
    return out;
  } finally {
    decoded.close();
  }
}
