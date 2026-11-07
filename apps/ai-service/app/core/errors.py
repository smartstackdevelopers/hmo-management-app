from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status


class AiServiceError(Exception):
    """Base error with a safe public category (never leak secrets)."""

    def __init__(self, category: str, message: str, *, status_code: int = 400) -> None:
        self.category = category
        self.message = message
        self.status_code = status_code
        super().__init__(message)

    def to_http(self) -> HTTPException:
        return HTTPException(
            status_code=self.status_code,
            detail={"error": self.category, "message": self.message},
        )


class AuthError(AiServiceError):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__("auth_error", message, status_code=status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(AiServiceError):
    def __init__(self, message: str = "Access denied") -> None:
        super().__init__("forbidden", message, status_code=status.HTTP_403_FORBIDDEN)


class ValidationServiceError(AiServiceError):
    def __init__(self, message: str) -> None:
        super().__init__("validation_error", message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class PromptError(AiServiceError):
    def __init__(self, message: str, *, status_code: int = 404) -> None:
        super().__init__("prompt_error", message, status_code=status_code)


class ProviderError(AiServiceError):
    def __init__(self, message: str, *, status_code: int = 503) -> None:
        super().__init__("provider_error", message, status_code=status_code)


class WorkflowError(AiServiceError):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__("workflow_error", message, status_code=status_code)


def safe_error_body(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, AiServiceError):
        return {"error": exc.category, "message": exc.message}
    return {"error": "internal_error", "message": "An unexpected error occurred"}
