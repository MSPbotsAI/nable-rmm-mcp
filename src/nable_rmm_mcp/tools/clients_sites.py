import json
from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..api_client import NableClient, NableError

_NO_TOKEN = "Error: No N-able RMM API key. Send the X-Nable-Api-Token header."


def register(mcp: FastMCP, client_factory: Callable[[], NableClient | None]) -> None:

    @mcp.tool()
    async def nable_rmm_get_clients(devicetype: str | None = None) -> str:
        """List all clients (customers) visible to this N-able RMM API key.

        Args:
            devicetype: Filter to clients with active devices of this type.
                One of "server", "workstation", "mobile_device". N-able RMM
                defaults to "server" if omitted — pass explicitly to avoid
                missing clients that only have workstations/mobile devices.
        """
        client = client_factory()
        if client is None:
            return _NO_TOKEN
        try:
            result = await client.call("list_clients", {"devicetype": devicetype})
            return json.dumps(result, indent=2)
        except NableError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def nable_rmm_get_sites(clientid: int) -> str:
        """List all sites under a client.

        Args:
            clientid: Client ID, from nable_rmm_get_clients.
        """
        client = client_factory()
        if client is None:
            return _NO_TOKEN
        try:
            result = await client.call("list_sites", {"clientid": clientid})
            return json.dumps(result, indent=2)
        except NableError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def nable_rmm_create_client(
        name: str,
        timezone: str | None = None,
        officehoursemail: str | None = None,
        officehourssms: str | None = None,
        outofofficehoursemail: str | None = None,
        outofofficehourssms: str | None = None,
    ) -> str:
        """Create a new client (customer) in N-able RMM.

        Args:
            name: Name of the new client. Must be unique — a duplicate name
                returns an error from N-able RMM.
            timezone: Timezone identifier, e.g. "Europe/Madrid".
            officehoursemail: Alert email address during office hours.
            officehourssms: Alert phone number (SMS) during office hours.
            outofofficehoursemail: Alert email address outside office hours.
            outofofficehourssms: Alert phone number (SMS) outside office hours.
        """
        client = client_factory()
        if client is None:
            return _NO_TOKEN
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
            return json.dumps(result, indent=2)
        except NableError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def nable_rmm_create_site(
        clientid: int,
        sitename: str,
        router1: str | None = None,
        router2: str | None = None,
        workstationtemplate: str | None = None,
        servertemplate: str | None = None,
    ) -> str:
        """Create a new site under an existing client.

        Args:
            clientid: The client to create the site under.
            sitename: Name of the new site.
            router1: Primary router IP/hostname for connectivity checks.
            router2: Secondary router IP/hostname (dual routing).
            workstationtemplate: Workstation check template id, "off", or
                "inherit" (default).
            servertemplate: Server check template id, "off", or "inherit"
                (default).
        """
        client = client_factory()
        if client is None:
            return _NO_TOKEN
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
            return json.dumps(result, indent=2)
        except NableError as e:
            return f"Error: {e}"
