# Developer 2 - Report Domain Integration

This document covers how the report domain plugs into the shared Developer 1
foundation. It is written for a reviewer who has already read the Developer 1
code and only wants to know what Developer 2 added, where it was mounted, and
which contracts it relies on.

## 1. Shared interfaces consumed

| Import                                | Use                                   |
| ------------------------------------- | ------------------------------------- |
| `app.db.base.Base`                    | Model declarative base                 |
| `app.db.session.get_db`               | Request-scoped Session                 |
| `app.api.deps.CurrentUser`            | JWT-authenticated principal            |
| `app.api.deps.AdminUser`              | Admin role gate                        |
| `app.api.deps.PaginationDep`          | Shared pagination                      |
| `app.core.exceptions.*`               | Error envelope exceptions              |
| `app.schemas.common.Page/APIModel`    | Response envelopes / base schema       |
| `app.core.enums.UserRole`             | Role checks                            |
| `app.models.user.User`                | Owner / assignee / actor               |
| `app.models.department.Department`    | Routing / SLA                          |

Nothing in the shared surface was redefined. No second `Base`, engine, auth
system or role model exists.

## 2. New modules

```
app/
  core/enums.py                              # +ReportCategory/Priority/Status/NotificationType
  core/config.py                             # +report/AI settings
  models/
    report.py, report_photo.py, assignment.py, status_history.py,
    vote.py, notification.py
  schemas/
    report.py, assignment.py, status_history.py,
    notification.py, analytics.py, report_photo.py, vote.py
  services/
    report_service.py, report_workflow_service.py, assignment_service.py,
    notification_service.py, deadline_service.py, ai_service.py,
    duplicate_detection_service.py, image_storage_service.py,
    analytics_service.py
  api/v1/endpoints/
    reports.py, report_photos.py, assignments.py, votes.py,
    notifications.py, analytics.py
  migrations/versions/
    20261010_0002_0002_reports_domain.py    # revision 0002_reports
  tests/test_reports.py
```

The following shared files were touched (additively, not replaced):

- `app/db/registry.py` — report-domain model imports added.
- `app/models/__init__.py` — report-domain exports added.
- `app/api/v1/router.py` — report-domain routers mounted (Developer 1 left a
  marker block for exactly this).
- `app/tests/test_routing.py` — relaxed the "exactly 3 routers" assertion to
  "at least the 3 core routers", matching the integration guidance.

## 3. Routes

All under `/api/v1`. Developer 1's prefix is applied exactly once.

### Reports
- `POST /reports` - citizen create
- `GET  /reports` - filtered list (role-aware)
- `GET  /reports/my` - owner's reports
- `GET  /reports/map` - minimal payload for Leaflet markers
- `GET  /reports/{id}` - detail
- `GET  /reports/{id}/history` - status audit trail
- `GET  /reports/{id}/duplicates` - likely duplicates
- `PATCH /reports/{id}` - owner edit while submitted
- `POST /reports/{id}/moderate` - admin priority/department/note
- `DELETE /reports/{id}` - owner while submitted, or admin
- `POST /reports/{id}/status` - transition (staff/admin, or citizen reopen)

### Photos
- `POST   /reports/{id}/photos`
- `GET    /reports/{id}/photos`
- `DELETE /reports/{id}/photos/{photo_id}`
- `GET    /reports/photos/{photo_id}/content` (dev byte serving)

### Assignments
- `POST /reports/{id}/assign` (admin)
- `GET  /assignments/my` (workers)
- `GET  /departments/{id}/queue` (staff/admin)

### Votes
- `POST   /reports/{id}/vote`
- `DELETE /reports/{id}/vote`
- `GET    /reports/{id}/votes`

### Notifications
- `GET   /notifications`
- `GET   /notifications/unread-count`
- `PATCH /notifications/{id}/read`
- `POST  /notifications/mark-all-read`

### Analytics (admin only)
- `GET /analytics/overview`
- `GET /analytics/reports-by-status`
- `GET /analytics/reports-by-category`
- `GET /analytics/reports-over-time`
- `GET /analytics/department-performance`
- `GET /analytics/overdue-reports`

## 4. Status transition matrix

Enforced only in `app.services.report_workflow_service`. Routes never mutate
`report.status` directly.

```
submitted      -> under_review, rejected
under_review   -> assigned, rejected, in_progress
assigned       -> in_progress, under_review
in_progress    -> resolved, assigned
resolved       -> reopened
rejected       -> under_review               (admin only)
reopened       -> under_review, assigned, in_progress
```

Role scope:

- citizen owner: only `resolved -> reopened` on their own report
- worker: only on their active assignment; cannot reject
- admin: any transition in the matrix above

Every transition inserts a `status_history` row and (where applicable) a
notification in the same transaction.

## 5. SLA / deadlines

`deadline_service.compute_deadline` scales the department's
`default_sla_hours` by priority:

| Priority | Multiplier |
| -------- | ---------- |
| urgent   | 0.25x      |
| high     | 0.5x       |
| medium   | 1.0x       |
| low      | 2.0x       |

Deadlines are UTC. Overdue detection and analytics all go through this
service. There is no background scheduler shipped; the API functions
regardless, and `deadline_service.list_overdue_reports` is the integration
point if one is later added.

## 6. Photo storage

Local filesystem in development; the `Storage` protocol in
`image_storage_service` lets an S3-compatible implementation drop in later.
Content types are sniffed from the actual bytes (JPEG/PNG/WebP). File names
are server-generated under `reports/{report_id}/`; user-supplied paths are
rejected. Orphaned files are cleaned up when metadata persistence fails.

Dev serving goes through `GET /reports/photos/{id}/content`, which requires
authentication. In production, replace with a presigned URL or an
`X-Accel-Redirect` route.

## 7. AI integration (optional)

`ai_service` ships with a deterministic classifier and priority rule that
require no external service. When `AI_ENABLED=true`, provider calls are
wrapped in `try/except` and fall back to the deterministic path on any
failure. AI output cannot bypass authorization, status rules or validation -
only `ai_category` and `ai_confidence` fields are populated, which the
workflow never consults.

External providers may receive report text and (if configured) uploaded
photos. Keep `AI_ENABLED=false` in environments where that is not permitted.

## 8. Migration

`0002_reports` with `down_revision = "0001_core"`. Upgrade creates every
report-domain table and index; downgrade removes them in reverse order.
Applied with `alembic upgrade head` after Developer 1's `0001_core`.

## 9. Verification

```
# From backend/
.venv\Scripts\python -m pytest -q app/tests/test_reports.py
```
