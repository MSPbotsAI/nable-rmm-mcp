import contextvars
from collections.abc import Callable

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .api_client import NableClient
from .config import Settings

# Per-request credential isolation via contextvars.
# GatewayTokenMiddleware sets this before the MCP handler runs.
# Python asyncio copies context per task, so concurrent SSE connections are isolated.
# Value is (api_token, server_override) — server_override is None unless the
# caller sent X-Nable-Server (N-able RMM has 11 regional servers per tenant).
_gateway_creds_var: contextvars.ContextVar[tuple[str, str | None] | None] = contextvars.ContextVar(
    "nable_rmm_gateway_creds", default=None
)


def get_client_from_context(settings: Settings) -> NableClient | None:
    """Resolve the active NableClient for the current request context."""
    creds = _gateway_creds_var.get()
    if not creds:
        return None
    api_key, server_override = creds
    return NableClient(api_key, server_override or settings.nable_base_url)


class GatewayTokenMiddleware:
    """ASGI middleware.

    Reads X-Nable-Api-Token (required) and X-Nable-Server (optional, per-tenant
    regional server override) from request headers and stores them in the
    contextvar. Header names mirror the "API Token" / "URL" fields used by the
    existing N-able RMM integration on app.mspbots.ai. Returns 401 if the
    token header is missing on /mcp requests.
    """

    def __init__(self, app: ASGIApp, settings: Settings):
        self.app = app
        self.settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not path.startswith("/mcp"):
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        api_key = request.headers.get("x-nable-api-token")
        if not api_key:
            response = JSONResponse(
                {
                    "error": "Missing credentials",
                    "message": "This server requires the X-Nable-Api-Token header containing a valid N-able RMM API key",
                    "required_headers": ["X-Nable-Api-Token"],
                    "optional_headers": ["X-Nable-Server"],
                },
                status_code=401,
            )
            await response(scope, receive, send)
            return

        server_override = request.headers.get("x-nable-server")
        ctx_token = _gateway_creds_var.set((api_key, server_override))
        try:
            await self.app(scope, receive, send)
        finally:
            _gateway_creds_var.reset(ctx_token)


def create_mcp_server(settings: Settings) -> FastMCP:
    """Build the FastMCP server instance and register all N-able RMM tools."""
    # DNS-rebinding protection is a browser-oriented safeguard that rejects
    # non-localhost Host headers with 421. Disable it so the server works
    # correctly behind a reverse proxy or docker network.
    mcp = FastMCP(
        name="nable-rmm-mcp",
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    client_factory: Callable[[], NableClient | None] = lambda: get_client_from_context(settings)

    from .tools import checks, clients_sites, devices

    clients_sites.register(mcp, client_factory)
    devices.register(mcp, client_factory)
    checks.register(mcp, client_factory)

    return mcp
