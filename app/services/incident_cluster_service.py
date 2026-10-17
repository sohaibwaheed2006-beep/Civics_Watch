"""Incident clustering - group reports describing the same real-world event.

When 15 neighbors file separate reports for a single burst main, the dispatch
queue should not contain 15 tickets. This service runs at submission:

* It asks :mod:`duplicate_detection_service` for likely duplicates of the new
  report.
* If a match crosses the configured link threshold it either joins the
  existing cluster (inheriting the ``incident_cluster_id``) or forms a new
  cluster containing both reports.
* The ``duplicate_of_report_id`` pointer always targets the canonical (oldest)
  report in the cluster so cascade actions have a clear anchor.

``cascade_resolve`` applies a status change to every member of a cluster in
one go, which is how a worker's single "fixed" closure resolves all 15 citizen
tickets at the same time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import ReportStatus
from app.core.logging import get_logger
from app.models.report import Report
from app.services import duplicate_detection_service

logger = get_logger(__name__)

__all__ = [
    "ClusterInfo",
    "attach_to_cluster",
    "cluster_members",
    "cascade_resolve",
]


@dataclass(frozen=True, slots=True)
class ClusterInfo:
    cluster_id: int
    canonical_report_id: int
    members: Sequence[Report]


def _next_cluster_id(db: Session) -> int:
    """Allocate a fresh cluster id. SQLite-safe (no sequences)."""
    current = db.execute(
        select(func.coalesce(func.max(Report.incident_cluster_id), 0))
    ).scalar_one()
    return int(current or 0) + 1


def attach_to_cluster(
    db: Session, *, report: Report
) -> int | None:
    """Place ``report`` into a cluster if any likely-duplicate is close enough.

    Returns the ``incident_cluster_id`` applied, or ``None`` if the report
    stands alone. Mutates ``report`` in place: sets ``incident_cluster_id`` and
    ``duplicate_of_report_id`` when a cluster is joined; the caller flushes.
    """
    settings = get_settings()
    link_threshold = settings.CLUSTER_LINK_MIN_SCORE

    matches = duplicate_detection_service.find_duplicates(
        db,
        latitude=report.latitude,
        longitude=report.longitude,
        title=report.title,
        description=report.description,
        category=report.category,
        exclude_report_id=report.id,
        limit=5,
    )
    if not matches:
        return None

    top = matches[0]
    if top.score < link_threshold:
        return None

    # Prefer joining the match's existing cluster if it has one.
    cluster_id: int
    canonical_id: int
    if top.report.incident_cluster_id is not None:
        cluster_id = top.report.incident_cluster_id
        # Find the oldest member of that cluster as the canonical.
        oldest = db.execute(
            select(Report)
            .where(Report.incident_cluster_id == cluster_id)
            .order_by(Report.created_at.asc(), Report.id.asc())
            .limit(1)
        ).scalar_one_or_none()
        canonical_id = oldest.id if oldest is not None else top.report.id
    else:
        cluster_id = _next_cluster_id(db)
        # Both the match and the new report join a brand-new cluster. The
        # match is the older of the pair.
        top.report.incident_cluster_id = cluster_id
        canonical_id = top.report.id

    report.incident_cluster_id = cluster_id
    if report.id != canonical_id:
        report.duplicate_of_report_id = canonical_id
    report.duplicate_score = top.score

    logger.info(
        "Clustered report=%s into cluster=%s canonical=%s score=%.2f",
        report.id,
        cluster_id,
        canonical_id,
        top.score,
    )
    return cluster_id


def cluster_members(
    db: Session, *, cluster_id: int
) -> Sequence[Report]:
    stmt = (
        select(Report)
        .where(Report.incident_cluster_id == cluster_id)
        .order_by(Report.created_at.asc(), Report.id.asc())
    )
    return db.execute(stmt).scalars().all()


def cascade_resolve(
    db: Session,
    *,
    cluster_id: int,
    new_status: ReportStatus,
    exclude_report_id: int | None = None,
) -> int:
    """Advance every cluster member (except ``exclude_report_id``) to the status.

    This is a bulk no-history write: it exists so a single worker closure
    propagates to the duplicate tickets without spawning N notifications. The
    history row for the canonical report already documents the closure.

    Returns the number of rows updated.
    """
    stmt = select(Report).where(Report.incident_cluster_id == cluster_id)
    if exclude_report_id is not None:
        stmt = stmt.where(Report.id != exclude_report_id)
    affected = 0
    for member in db.execute(stmt).scalars().all():
        if member.status == new_status:
            continue
        member.status = new_status
        if new_status == ReportStatus.RESOLVED:
            from app.db.base import utcnow

            member.resolved_at = utcnow()
        affected += 1
    return affected
