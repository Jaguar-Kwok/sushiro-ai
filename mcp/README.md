# sushiro-mcp

MCP server exposing the Sushiro Hong Kong SushiPass queue API
(`https://sushipass.sushiro.com.hk/api/2.0`) as tools, built on the official
MCP Python SDK v2.

The upstream API is a free public official endpoint with no authentication.
To keep the impact on it minimal, this server throttles itself to **at most
one upstream request per second** (see [Rate limiting](#rate-limiting)).

> **Unofficial notice:** independent educational/research project, not
> affiliated with or endorsed by Sushiro Hong Kong. See the repo root
> [NOTICE.md](../NOTICE.md) and [DISCLAIMER.md](../DISCLAIMER.md).

## Tools

| Tool | Description |
| ---- | ----------- |
| `list_stores` | List up to 100 Sushiro HK stores near a point, closest first, with opening status, ticket-issuing status and current wait |
| `get_store_queue` | Get the current ticket queue for one store (`storeQueue` = upcoming ticket numbers, first element served next) |

`list_stores` returns a trimmed projection per store: `id`, `name`, `name_en`,
`store_status` (`OPEN` or closed), `net_ticket_status` (`OFFLINE_MANUAL` =
issuing tickets, `OFFLINE_CLOSING`/`OFFLINE_CLOSED` = stopped issuing),
`wait` (groups waiting), `address`, `area`, `latitude`, `longitude`.

## Run locally

    uv sync
    uv run sushiro-mcp                    # HTTP: serves MCP on http://127.0.0.1:8000/mcp
    uv run sushiro-mcp --transport stdio  # stdio: for Claude Desktop, opencode, etc.

No credentials are needed — the upstream API is unauthenticated. The
`/health` probe route exists only on the HTTP transport.

Example stdio client config (Claude Desktop, opencode, etc.):

    {
      "mcpServers": {
        "sushiro": {
          "command": "uv",
          "args": ["--directory", "/path/to/sushiro-ai/mcp", "run", "sushiro-mcp", "--transport", "stdio"]
        }
      }
    }

Inspect with the MCP Inspector (needs Node.js on PATH):

    uv run mcp dev src/sushiro_mcp/server.py

## Docker

    docker build -t sushiro-mcp .
    docker run --rm -p 8000:8000 sushiro-mcp

## Rate limiting

Every upstream request is serialized and spaced at least 1 second apart
(`SUSHIRO_MIN_INTERVAL_SEC`, clamped to a minimum of 1.0 so it can only be
increased, never lowered). Consequences:

- Concurrent tool calls queue behind each other; polling queues for many
  stores takes roughly one second per store. That is intentional.
- Tests and scripts in this repo must not call the upstream API in loops —
  use recorded fixtures or mocks (see `AGENTS.md`).

## CI

`.github/workflows/docker-publish.yml` builds the image and pushes it to
`ghcr.io/<owner>/sushiro-mcp` on every push to `main` and every `v*` tag.
The first run creates the GHCR package (private by default — adjust visibility
in the repo's package settings). `GITHUB_TOKEN` needs no configuration.

## Configuration

| Env var | Default | Purpose |
| ------- | ------- | ------- |
| `SUSHIRO_BASE_URL` | `https://sushipass.sushiro.com.hk/api/2.0` | Upstream API base URL |
| `SUSHIRO_MIN_INTERVAL_SEC` | `1.0` | Minimum seconds between upstream requests (clamped to ≥ 1.0) |
| `MCP_TRANSPORT` | `http` | Transport: `http` (streamable HTTP) or `stdio` — the `--transport` flag overrides |
| `MCP_HOST` | `127.0.0.1` | Bind address (`0.0.0.0` in Docker) |
| `MCP_PORT` | `8000` | Listen port |
| `MCP_ALLOWED_HOSTS` | — | Comma-separated Host allowlist for production hostnames |
| `MCP_ALLOWED_ORIGINS` | — | Comma-separated Origin allowlist (browser clients) |

### Deploying behind a real hostname

The server rejects requests whose `Host` header is not localhost unless
`MCP_ALLOWED_HOSTS` is set. Behind a real hostname set at minimum:

    -e MCP_ALLOWED_HOSTS=mcp.example.com,mcp.example.com:*

Without it every request fails with `421 Misdirected Request` before any tool
logic runs.

## 香港中文摘要

`sushiro-mcp` 是一個以官方 MCP Python SDK v2 打造的 MCP 伺服器，將壽司郎香港
SushiPass 排隊 API（`https://sushipass.sushiro.com.hk/api/2.0`）包裝成兩個
工具：

- `list_stores` — 列出某位置附近最多 100 間分店（由近至遠），含營業狀態、
  派籌狀態（`net_ticket_status`：`OFFLINE_MANUAL` = 正在派籌；
  `OFFLINE_CLOSING`／`OFFLINE_CLOSED` = 已停止派籌）及等候組數（`wait`）
- `get_store_queue` — 查詢一間分店的即時取籌排隊：`storeQueue` 為即將叫號的
  籌號清單（第一個元素 = 下一個叫號），`boothQueue`／`counterQueue` 及訂座
  （reservation）變體把同一條隊按籌的種類分拆；空陣列 = 無人等候

上游 API 免費、公開、無需金鑰。為減輕其負擔，伺服器自我節流：**每秒最多一個
上游請求**（`SUSHIRO_MIN_INTERVAL_SEC`，下限鎖定為 1.0），並逐一序列化。並發
的工具呼叫會排隊處理，逐一輪詢多間分店大約每間需時一秒——這是刻意設計。

本機執行：

    uv sync
    uv run sushiro-mcp                    # HTTP：MCP 服務於 http://127.0.0.1:8000/mcp
    uv run sushiro-mcp --transport stdio  # stdio：Claude Desktop、opencode 等

stdio 客戶端設定範例（Claude Desktop、opencode 等）：

    {
      "mcpServers": {
        "sushiro": {
          "command": "uv",
          "args": ["--directory", "/path/to/sushiro-ai/mcp", "run", "sushiro-mcp", "--transport", "stdio"]
        }
      }
    }

Docker：

    docker build -t sushiro-mcp .
    docker run --rm -p 8000:8000 sushiro-mcp

環境變數（`SUSHIRO_BASE_URL`、`MCP_TRANSPORT`、`MCP_HOST`、`MCP_PORT`、
`MCP_ALLOWED_HOSTS`、`MCP_ALLOWED_ORIGINS` 等）的完整說明、部署到真實
hostname 時的 allowlist 設定，以及 CI 自動建置的 GHCR 映像（首次發佈後預設為
private，請在手動改為 public），請參閱上方英文版的
[Configuration](#configuration) 及 [CI](#ci) 一節。

本專案屬非官方教育及研究用途，與壽司郎香港或 SushiPass API 營運者並無任何
隸屬或認可關係；詳見 repo 根目錄的 [NOTICE.md](../NOTICE.md) 及
[DISCLAIMER.md](../DISCLAIMER.md)。
