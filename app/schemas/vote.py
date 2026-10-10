"""Vote schemas."""

from __future__ import annotations

from app.schemas.common import APIModel

__all__ = ["VoteCountRead"]


class VoteCountRead(APIModel):
    report_id: int
    count: int
    voted: bool  # whether the current user has voted
