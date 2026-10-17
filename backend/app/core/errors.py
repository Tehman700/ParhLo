"""App-level exceptions. Raise these from services; main.py maps them to HTTP responses."""


class AppError(Exception):
    status_code = 400

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class NotConfiguredError(AppError):
    """A feature needs configuration (e.g. an API key) that is missing."""

    status_code = 503


class UpstreamError(AppError):
    """An external service (LLM provider, etc.) failed."""

    status_code = 502


class NotFoundError(AppError):
    status_code = 404
