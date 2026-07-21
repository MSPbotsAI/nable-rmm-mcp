# nable-rmm-mcp

**N-able RMM** MCP server — exposes the N-able RMM Data Extraction API as MCP tools.

> **Naming note:** this integration is called **"N-able RMM"** in app.mspbots.ai (`sys_integration.subject_code = SOLARWIND` — it was originally SolarWinds RMM). N-able's own public developer docs call the same product **"N-sight"** (`https://developer.n-able.com/n-sight/docs/...`). This is a different product from **N-able N-Central**, which is a separate integration in app.mspbots.ai with its own API. This server wraps N-sight/N-able RMM only.

## Overview

This server implements the [Model Context Protocol](https://modelcontextprotocol.io/) (Streamable HTTP/SSE transport) and wraps the [N-sight API](https://developer.n-able.com/n-sight/docs/getting-started-with-the-n-sight-api) (the API behind the "N-able RMM" integration). It follows the MSPbots **Vendor MCP Service SOP**: stateless, no stored credentials, per-request header authentication.

The underlying API itself authenticates via an `apikey` query parameter and returns XML. This server never stores that key — the caller passes it per-request via a header, and every tool response is the XML converted to JSON for readability.

## Quick Start

### Docker (recommended)

```bash
docker compose up --build
```

The server starts on `http://localhost:8080`.

### Local (uv)

```bash
uv sync
python -m nable_rmm_mcp
```

## Health Check

```bash
curl http://localhost:8080/health
# {"status": "ok", "service": "nable-rmm-mcp", "transport": "http"}
```

No token is required for the health endpoint.

## 授权参数说明 (Authentication)

Every request to `/mcp` must include the following HTTP headers. Header naming mirrors the fields on the existing "N-able RMM" integration form in app.mspbots.ai (**API Token** / **URL**).

| Header | 类型 | 是否必填 | 默认值 | 枚举值 | 字段描述 | Example |
|---|---|---|---|---|---|---|
| `X-Nable-Api-Token` | string | 必填 | 无 | 无(自由文本) | N-able RMM API key,在 **Settings > General Settings > API > Generate** 生成。若 key 被限定到某个 client group,调用只返回该组内客户的数据。 | `X-Nable-Api-Token: <your_api_key>` |
| `X-Nable-Server` | string | 可选 | `NABLE_BASE_URL` 环境变量(默认 `https://www.am.remote.management`) | 见下方 11 个地区服务器列表 | N-able RMM 按账号所属地区分为 11 个独立服务器,不带该 header 时用环境变量默认值;网关同时服务多地区租户时按请求覆盖。 | `X-Nable-Server: https://www.systemmonitor.co.uk` |

`X-Nable-Server` 的 11 个枚举值(地区 → Base URL):

| Region | Base URL |
|---|---|
| Americas (default) | `https://www.am.remote.management` |
| Asia | `https://wwwasia.system-monitor.com` |
| Australia | `https://www.system-monitor.com` |
| Europe | `https://wwweurope1.systemmonitor.eu.com` |
| France | `https://wwwfrance.systemmonitor.eu.com` |
| France1 | `https://wwwfrance1.systemmonitor.eu.com` |
| Germany | `https://wwwgermany1.systemmonitor.eu.com` |
| Ireland | `https://wwwireland.systemmonitor.eu.com` |
| Poland | `https://wwwpoland1.systemmonitor.eu.com` |
| United Kingdom | `https://www.systemmonitor.co.uk` |
| United States | `https://www.systemmonitor.us` |

Missing `X-Nable-Api-Token` returns `401 Unauthorized`. N-able RMM also caps automated calls at **60 requests/minute per key** — this server does not throttle for you, so pace bulk calls accordingly.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MCP_HTTP_PORT` | `8080` | Listening port |
| `MCP_HTTP_HOST` | `0.0.0.0` | Listening host |
| `NABLE_BASE_URL` | `https://www.am.remote.management` | Default regional server; override per-request with `X-Nable-Server` |

## MCP Endpoint

```
POST http://localhost:8080/mcp
```

Connect your MCP client with:
- Transport: `http` (Streamable HTTP / SSE)
- Headers: `X-Nable-Api-Token: <api_key>` (required), `X-Nable-Server: <base_url>` (optional)

## Tool List

16 tools, covering the full public N-sight API reference plus the 4 endpoints already in production use under app.mspbots.ai's "N-able RMM" integration (Device Monitoring Details, Drive Space History, Patch, Performance History).

### Clients & Sites

| Tool | 功能 | 参数 |
|---|---|---|
| `nable_rmm_get_clients` | 列出该 API key 可见的所有客户 | `devicetype?`("server"/"workstation"/"mobile_device") |
| `nable_rmm_get_sites` | 列出某客户下的所有站点 | `clientid` (必填, int) |
| `nable_rmm_create_client` | 新建客户(写操作) | `name` (必填), `timezone?`, `officehoursemail?`, `officehourssms?`, `outofofficehoursemail?`, `outofofficehourssms?` |
| `nable_rmm_create_site` | 在客户下新建站点(写操作) | `clientid` (必填), `sitename` (必填), `router1?`, `router2?`, `workstationtemplate?`, `servertemplate?` |

### Devices

| Tool | 功能 | 参数 |
|---|---|---|
| `nable_rmm_get_devices_at_client` | 按设备类型列出客户下所有站点的设备 | `clientid` (必填), `devicetype` (必填, "server"/"workstation"/"mobile_device") |
| `nable_rmm_get_servers` | 列出站点下的服务器设备及在线/检查状态 | `siteid` (必填, int) |
| `nable_rmm_get_workstations` | 列出站点下的工作站设备及在线/检查状态 | `siteid` (必填, int) |
| `nable_rmm_get_agentless_assets` | 列出站点下的无代理(扫描发现)资产(N-able 已标记该功能为 deprecated) | `siteid` (必填, int) |
| `nable_rmm_get_device_monitoring_details` | 获取单个设备的详细监控信息 | `deviceid` (必填, int) |

### Checks, Patch & Performance

| Tool | 功能 | 参数 |
|---|---|---|
| `nable_rmm_get_failing_checks` | 列出当前失败的检查项 | `clientid?`, `check_type?`("checks"/"tasks"/"random") |
| `nable_rmm_get_checks` | 列出某设备上配置的所有检查项 | `deviceid` (必填, int) |
| `nable_rmm_get_check_config` | 获取单个检查项的详细配置(结构因检查类型/OS而异) | `checkid` (必填, int) |
| `nable_rmm_get_outages` | 列出设备的 outage 记录(开放中或近61天内关闭) | `deviceid` (必填, int) |
| `nable_rmm_get_drive_space_history` | 磁盘空间检查历史(基于 list_checks 按 check_type 1003/1004 过滤,N-sight 无独立服务) | `deviceid` (必填, int) |
| `nable_rmm_get_patch_list` | 列出设备上的所有补丁及状态/严重程度 | `deviceid` (必填, int) |
| `nable_rmm_get_performance_history` | 设备历史性能指标(带宽/磁盘/CPU/内存/网卡) | `deviceid` (必填, int), `interval` (必填, int, 只能是 15 或 60), `since?` |

## 测试示例 (Test Example)

List all servers at a site:

```json
{
  "method": "tools/call",
  "params": {
    "name": "nable_rmm_get_servers",
    "arguments": { "siteid": 12345 }
  }
}
```

Equivalent `curl` against the running server (streamable HTTP MCP endpoint):

```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "X-Nable-Api-Token: <api_key>" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "nable_rmm_get_servers",
      "arguments": { "siteid": 12345 }
    }
  }'
```

Expected shape of a successful result (the underlying XML response, converted to JSON; fields abbreviated):

```json
{
  "content": [
    {
      "type": "text",
      "text": "{\n  \"created\": \"2026-03-15T10:00:00+00:00\",\n  \"host\": \"...\",\n  \"status\": \"OK\",\n  \"items\": {\n    \"server\": [ { \"serverid\": \"9001\", \"name\": \"DC01\", \"online\": \"1\", \"status_247\": \"5\", \"os\": \"Windows Server 2022\" } ]\n  }\n}"
    }
  ]
}
```

## API Reference

- [N-sight API — Getting Started](https://developer.n-able.com/n-sight/docs/getting-started-with-the-n-sight-api)
- [Generate an API Key](https://developer.n-able.com/n-sight/docs/generate-an-api-key)
- [Determine the server for your API query](https://developer.n-able.com/n-sight/docs/determine-server-for-api-query)

## Verified Against a Live Account

All 14 read tools have been exercised end-to-end against a real N-able RMM account (US region) and returned real data, including edge cases N-able's public docs left ambiguous:
- `nable_rmm_get_performance_history`'s `interval` parameter is **required** (not optional as the docs example implied) and only accepts `15` or `60` — confirmed via the API's own validation error (`Invalid "interval": must be 15 or 60 (minutes)`).
- `nable_rmm_get_agentless_assets` returns empty `items` on this account, consistent with N-able's note that the feature is deprecated.

The two write tools (`nable_rmm_create_client`, `nable_rmm_create_site`) were **not** exercised against the live account to avoid creating real data in a production customer's N-able RMM tenant — verify these against a disposable test account before relying on them.

## Known Gaps / Not Implemented

- `get_site_installation_package` — returns a binary installer download rather than structured data, not practical as an MCP tool.
