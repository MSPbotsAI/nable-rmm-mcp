import json
from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..api_client import NableClient, NableError

_NO_TOKEN = "Error: No N-able RMM API key. Send the X-Nable-Api-Token header."


def register(mcp: FastMCP, client_factory: Callable[[], NableClient | None]) -> None:

    @mcp.tool()
    async def nable_rmm_get_devices_at_client(clientid: int, devicetype: str) -> str:
        """List devices of a given type across all sites for a client.

        Args:
            clientid: Client ID, from nable_rmm_get_clients.
            devicetype: One of "server", "workstation", "mobile_device".
        """
        client = client_factory()
        if client is None:
            return _NO_TOKEN
        try:
            result = await client.call(
                "list_devices_at_client", {"clientid": clientid, "devicetype": devicetype}
            )
            return json.dumps(result, indent=2)
        except NableError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def nable_rmm_get_servers(siteid: int) -> str:
        """List all server devices at a site, with online/check status and agent info.

        Args:
            siteid: Site ID, from nable_rmm_get_sites.
        """
        client = client_factory()
        if client is None:
            return _NO_TOKEN
        try:
            result = await client.call("list_servers", {"siteid": siteid})
            return json.dumps(result, indent=2)
        except NableError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def nable_rmm_get_workstations(siteid: int) -> str:
        """List all workstation devices at a site, with online/check status and agent info.

        Args:
            siteid: Site ID, from nable_rmm_get_sites.
        """
        client = client_factory()
        if client is None:
            return _NO_TOKEN
        try:
            result = await client.call("list_workstations", {"siteid": siteid})
            return json.dumps(result, indent=2)
        except NableError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def nable_rmm_get_agentless_assets(siteid: int) -> str:
        """List agentless (network-scanned) assets at a site.

        Note: N-able has marked the agentless assets feature as deprecated —
        this may return empty results on newer accounts.

        Args:
            siteid: Site ID, from nable_rmm_get_sites.
        """
        client = client_factory()
        if client is None:
            return _NO_TOKEN
        try:
            result = await client.call("list_agentless_assets", {"siteid": siteid})
            return json.dumps(result, indent=2)
        except NableError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def nable_rmm_get_device_monitoring_details(deviceid: int) -> str:
        """Get detailed monitoring info for a single server/workstation device.

        Args:
            deviceid: Device ID — from nable_rmm_get_devices_at_client,
                nable_rmm_get_servers, or nable_rmm_get_workstations.
        """
        client = client_factory()
        if client is None:
            return _NO_TOKEN
        try:
            result = await client.call("list_device_monitoring_details", {"deviceid": deviceid})
            return json.dumps(result, indent=2)
        except NableError as e:
            return f"Error: {e}"
