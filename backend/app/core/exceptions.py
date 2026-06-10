class AppError(Exception):
    """Base application error with HTTP status."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ServiceUnavailableError(AppError):
    def __init__(self, message: str = "Service unavailable"):
        super().__init__(message, status_code=503)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "未登录或登录已过期"):
        super().__init__(message, status_code=401)


class BadRequestError(AppError):
    def __init__(self, message: str = "Bad request"):
        super().__init__(message, status_code=400)


class RateLimitError(AppError):
    def __init__(
        self,
        message: str = "请求过于频繁，请稍后再试",
        retry_after_sec: int = 60,
    ):
        self.retry_after_sec = retry_after_sec
        super().__init__(message, status_code=429)


def rate_limit_error_body(exc: RateLimitError) -> dict:
    return {
        "status": "error",
        "code": "RATE_LIMIT",
        "message": exc.message,
        "retry_after_sec": exc.retry_after_sec,
    }


class LLMError(AppError):
    def __init__(self, message: str = "LLM request failed"):
        super().__init__(message, status_code=502)
