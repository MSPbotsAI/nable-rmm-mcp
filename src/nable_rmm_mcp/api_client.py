from typing import Any
from xml.etree import ElementTree as ET

import httpx

DEFAULT_BASE_URL = "https://www.am.remote.management"


class NableError(Exception):
    def __init__(self, message: str, error_code: str | None = None):
        self.error_code = error_code
        suffix = f" ({error_code})" if error_code else ""
        super().__init__(f"N-able RMM API error{suffix}: {message}")


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
    response is XML, which this client parses into a nested dict.
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

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self._base_url}/api/", params=query)
            if resp.status_code >= 400:
                raise NableError(f"HTTP {resp.status_code}: {resp.text[:300]}")
            return self._parse(resp.text)

    def _parse(self, xml_text: str) -> Any:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            raise NableError(f"Malformed XML response: {e}") from None

        error = root.find("error")
        if error is not None:
            message = error.findtext("message") or "Unknown error"
            code = error.findtext("errorcode")
            raise NableError(message, code)

        status = root.attrib.get("status")
        if status and status.upper() == "FAIL":
            raise NableError("Request failed with no error detail in response")

        return _elem_to_obj(root)
