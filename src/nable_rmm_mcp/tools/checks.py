import json
from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..api_client import NableClient, NableError

_NO_TOKEN = "Error: No N-able RMM API key. Send the X-Nable-Api-Token header."

# check_type codes documented by N-able for drive/disk space checks.
_DRIVE_SPACE_CHECK_TYPES = {"1003", "1004"}


def _as_list(value) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def register(mcp: FastMCP, client_factory: Callable[[], NableClient | None]) -> None:

    @mcp.tool()
    async def nable_rmm_get_failing_checks(
        clientid: int | None = None,
        check_type: str | None = None,
    ) -> str:
        """List currently failing checks, optionally scoped to one client.

        Args:
            clientid: Restrict to failing checks for this client. Omit for
                all clients visible to this API key.
            check_type: One of "checks" (all check failures), "tasks"
                (Windows Automated Tasks only), "random" (spot checks only).
        """
        client = client_factory()
        if client is None:
            return _NO_TOKEN
        try:
            result = await client.call(
                "list_failing_checks", {"clientid": clientid, "check_type": check_type}
            )
            return json.dumps(result, indent=2)
        except NableError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def nable_rmm_get_checks(deviceid: int) -> str:
        """List all monitoring checks configured on a device.

        Args:
            deviceid: Device ID — from nable_rmm_get_devices_at_client,
                nable_rmm_get_servers, or nable_rmm_get_workstations.
        """
        client = client_factory()
        if client is None:
            return _NO_TOKEN
        try:
            result = await client.call("list_checks", {"deviceid": deviceid})
            return json.dumps(result, indent=2)
        except NableError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def nable_rmm_get_check_config(checkid: int) -> str:
        """Get the detailed configuration of a single check (structure varies by check type/OS).

        Args:
            checkid: Check ID, from nable_rmm_get_checks or nable_rmm_get_failing_checks.
        """
        client = client_factory()
        if client is None:
            return _NO_TOKEN
        try:
            result = await client.call("list_check_config", {"checkid": checkid})
            return json.dumps(result, indent=2)
        except NableError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def nable_rmm_get_outages(deviceid: int) -> str:
        """List outages for a device that are open, or were closed in the last 61 days.

        Covers check failures, device offline/overdue, site-down, and upload
        errors.

        Args:
            deviceid: Device ID — from nable_rmm_get_devices_at_client,
                nable_rmm_get_servers, or nable_rmm_get_workstations.
        """
        client = client_factory()
        if client is None:
            return _NO_TOKEN
        try:
            result = await client.call("list_outages", {"deviceid": deviceid})
            return json.dumps(result, indent=2)
        except NableError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def nable_rmm_get_drive_space_history(deviceid: int) -> str:
        """Get drive/disk space check history for a device.

        This calls N-able RMM's generic check-listing service and filters to
        check_type 1003 (Drive Space Change Check) and 1004 (Disk Space
        Check) — N-able RMM does not expose a dedicated drive-space service.

        Args:
            deviceid: Device ID — from nable_rmm_get_devices_at_client,
                nable_rmm_get_servers, or nable_rmm_get_workstations.
        """
        client = client_factory()
        if client is None:
            return _NO_TOKEN
        try:
            result = await client.call("list_checks", {"deviceid": deviceid})
            checks = _as_list((result.get("items") or {}).get("check"))
            drive_checks = [
                c
                for c in checks
                if isinstance(c, dict) and c.get("check_type") in _DRIVE_SPACE_CHECK_TYPES
            ]
            return json.dumps({"checks": drive_checks, "total_checks": len(drive_checks)}, indent=2)
        except NableError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def nable_rmm_get_patch_list(deviceid: int) -> str:
        """List all patches known for a device, with status and severity.

        Args:
            deviceid: Device ID — from nable_rmm_get_devices_at_client,
                nable_rmm_get_servers, or nable_rmm_get_workstations.
        """
        client = client_factory()
        if client is None:
            return _NO_TOKEN
        try:
            result = await client.call("patch_list_all", {"deviceid": deviceid})
            return json.dumps(result, indent=2)
        except NableError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def nable_rmm_get_performance_history(
        deviceid: int,
        interval: str | None = None,
        since: str | None = None,
    ) -> str:
        """Get historical performance metrics for a device (bandwidth, disk,
        CPU, memory, network interface utilization).

        Data covers the last 24 hours at 15-minute intervals, plus the last
        8 days at hourly intervals. Consecutive identical intervals merge
        into a single entry.

        Args:
            deviceid: Device ID — from nable_rmm_get_devices_at_client,
                nable_rmm_get_servers, or nable_rmm_get_workstations.
            interval: Optional — accepted values are not fully documented by
                N-able's public API reference; pass through only if you have
                a confirmed value for your account.
            since: Optional date/time to limit results to data newer than
                this point, to avoid re-fetching the full 8-day history.
        """
        client = client_factory()
        if client is None:
            return _NO_TOKEN
        try:
            result = await client.call(
                "list_performance_history",
                {"deviceid": deviceid, "interval": interval, "since": since},
            )
            return json.dumps(result, indent=2)
        except NableError as e:
            return f"Error: {e}"
