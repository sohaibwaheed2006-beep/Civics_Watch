import { ReportCategory } from '@/types/report';

export const CATEGORY_IMAGES: Record<ReportCategory, { url: string; fallback: string; alt: string }> = {
  road_damage: {
    url: 'https://images.unsplash.com/photo-1515162816999-a0c47dc192f7?auto=format&fit=crop&w=800&q=80',
    fallback: '/images/categories/road_damage.jpg',
    alt: 'Road surface damage and asphalt maintenance',
  },
  streetlight: {
    url: 'https://images.unsplash.com/photo-1509114397022-ed747cca3f65?auto=format&fit=crop&w=800&q=80',
    fallback: '/images/categories/streetlight.jpg',
    alt: 'Streetlight and municipal electrical infrastructure',
  },
  garbage_waste: {
    url: 'https://images.unsplash.com/photo-1532996122724-e3c354a0b15b?auto=format&fit=crop&w=800&q=80',
    fallback: '/images/categories/garbage_waste.jpg',
    alt: 'Sanitation, municipal waste, and litter containment',
  },
  water_leak: {
    // Self-hosted: the previous Unsplash IDs resolved to unrelated stock
    // (a workshop / a living room). Serving the image locally keeps it correct.
    url: '/images/categories/water_leak.jpg',
    fallback: '/images/categories/water_leak.jpg',
    alt: 'Water gushing from a leaking metal water pipe',
  },
  drainage: {
    url: '/images/categories/drainage.jpg',
    fallback: '/images/categories/drainage.jpg',
    alt: 'A curbside storm drain blocked with standing water and debris',
  },
  public_property: {
    url: 'https://images.unsplash.com/photo-1519331379826-f10be5486c6f?auto=format&fit=crop&w=800&q=80',
    fallback: '/images/categories/public_property.jpg',
    alt: 'Public property, parks, railings, and civic assets',
  },
  other: {
    url: 'https://images.unsplash.com/photo-1480714378408-67cf0d13bc1b?auto=format&fit=crop&w=800&q=80',
    fallback: '/images/categories/other.jpg',
    alt: 'Neighborhood civic infrastructure',
  },
};

// Department banners, keyed to the three canonical seeded departments
// (see mock-data.ts). All self-hosted — the previous Unsplash IDs had drifted
// to unrelated or dead images (clouds / a blank grey / an engineering workshop).
export const DEPARTMENT_IMAGES: Record<string, string> = {
  'dept-1': '/images/departments/electrical.jpg', // Electrical
  'dept-2': '/images/categories/water_leak.jpg', // Plumbing / Water
  'dept-3': '/images/departments/general_works.jpg', // General Works (default)
};

export const USER_AVATARS: Record<string, string> = {};

export function getCategoryCoverImage(category?: string | null): string {
  if (category && category in CATEGORY_IMAGES) {
    return CATEGORY_IMAGES[category as ReportCategory].url;
  }
  return CATEGORY_IMAGES.other.url;
}

export function getDepartmentCoverImage(departmentId?: string | null, name?: string | null): string {
  if (departmentId && DEPARTMENT_IMAGES[departmentId]) {
    return DEPARTMENT_IMAGES[departmentId];
  }
  if (name) {
    const lower = name.toLowerCase();
    if (lower.includes('elect') || lower.includes('light')) return DEPARTMENT_IMAGES['dept-1'];
    if (
      lower.includes('plumb') ||
      lower.includes('water') ||
      lower.includes('sewer') ||
      lower.includes('drain')
    ) {
      return DEPARTMENT_IMAGES['dept-2'];
    }
  }
  // General Works / Roads / Waste / Parks and anything else fall back to the
  // general-works banner.
  return DEPARTMENT_IMAGES['dept-3'];
}

export function getCategorySvgDataUri(category?: string | null): string {
  const cat = category || 'other';
  const label =
    cat === 'road_damage'
      ? 'Roads & Potholes'
      : cat === 'streetlight'
      ? 'Lighting & Power'
      : cat === 'garbage_waste'
      ? 'Waste & Sanitation'
      : cat === 'water_leak'
      ? 'Water Main Leaks'
      : cat === 'drainage'
      ? 'Blocked Drainage'
      : cat === 'public_property'
      ? 'Parks & Property'
      : 'Civic Infrastructure';

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
    <defs>
      <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#0f766e" />
        <stop offset="100%" stop-color="#0f172a" />
      </linearGradient>
    </defs>
    <rect width="100%" height="100%" fill="url(#g)" />
    <circle cx="200" cy="120" r="48" fill="#14b8a6" fill-opacity="0.25" />
    <path d="M180 120 L200 95 L220 120 L210 120 L210 145 L190 145 L190 120 Z" fill="#5eead4" />
    <text x="200" y="210" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="16" font-weight="700" fill="#ffffff" text-anchor="middle">${label}</text>
    <text x="200" y="235" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="11" fill="#99f6e4" text-anchor="middle">Community Service</text>
  </svg>`;

  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

export function handleImageFallback(e: React.SyntheticEvent<HTMLImageElement>, category?: string | null) {
  const target = e.currentTarget;
  const svgUri = getCategorySvgDataUri(category);
  if (target.src !== svgUri) {
    target.src = svgUri;
  }
}

export function getUserAvatar(_userId?: string | null, _role?: string | null): undefined {
  return undefined;
}
