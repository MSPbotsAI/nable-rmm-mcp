from collections.abc import Callable
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from .._json import dump_json_capped
from ..api_client import NableClient, NableError
from ._common import NO_TOKEN

_DEVICE_TYPE_DESC = 'One of "server", "workstation", "mobile_device".'


def register(mcp: FastMCP, client_factory: Callable[[], NableClient | None]) -> None:

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def nable_rmm_get_devices_at_client(
        clientid: Annotated[int, Field(description="Client ID, from nable_rmm_get_clients.")],
        devicetype: Annotated[str, Field(description=_DEVICE_TYPE_DESC)],
    ) -> str:
        """List devices of a given type across all sites for a client."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.call(
                "list_devices_at_client", {"clientid": clientid, "devicetype": devicetype}
            )
            return dump_json_capped(result)
        except NableError as e:
            return e.to_envelope()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def nable_rmm_get_servers(
        siteid: Annotated[int, Field(description="Site ID, from nable_rmm_get_sites.")],
    ) -> str:
        """List server devices at a site, with online/check status and agent info."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.call("list_servers", {"siteid": siteid})
            return dump_json_capped(result)
        except NableError as e:
            return e.to_envelope()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def nable_rmm_get_workstations(
        siteid: Annotated[int, Field(description="Site ID, from nable_rmm_get_sites.")],
    ) -> str:
        """List workstation devices at a site, with online/check status and agent info."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.call("list_workstations", {"siteid": siteid})
            return dump_json_capped(result)
        except NableError as e:
            return e.to_envelope()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def nable_rmm_get_agentless_assets(
        siteid: Annotated[int, Field(description="Site ID, from nable_rmm_get_sites.")],
    ) -> str:
        """List agentless (network-scanned) assets at a site.

        N-able has marked this feature deprecated; may return empty on newer accounts.
        """
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.call("list_agentless_assets", {"siteid": siteid})
            return dump_json_capped(result)
        except NableError as e:
            return e.to_envelope()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def nable_rmm_get_device_monitoring_details(
        deviceid: Annotated[
            int,
            Field(description="Device ID, from nable_rmm_get_devices_at_client/get_servers/get_workstations."),
        ],
    ) -> str:
        """Get detailed monitoring info for a single server/workstation device."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.call("list_device_monitoring_details", {"deviceid": deviceid})
            return dump_json_capped(result)
        except NableError as e:
            return e.to_envelope()
