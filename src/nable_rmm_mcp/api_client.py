import asyncio
from typing import Any
from xml.etree import ElementTree as ET

import httpx

from ._json import error_envelope

DEFAULT_BASE_URL = "https://www.am.remote.management"

_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)
_RETRYABLE_HTTP_STATUS = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_MAX_BACKOFF_SECONDS = 20.0

# One shared connection pool for the process lifetime. No credentials are
# ever stored on it — api_key is passed per-request as a query parameter, so
# this is safe to share across tenants/requests (see server.py's contextvar-
# based credential isolation, which is what actually keeps tenants apart).
_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True)
    return _http_client


# HTTP status_code -> (error code, retryable). status_code 0 means a network/
# connection-level failure (no response at all).
_STATUS_TO_CODE: dict[int, tuple[str, bool]] = {
    0: ("upstream_error", True),
    400: ("invalid_argument", False),
    401: ("unauthorized", False),
    403: ("unauthorized", False),
    404: ("not_found", False),
    422: ("invalid_argument", False),
    429: ("rate_limited", True),
}

# Fixed retryable default for each code in the SOP vocabulary, used when a
# NableError carries an explicit code_override instead of an HTTP status.
_CODE_RETRYABLE: dict[str, bool] = {
    "not_configured": False,
    "unauthorized": False,
    "not_found": False,
    "invalid_argument": False,
    "rate_limited": True,
    "upstream_error": True,
}

# N-able RMM's Data Extraction API frequently reports business-level failures
# as an <error> element inside an HTTP 200 XML body instead of an HTTP status
# code (e.g. a bad apikey or an unknown clientid still comes back 200 OK).
# N-able's own docs do not publish a fixed errorcode vocabulary for these
# embedded errors, so we classify them by keyword in the message text — this
# is a best-effort heuristic, not a documented contract.
_UNAUTHORIZED_HINTS = (
    "api key",
    "apikey",
    "not authoris",
    "not authoriz",
    "access denied",
    "permission",
)
_NOT_FOUND_HINTS = (
    "does not exist",
    "not exist",
    "not found",
    "no such",
    "unknown client",
    "unknown site",
    "unknown device",
)
_RATE_LIMIT_HINTS = ("rate limit", "too many requests", "throttle")


def _classify_http(status_code: int) -> tuple[str, bool]:
    if status_code in _STATUS_TO_CODE:
        return _STATUS_TO_CODE[status_code]
    if status_code >= 500:
        return "upstream_error", True
    return "invalid_argument", False


def _classify_embedded(message: str) -> tuple[str, bool]:
    lower = message.lower()
    if any(h in lower for h in _RATE_LIMIT_HINTS):
        return "rate_limited", True
    if any(h in lower for h in _UNAUTHORIZED_HINTS):
        return "unauthorized", False
    if any(h in lower for h in _NOT_FOUND_HINTS):
        return "not_found", False
    return "invalid_argument", False


class NableError(Exception):
    """Domain error for N-able RMM API failures.

    Covers three distinct failure shapes:
    - HTTP-level failures (``status_code`` set): connection errors
      (``status_code=0``), 4xx, 5xx.
    - Business-level failures embedded in an HTTP 200 XML ``<error>``
      element (``status_code`` is ``None``, classified from the message).
    - Cases with an unambiguous code known at raise time (``code_override``),
      e.g. malformed XML from the upstream service.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        xml_error_code: str | None = None,
        code_override: str | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.xml_error_code = xml_error_code
        self.code_override = code_override
        suffix = f" ({xml_error_code})" if xml_error_code else ""
        super().__init__(f"N-able RMM API error{suffix}: {message}")

    def _classify(self) -> tuple[str, bool]:
        if self.code_override is not None:
            return self.code_override, _CODE_RETRYABLE[self.code_override]
        if self.status_code is not None:
            return _classify_http(self.status_code)
        return _classify_embedded(self.message)

    def is_retryable(self) -> bool:
        return self._classify()[1]

    def to_envelope(self) -> str:
        code, retryable = self._classify()
        return error_envelope(code, self.message, retryable)


def _elem_to_obj(elem: ET.Element) -> Any:
    """Recursively convert an XML element into a JSON-friendly dict/str.

    Repeated child tags (e.g. multiple <site> nodes under <items>) become a
    list. Leaf elements with no children collapse to their text content.
    """
    children = list(elem)
    if not children:
        text = (elem.text or "").strip()
        if elem.attrib:
            obj: dict[str, Any] = dict(elem.attrib)
            if text:
                obj["_text"] = text
            return obj
        return text

    obj = dict(elem.attrib)
    for child in children:
        value = _elem_to_obj(child)
        if child.tag in obj:
            existing = obj[child.tag]
            if isinstance(existing, list):
                existing.append(value)
            else:
                obj[child.tag] = [existing, value]
        else:
            obj[child.tag] = value
    return obj


class NableClient:
    """Async httpx client wrapping the N-able RMM (N-sight) query-param API.

    Every N-able RMM service call — reads and writes alike — is a GET request
    with the api key and all arguments passed as query parameters; the
    response is XML, which this client parses into a nested dict. Reuses the
    module-level connection pool (see _get_http_client) across every call
    made through this instance, rather than opening a new connection per
    request.
    """

    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL):
        self._api_key = api_key
        self._base_url = self._normalize_base_url(base_url)

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        base_url = base_url.strip().rstrip("/")
        # The "URL" field on the app.mspbots.ai integration form is freeform
        # text — real tenant configs may omit the scheme (e.g. "www.systemmonitor.us").
        if not base_url.startswith(("http://", "https://")):
            base_url = f"https://{base_url}"
        return base_url

    async def call(self, service: str, params: dict | None = None) -> Any:
        query: dict[str, Any] = {"apikey": self._api_key, "service": service}
        for key, value in (params or {}).items():
            if value is not None:
                query[key] = value

        target = f"{self._base_url}/api/"
        client = _get_http_client()

        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = await client.get(target, params=query)
            except httpx.RequestError as e:
                last_exc = e
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(min(2**attempt, _MAX_BACKOFF_SECONDS))
                    continue
                raise NableError(f"Could not reach {target!r}: {e}", status_code=0) from None

            if resp.status_code in _RETRYABLE_HTTP_STATUS and attempt < _MAX_RETRIES:
                await asyncio.sleep(self._retry_delay(resp, attempt))
                continue

            if resp.status_code >= 400:
                raise NableError(
                    f"HTTP {resp.status_code}: {resp.text[:300]}", status_code=resp.status_code
                )

            try:
                return self._parse(resp.text)
            except NableError as e:
                if e.is_retryable() and attempt < _MAX_RETRIES:
                    await asyncio.sleep(min(2**attempt, _MAX_BACKOFF_SECONDS))
                    continue
                raise

        # Unreachable in practice (loop always returns or raises above), but
        # keeps type checkers happy and guards against future edits.
        if last_exc:
            raise NableError(f"{last_exc}", status_code=0) from last_exc
        raise NableError("request failed with no response", status_code=0)

    def _retry_delay(self, resp: httpx.Response, attempt: int) -> float:
        retry_after = resp.headers.get("Retry-After")
        if retry_after:
            try:
                return min(float(retry_after), _MAX_BACKOFF_SECONDS)
            except ValueError:
                pass
        return min(2**attempt, _MAX_BACKOFF_SECONDS)

    def _parse(self, xml_text: str) -> Any:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            raise NableError(
                f"Malformed XML response: {e}", code_override="upstream_error"
            ) from None

        error = root.find("error")
        if error is not None:
            message = error.findtext("message") or "Unknown error"
            code = error.findtext("errorcode")
            raise NableError(message, xml_error_code=code)

        status = root.attrib.get("status")
        if status and status.upper() == "FAIL":
            raise NableError(
                "Request failed with no error detail in response", code_override="invalid_argument"
            )

        return _elem_to_obj(root)
