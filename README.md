# Neighborhood Issue Reporter — Civic Technology Frontend

A modern, production-minded civic technology web application built with **React**, **Vite**, **TypeScript (Strict Mode)**, and **Tailwind CSS**. 

The platform enables **Citizens** to report and track neighborhood infrastructure hazards, empowers **Municipal Administrators** to triage, dispatch, and analyze issues with SLA tracking, and equips **Field Workers** with mobile-optimized work orders, directions, and on-site resolution workflows.

---

## 🌟 Key Features

### 👤 Citizen Portal
- **Dashboard:** Welcome overview with report statistics derived from live records, quick action buttons, and recent community updates.
- **Multi-Section Report Creation:**
  - Standardized problem categorization (Road Damage, Streetlights, Garbage/Waste, Water Leaks, Drainage, Public Property, etc.).
  - Interactive Leaflet map location picker (click-to-drop pin, draggable marker, browser GPS "Use My Current Location").
  - Photo evidence upload with client-side file validation (JPG/PNG/WebP, max 5MB, up to 5 photos) and image preview gallery.
  - Proactive duplicate detection warnings.
- **Report Tracking & Governance:** Real-time lifecycle timeline, upvoting mechanism, citizen withdrawal controls, and full photo lightbox preview.
- **Community Issue Map:** Interactive full-page map with status/priority filtering and location popups.

### 🏛️ Administrator Operations
- **Operations & Governance Dashboard:** Real-time KPI summary (Total, Open, In Progress, Resolved, Overdue SLA) with **Recharts** visualizations (Donut status breakdown, Category bar chart, Velocity trends).
- **Report Management Console:** Multi-parameter search, status, category, priority, and department filters with pagination and column sorting.
- **Triage & Worker Dispatch:** Assign field workers filtered by active department, adjust priority levels, set SLA deadlines, and transition states through permitted lifecycle rules.
- **Department & SLA Management:** Create, edit, and safely deactivate departments with custom response SLA targets (hours).
- **User Directory & RBAC:** View citizen and staff accounts, provision new field worker accounts, update department assignments, and safely manage administrative accounts.
- **SLA & Analytics Intelligence:** Detailed department compliance percentage tracking, average resolution hours, and workload monitoring.

### 👷 Field Worker Interface
- **Mobile-Optimized Interface:** High-contrast, large touch-target work order management designed for smartphones and tablets in the field.
- **Turn-by-Turn Navigation:** One-tap integration to launch Google Maps driving navigation directly to exact incident GPS coordinates.
- **Workflow State Actions:** "Start Work Order" (`in_progress`) and "Complete Work Order" (`resolved`) with required resolution notes and optional evidence photo URLs.
- **Field Navigation Map:** Spatial display of active dispatches on OpenStreetMap tiles.

---

## 🛠️ Mandatory Technology Stack

- **Core Framework:** React 18 & TypeScript (with `strict: true`)
- **Build Tool:** Vite 6
- **Styling:** Tailwind CSS (Custom civic palette: Slate-50 background, Teal/Navy accents, accessible focus indicators)
- **Routing:** React Router 6 (with role-based route guards and smart dashboard redirection)
- **Data Fetching & Cache:** TanStack Query v5 (React Query)
- **Forms & Validation:** React Hook Form & Zod schemas
- **Interactive Maps:** Leaflet & React Leaflet
- **Data Visualizations:** Recharts
- **Icons:** Lucide React
- **Notifications:** Accessible custom floating toast system & unread badge dropdown
- **Testing:** Vitest & React Testing Library (`@testing-library/react`, `jsdom`, `@testing-library/jest-dom`)

---

## 🚀 Quick Start Guide

### Prerequisites
- **Node.js:** v18.0.0 or newer (Tested on Node.js v25)
- **Package Manager:** `npm` (v9 or newer)

### 1. Installation
Clone the repository and install all dependencies:
```bash
npm install
```

### 2. Environment Configuration
Copy the example environment configuration:
```bash
cp .env.example .env
```

Default configuration variables in `.env`:
```env
# FastAPI Backend API endpoint
VITE_API_BASE_URL=http://localhost:8000/api/v1

# Application Branding
VITE_APP_NAME=Neighborhood Issue Reporter

# Default Map Center (Leaflet / OpenStreetMap)
VITE_MAP_DEFAULT_LAT=40.7128
VITE_MAP_DEFAULT_LNG=-74.0060
VITE_MAP_DEFAULT_ZOOM=13

# Fallback adapter when backend is unreachable or in preview/mock mode
VITE_ENABLE_MOCK_FALLBACK=true
```

### 3. Start Development Server
```bash
npm run dev
```
Open your browser at `http://localhost:5173`.

---

## 🔑 Demo Personas & Quick Login

When evaluating the application without entering credentials, use the 1-Click **"Demo Quick-Fill Personas"** buttons on the `/login` screen:

| Persona | Role | Email | Password | Landing Page |
| :--- | :--- | :--- | :--- | :--- |
| **Sarah Jenkins** | Citizen | `citizen@example.com` | `password123` | `/citizen/dashboard` |
| **Marcus Vance** | Administrator | `admin@example.com` | `password123` | `/admin/dashboard` |
| **Dave Miller** | Field Worker | `worker@example.com` | `password123` | `/worker/dashboard` |

---

## 🧪 Testing and Quality Assurance

Run the test suite via Vitest:
```bash
npm test
```

Run test suite in interactive watch mode:
```bash
npm run test:watch
```

Run strict TypeScript type checks:
```bash
npm run typecheck
```

Build production bundle:
```bash
npm run build
```

Preview production build locally:
```bash
npm run preview
```

---

## 🗺️ Project Structure

```text
├── src/
│   ├── app/
│   │   ├── App.tsx             # Root application component
│   │   ├── router.tsx          # Route definitions & RBAC guards
│   │   └── providers.tsx       # QueryClient, Auth, & Toast providers
│   ├── components/
│   │   ├── data-display/       # Status badges, priority badges, timelines, pagination
│   │   ├── layout/             # Header, sidebar, mobile navigation, app & public layouts
│   │   ├── maps/               # Interactive Leaflet location picker & issue map
│   │   ├── reports/            # ReportCard, ReportFilters, view toggles
│   │   └── ui/                 # Accessible button, input, select, textarea, modal, toast
│   ├── features/
│   │   ├── admin/              # Dashboard, reports triage, departments, users, analytics
│   │   ├── auth/               # Login, register, forgot-password, unauthorized
│   │   ├── citizen/            # Citizen dashboard, report creation, my reports, issue map
│   │   ├── notifications/      # Notifications inbox with unread filters
│   │   └── worker/             # Field dashboard, assignments, navigation, resolution notes
│   ├── hooks/
│   │   ├── use-auth.tsx        # Authentication context & session hook
│   │   ├── use-debounce.ts     # Search debouncing hook
│   │   └── use-toast.tsx       # Toast notifications hook & context
│   ├── lib/
│   │   ├── api-client.ts       # Axios client with auth interceptors & storage
│   │   ├── api-errors.ts       # FastAPI 422/400/401/403/500 error parser
│   │   ├── constants.ts        # Problem categories, status styling, map defaults
│   │   ├── formatters.ts       # Date, coordinate, category, and status formatters
│   │   ├── mock-adapter.ts     # Resilient typed mock adapter with localStorage persistence
│   │   ├── mock-data.ts        # Realistic initial civic dataset
│   │   └── permissions.ts      # Role-based action permissions matrix
│   ├── schemas/                # Zod validation schemas for auth, reports, departments, users
│   ├── services/               # Typed services (auth, reports, departments, users, notifications)
│   ├── test/                   # Vitest tests (auth, reports, utils, components)
│   └── types/                  # TypeScript interface declarations
├── API_INTEGRATION_NOTES.md    # Detailed API contract documentation
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```

---

## 🔧 Backend Integration & Troubleshooting

### CORS Configuration
Ensure your FastAPI backend has `CORSMiddleware` configured to permit requests from the Vite frontend origin (`http://localhost:5173` or `http://127.0.0.1:5173`):
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Offline / Fallback Mode
If the FastAPI backend is not currently running, the frontend automatically falls back to `MockBackendAdapter` when `VITE_ENABLE_MOCK_FALLBACK=true`. All state updates (e.g. creating reports, assigning workers, marking resolutions) persist to browser `localStorage` and survive page refreshes.

---

## 📄 License
MIT License &copy; 2026 Neighborhood Issue Reporter Civic Technology Initiative.
