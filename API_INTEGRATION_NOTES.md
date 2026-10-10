# API Integration Notes — Neighborhood Issue Reporter Frontend

This document specifies the integration contract between the React frontend and the FastAPI + MySQL backend services.

---

## 1. API Base URL and Environment Configuration

- **Default API Base URL:** `http://localhost:8000/api/v1`
- **Configured via:** `VITE_API_BASE_URL` in `.env` (or `.env.example`)
- **Fallback Simulation Adapter:** Controlled via `VITE_ENABLE_MOCK_FALLBACK=true`. When the backend server is unreachable or offline during local frontend evaluation, the typed adapter seamlessly handles mutations and queries with persistent state in `localStorage` without faking permanent production data.

---

## 2. Authentication & Session Strategy

- **Strategy:** Bearer JWT token authentication.
- **Request Header:**
  ```http
  Authorization: Bearer <access_token>
  ```
- **Login Endpoint:** `POST /api/v1/auth/login`
  - **Payload:** `{ "email": string, "password": string }`
  - **Response (200 OK):**
    ```json
    {
      "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "tokenType": "bearer",
      "user": {
        "id": "user-uuid",
        "email": "citizen@example.com",
        "fullName": "Sarah Jenkins",
        "role": "citizen",
        "phone": "+1 (555) 234-5678",
        "isActive": true,
        "createdAt": "2026-02-01T10:00:00Z"
      }
    }
    ```
- **Register Endpoint:** `POST /api/v1/auth/register`
  - **Payload:** `{ "fullName": string, "email": string, "password": string, "phone"?: string }`
  - **Enforcement:** Citizen registration form restricts role assignment to `"citizen"` strictly to prevent privilege escalation.
- **Session Verification:** `GET /api/v1/auth/me`
- **Session Logout:** `POST /api/v1/auth/logout`
  - Clears browser auth token and TanStack Query cache.
- **Token Expiry / 401 Handling:** Automatically removes stored credentials and redirects to `/login` without redirect loops.

---

## 3. Roles and Permissions Matrix

The platform recognizes three distinct roles:

| Role | Role Value | Permitted Portals & Responsibilities |
| :--- | :--- | :--- |
| **Citizen** | `citizen` | Submit reports, upload photos, pick GPS map coordinates, track report lifecycle, upvote issues, manage personal profile. |
| **Administrator** | `admin` | Triage & review reports, change report status across permitted transitions, assign departments and field workers, manage user directory, monitor SLA analytics. |
| **Field Worker** | `worker` | Review assigned work orders, launch turn-by-turn navigation, start repairs (`in_progress`), mark work completed (`resolved`) with resolution notes and completion evidence. |

---

## 4. Report Lifecycle & Permitted Status Transitions

### Status Enum Values
- `submitted`: Newly created report queued for review.
- `under_review`: Assessed by municipal staff.
- `assigned`: Dispatched to department and field worker.
- `in_progress`: Field worker actively on-site remediating problem.
- `resolved`: Remediated and verified with notes.
- `rejected`: Flagged as duplicate, outside municipal jurisdiction, or invalid.
- `reopened`: Reopened due to recurrence or incomplete fix.

### Transition Rules
- **Citizen:** Can withdraw their own report only while in `submitted` or `under_review` state.
- **Worker:** Can transition `assigned` &rarr; `in_progress`, and `in_progress` &rarr; `resolved` (accompanied by resolution note).
- **Admin:** Governs all transitions:
  - `submitted` &rarr; `under_review` | `assigned` | `rejected`
  - `under_review` &rarr; `assigned` | `in_progress` | `rejected`
  - `assigned` &rarr; `in_progress` | `under_review` | `rejected`
  - `in_progress` &rarr; `resolved` | `assigned` | `rejected`
  - `resolved` &rarr; `reopened`
  - `rejected` &rarr; `under_review` | `reopened`

---

## 5. Report Categories & Problem Types

Canonical categories expected by backend:
1. `road_damage`: Potholes, road cracks, asphalt cave-ins.
2. `streetlight`: Dark or broken street lighting.
3. `garbage_waste`: Overflowing bins, illegal dumping.
4. `water_leak`: Water mains and curb bubbling.
5. `drainage`: Blocked storm drains and gutters.
6. `public_property`: Damaged park benches, broken railings, playground issues.
7. `other`: Miscellaneous neighborhood hazards.

---

## 6. Endpoints Contract

### Reports
- `GET /api/v1/reports`:
  - **Query Params:** `search`, `status`, `category`, `priority`, `departmentId`, `citizenId`, `assignedWorkerId`, `page`, `limit`, `sortOrder`
  - **Response:**
    ```json
    {
      "data": [ ...Report ],
      "total": 42,
      "page": 1,
      "limit": 10,
      "totalPages": 5
    }
    ```
- `GET /api/v1/reports/:id`: Returns single `Report` object.
- `POST /api/v1/reports`:
  - **Format:** `multipart/form-data`
  - **Fields:** `title`, `description`, `category`, `latitude`, `longitude`, `address` (optional), `photos` (repeated file fields, up to 5 files, max 5MB each).
- `PATCH /api/v1/reports/:id/status`:
  - **Payload:** `{ "status": ReportStatus, "note"?: string, "resolutionEvidenceUrl"?: string }`
- `POST /api/v1/reports/:id/assign`:
  - **Payload:** `{ "workerId": string, "departmentId": string, "priority"?: string, "deadline"?: string }`
- `POST /api/v1/reports/:id/upvote`: Toggles citizen upvote on report.
- `DELETE /api/v1/reports/:id`: Withdraws report.

### Departments
- `GET /api/v1/departments`: Lists all departments with SLA hours and worker counts.
- `POST /api/v1/departments`: `{ "name": string, "description": string, "defaultSlaHours": number }`
- `PATCH /api/v1/departments/:id`: Update department details or `isActive` status.

### Users & Workers
- `GET /api/v1/users`: Paginated user list with role and department filters.
- `POST /api/v1/users/workers`: Provisions field worker account `{ "fullName": string, "email": string, "password": string, "departmentId": string, "phone"?: string }`.
- `PATCH /api/v1/users/:id`: Updates user role, department, or active status.

### Worker Assignments
- `GET /api/v1/workers/:id/assignments`: Returns assignments specific to technician.

### Notifications
- `GET /api/v1/notifications?userId=:id`: Retrieves notifications for user.
- `PATCH /api/v1/notifications/:id/read`: Marks individual notification read.
- `POST /api/v1/notifications/read-all`: Marks all notifications read for user.

### Analytics
- `GET /api/v1/analytics/overview`: Returns KPI metrics, status breakdowns, category distributions, and department SLA compliance percentages.

---

## 7. Known Missing Backend Capabilities & Architecture Notes

1. **Email Password Recovery:**
   - Standard local FastAPI containers typically do not bundle an external SMTP gateway out-of-the-box.
   - The frontend `/forgot-password` route explains this operational state transparently rather than simulating fake success emails.
2. **Reverse Geocoding:**
   - Map coordinate selection uses Leaflet and OpenStreetMap tiles directly without exposing commercial third-party API keys (e.g. Google Maps API keys).
   - Coordinates (`latitude` and `longitude`) are authoritative; optional human-readable street addresses can be provided by the reporting citizen.
3. **Real-time Push / WebSockets:**
   - Since WebSockets are not standardized in the preliminary contract, the frontend notification bell utilizes TanStack Query polling (30s background intervals) and automatic mutation invalidation for real-time responsiveness.
