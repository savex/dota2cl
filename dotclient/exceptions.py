#    Author: Alex Savatieiev (a.savex@gmail.com)
#    November 2025


class DotClientError(Exception):
    """
    Base class for all dotclient errors.
    """


class InvalidEndpointError(DotClientError, ValueError):
    """
    Raised when an endpoint is not present in the loaded API schema.
    """


class SchemaLoadError(DotClientError):
    """
    Raised when the API schema could not be fetched or parsed.
    """


class ApiRequestError(DotClientError):
    """
    Raised when a request to the API fails
    (connection error, timeout or HTTP error status).
    Messages never include the request URL, as it may contain the API key.
    """
    def __init__(self, message: str, endpoint: str | None = None,
                 status_code: int | None = None):
        super().__init__(message)
        self.endpoint = endpoint
        self.status_code = status_code


class RateLimitError(ApiRequestError):
    """
    Raised when the API keeps returning 429 Too Many Requests
    after all retries are used.
    """
    def __init__(self, message: str, endpoint: str | None = None,
                 retry_after: float | None = None):
        super().__init__(message, endpoint=endpoint, status_code=429)
        self.retry_after = retry_after


class NotFoundError(ApiRequestError):
    """
    Raised when the API returns 404 for the requested resource.
    """
    def __init__(self, message: str, endpoint: str | None = None):
        super().__init__(message, endpoint=endpoint, status_code=404)


class InvalidResponseError(DotClientError):
    """
    Raised when a response body is not valid JSON
    or does not have the expected shape.
    """
