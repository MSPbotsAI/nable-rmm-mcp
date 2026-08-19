"""tools/list snapshot + error-envelope mapping tests.

No network calls: tool enumeration goes through FastMCP's in-process
list_tools(), and the error-code mapping is tested directly against
NableError, independent of any real HTTP request.
"""

import json

import pytest

from nable_rmm_mcp.api_client import NableError
from nable_rmm_mcp.config import Settings
from nable_rmm_mcp.server import create_mcp_server

# name -> (required params, readOnlyHint)
EXPECTED_TOOLS = {
    "nable_rmm_get_failing_checks": (set(), True),
    "nable_rmm_get_checks": ({"deviceid"}, True),
    "nable_rmm_get_check_config": ({"checkid"}, True),
    "nable_rmm_get_outages": ({"deviceid"}, True),
    "nable_rmm_get_drive_space_history": ({"deviceid"}, True),
    "nable_rmm_get_patch_list": ({"deviceid"}, True),
    "nable_rmm_get_performance_history": ({"deviceid", "interval"}, True),
    "nable_rmm_get_clients": (set(), True),
    "nable_rmm_get_sites": ({"clientid"}, True),
    "nable_rmm_create_client": ({"name"}, False),
    "nable_rmm_create_site": ({"clientid", "sitename"}, False),
    "nable_rmm_get_devices_at_client": ({"clientid", "devicetype"}, True),
    "nable_rmm_get_servers": ({"siteid"}, True),
    "nable_rmm_get_workstations": ({"siteid"}, True),
    "nable_rmm_get_agentless_assets": ({"siteid"}, True),
    "nable_rmm_get_device_monitoring_details": ({"deviceid"}, True),
}


@pytest.mark.asyncio
async def test_tools_list_snapshot():
    mcp = create_mcp_server(Settings())
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert names == set(EXPECTED_TOOLS), f"unexpected tool set: {names}"

    by_name = {t.name: t for t in tools}
    for name, (expected_required, expected_readonly) in EXPECTED_TOOLS.items():
        tool = by_name[name]
        required = set(tool.inputSchema.get("required", []))
        assert required == expected_required, f"{name}: required={required}"
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is expected_readonly, f"{name}: readOnlyHint mismatch"
        if not expected_readonly:
            assert tool.annotations.destructiveHint is False, f"{name}: expected destructiveHint=False"
        assert len(tool.description or "") <= 500, f"{name}: description too long"
        first_line = (tool.description or "").strip().splitlines()[0]
        assert len(first_line) <= 100, f"{name}: first line too long: {first_line!r}"


@pytest.mark.asyncio
async def test_service_instructions_present_and_bounded():
    mcp = create_mcp_server(Settings())
    assert mcp.instructions
    assert len(mcp.instructions) <= 1500


@pytest.mark.parametrize(
    "status_code,expected_code,expected_retryable",
    [
        (0, "upstream_error", True),
        (400, "invalid_argument", False),
        (401, "unauthorized", False),
        (403, "unauthorized", False),
        (404, "not_found", False),
        (422, "invalid_argument", False),
        (429, "rate_limited", True),
        (500, "upstream_error", True),
        (503, "upstream_error", True),
    ],
)
def test_http_error_envelope_mapping(status_code, expected_code, expected_retryable):
    err = NableError("boom", status_code=status_code)
    envelope = json.loads(err.to_envelope())
    assert envelope["error"]["code"] == expected_code
    assert envelope["error"]["retryable"] is expected_retryable
    assert envelope["error"]["message"] == "boom"


@pytest.mark.parametrize(
    "message,expected_code,expected_retryable",
    [
        ("Invalid API key supplied", "unauthorized", False),
        ("Client does not exist", "not_found", False),
        ("Rate limit exceeded, try again later", "rate_limited", True),
        ("Some other validation failure", "invalid_argument", False),
    ],
)
def test_embedded_xml_error_envelope_mapping(message, expected_code, expected_retryable):
    err = NableError(message, xml_error_code="1")
    envelope = json.loads(err.to_envelope())
    assert envelope["error"]["code"] == expected_code
    assert envelope["error"]["retryable"] is expected_retryable


def test_malformed_xml_maps_to_upstream_error():
    err = NableError("Malformed XML response: bad token", code_override="upstream_error")
    envelope = json.loads(err.to_envelope())
    assert envelope["error"]["code"] == "upstream_error"
    assert envelope["error"]["retryable"] is True
