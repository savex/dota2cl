import re
import logging


class SecretsFilter(logging.Filter):
    """
    Masks registered secret values and common key=... / 'key': '...'
    patterns in log messages and tracebacks.
    """
    MASK = "***"
    # key=..., api_key=..., 'key': '...' in URLs, dicts and messages
    _patterns = [
        re.compile(r"(?i)(\b(?:api_)?key=)[^&\s'\"]+"),
        re.compile(r"(?i)(['\"](?:api_)?key['\"]\s*:\s*['\"])[^'\"]+"),
    ]

    def __init__(self):
        super().__init__()
        self._secrets: set[str] = set()

    def add_secret(self, value: str | None) -> None:
        if value:
            self._secrets.add(value)

    def redact(self, text: str) -> str:
        for secret in self._secrets:
            text = text.replace(secret, self.MASK)
        for pattern in self._patterns:
            text = pattern.sub(rf"\1{self.MASK}", text)
        return text

    def filter(self, record):
        # Render msg % args once, then mask the final text
        record.msg = self.redact(record.getMessage())
        record.args = None
        # Pre-render tracebacks: requests' HTTPError includes the full URL
        if record.exc_info and not record.exc_text:
            record.exc_text = logging.Formatter().formatException(
                record.exc_info)
        if record.exc_text:
            record.exc_text = self.redact(record.exc_text)
        return True


secrets_filter = SecretsFilter()
