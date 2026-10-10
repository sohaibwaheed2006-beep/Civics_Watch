"""Pydantic request and response schemas.

``common`` holds the shared conventions (error envelope, pagination, base model
config); the domain modules hold the request/response models.

The re-exports here let callers write ``from app.schemas import UserRead``
without tracking which module a type lives in.

Phase 3 adds ``department.py``.
"""

from app.schemas.auth import (
    MIN_PASSWORD_LENGTH,
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.common import (
    APIModel,
    ErrorBody,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    MessageResponse,
    Page,
    PaginationMeta,
    SortOrder,
)
from app.schemas.user import UserProfileUpdate, UserRead, UserRole

__all__ = [
    # common
    "APIModel",
    "ErrorBody",
    "ErrorDetail",
    "ErrorResponse",
    "HealthResponse",
    "MessageResponse",
    "Page",
    "PaginationMeta",
    "SortOrder",
    # auth
    "MIN_PASSWORD_LENGTH",
    "ChangePasswordRequest",
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    # user
    "UserProfileUpdate",
    "UserRead",
    "UserRole",
]
