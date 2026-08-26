from collections.abc import Callable
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from .._json import dump_json_capped
from ..api_client import NableClient, NableError
from ._common import NO_TOKEN


def register(mcp: FastMCP, client_factory: Callable[[], NableClient | None]) -> None:

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def nable_rmm_get_clients(
        devicetype: Annotated[
            Literal["server", "workstation", "mobile_device"] | None,
            Field(
                description='One of "server", "workstation", "mobile_device". N-able RMM '
                'defaults to "server" if omitted, which can hide clients that only have '
                "workstations/mobile devices — pass explicitly to see all clients."
            ),
        ] = None,
    ) -> str:
        """List all clients (customers) visible to this N-able RMM API key."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.call("list_clients", {"devicetype": devicetype})
            return dump_json_capped(result)
        except NableError as e:
            return e.to_envelope()

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def nable_rmm_get_sites(
        clientid: Annotated[int, Field(description="Client ID, from nable_rmm_get_clients.")],
    ) -> str:
        """List all sites under a client."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.call("list_sites", {"clientid": clientid})
            return dump_json_capped(result)
        except NableError as e:
            return e.to_envelope()

    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
    )
    async def nable_rmm_create_client(
        name: Annotated[
            str, Field(description="Name of the new client. Must be unique, or N-able RMM errors.")
        ],
        timezone: Annotated[
            str | None, Field(description='Timezone identifier, e.g. "Europe/Madrid".')
        ] = None,
        officehoursemail: Annotated[
            str | None, Field(description="Alert email address during office hours.")
        ] = None,
        officehourssms: Annotated[
            str | None, Field(description="Alert phone number (SMS) during office hours.")
        ] = None,
        outofofficehoursemail: Annotated[
            str | None, Field(description="Alert email address outside office hours.")
        ] = None,
        outofofficehourssms: Annotated[
            str | None, Field(description="Alert phone number (SMS) outside office hours.")
        ] = None,
    ) -> str:
        """Create a new client (customer) in N-able RMM. Adds a record; does not modify or delete anything."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.call(
                "add_client",
                {
                    "name": name,
                    "timezone": timezone,
                    "officehoursemail": officehoursemail,
                    "officehourssms": officehourssms,
                    "outofofficehoursemail": outofofficehoursemail,
                    "outofofficehourssms": outofofficehourssms,
                },
            )
            return dump_json_capped(result)
        except NableError as e:
            return e.to_envelope()

    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
    )
    async def nable_rmm_create_site(
        clientid: Annotated[int, Field(description="The client to create the site under.")],
        sitename: Annotated[str, Field(description="Name of the new site.")],
        router1: Annotated[
            str | None, Field(description="Primary router IP/hostname for connectivity checks.")
        ] = None,
        router2: Annotated[
            str | None, Field(description="Secondary router IP/hostname (dual routing).")
        ] = None,
        workstationtemplate: Annotated[
            str | None,
            Field(description='Workstation check template ID, "off", or "inherit" (default).'),
        ] = None,
        servertemplate: Annotated[
            str | None,
            Field(description='Server check template ID, "off", or "inherit" (default).'),
        ] = None,
    ) -> str:
        """Create a new site under an existing client. Adds a record; does not modify or delete anything."""
        client = client_factory()
        if client is None:
            return NO_TOKEN
        try:
            result = await client.call(
                "add_site",
                {
                    "clientid": clientid,
                    "sitename": sitename,
                    "router1": router1,
                    "router2": router2,
                    "workstationtemplate": workstationtemplate,
                    "servertemplate": servertemplate,
                },
            )
            return dump_json_capped(result)
        except NableError as e:
            return e.to_envelope()
