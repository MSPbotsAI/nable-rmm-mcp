from collections.abc import Callable
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from .._json import dump_json_capped
from ..api_client import NableClient, NableError
from ._common import NO_TOKEN

# check_type codes documented by N-able for drive/disk space checks.
_DRIVE_SPACE_CHECK_TYPES = {"1003", "1004"}


def _as_list(value) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def register(mcp: FastMCP, client_factory: Callable[[], NableClient | None]) -> None:

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def nable_rmm_get_failing_checks(
        clientid: Annotated[
            int | None,
            Field(description="Restrict to failing checks for this client; omit for all clients."),
        ] = None,
        check_type: Annotated[
            str | None,
            Field(
                description='One of "checks" (all failures), "tasks" (Windows Automated '
                'Tasks only), "random" (spot checks only).'
            ),
        ] = None,
    ) -> str:
        """List currently failing checks, optionally scoped to one client."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.call(
                "list_failing_checks", {"clientid": clientid, "check_type": check_type}
            )
            return dump_json_capped(result)
        except NableError as e:
            return e.to_envelope()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def nable_rmm_get_checks(
        deviceid: Annotated[
            int,
            Field(description="Device ID, from nable_rmm_get_devices_at_client/get_servers/get_workstations."),
        ],
    ) -> str:
        """List all monitoring checks configured on a device."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.call("list_checks", {"deviceid": deviceid})
            return dump_json_capped(result)
        except NableError as e:
            return e.to_envelope()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def nable_rmm_get_check_config(
        checkid: Annotated[
            int, Field(description="Check ID, from nable_rmm_get_checks or nable_rmm_get_failing_checks.")
        ],
    ) -> str:
        """Get the detailed config of a single check (shape varies by check type/OS)."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.call("list_check_config", {"checkid": checkid})
            return dump_json_capped(result)
        except NableError as e:
            return e.to_envelope()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def nable_rmm_get_outages(
        deviceid: Annotated[
            int,
            Field(description="Device ID, from nable_rmm_get_devices_at_client/get_servers/get_workstations."),
        ],
    ) -> str:
        """List outages for a device: open ones, or those closed in the last 61 days.

        Covers check failures, device offline/overdue, site-down, and upload errors.
        """
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.call("list_outages", {"deviceid": deviceid})
            return dump_json_capped(result)
        except NableError as e:
            return e.to_envelope()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def nable_rmm_get_drive_space_history(
        deviceid: Annotated[
            int,
            Field(description="Device ID, from nable_rmm_get_devices_at_client/get_servers/get_workstations."),
        ],
    ) -> str:
        """Get drive/disk space check history for a device.

        Filters the device's checks to drive-space check types only; N-able RMM
        has no dedicated drive-space service.
        """
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.call("list_checks", {"deviceid": deviceid})
            checks = _as_list((result.get("items") or {}).get("check"))
            drive_checks = [
                c
                for c in checks
                if isinstance(c, dict) and c.get("check_type") in _DRIVE_SPACE_CHECK_TYPES
            ]
            return dump_json_capped({"checks": drive_checks, "total_checks": len(drive_checks)})
        except NableError as e:
            return e.to_envelope()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def nable_rmm_get_patch_list(
        deviceid: Annotated[
            int,
            Field(description="Device ID, from nable_rmm_get_devices_at_client/get_servers/get_workstations."),
        ],
    ) -> str:
        """List all patches known for a device, with status and severity."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.call("patch_list_all", {"deviceid": deviceid})
            return dump_json_capped(result)
        except NableError as e:
            return e.to_envelope()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def nable_rmm_get_performance_history(
        deviceid: Annotated[
            int,
            Field(description="Device ID, from nable_rmm_get_devices_at_client/get_servers/get_workstations."),
        ],
        interval: Annotated[
            int, Field(description="Must be 15 or 60 (minutes); no other value is accepted.")
        ],
        since: Annotated[
            str | None,
            Field(description="Optional date/time; only return data newer than this point."),
        ] = None,
    ) -> str:
        """Get historical performance metrics for a device (bandwidth, disk, CPU, memory, network).

        Covers the last 24 hours at 15-minute intervals plus the last 8 days
        hourly; consecutive identical intervals merge into one entry.
        """
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.call(
                "list_performance_history",
                {"deviceid": deviceid, "interval": interval, "since": since},
            )
            return dump_json_capped(result)
        except NableError as e:
            return e.to_envelope()
