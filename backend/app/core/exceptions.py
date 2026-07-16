"""Domain exceptions mapped to HTTP responses."""
from typing import Any, Optional


class AppError(Exception):
    def __init__(
        self,
        message: str = "An error occurred",
        *,
        status_code: int = 400,
        code: str = "app_error",
        details: Optional[Any] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", **kwargs):
        super().__init__(message, status_code=404, code="not_found", **kwargs)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Authentication required", **kwargs):
        super().__init__(message, status_code=401, code="unauthorized", **kwargs)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Insufficient permissions", **kwargs):
        super().__init__(message, status_code=403, code="forbidden", **kwargs)


class ConflictError(AppError):
    def __init__(self, message: str = "Conflict", **kwargs):
        super().__init__(message, status_code=409, code="conflict", **kwargs)


class ValidationAppError(AppError):
    def __init__(self, message: str = "Validation failed", **kwargs):
        super().__init__(message, status_code=422, code="validation_error", **kwargs)


class RateLimitError(AppError):
    def __init__(self, message: str = "Rate limit exceeded", **kwargs):
        super().__init__(message, status_code=429, code="rate_limit", **kwargs)
