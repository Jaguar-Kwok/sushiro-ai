---
name: sushiro-scraper
description: Fetch live Sushiro Hong Kong store lists and SushiPass ticket queues (which stores are open and issuing tickets, how many groups are waiting, which ticket number is being served next) directly from the official public SushiPass API, using a multi-layer fallback ladder (direct GET → throwaway script → curl+jq → webfetch/websearch) so results survive blocked or moved endpoints. Use this skill whenever the user asks about Sushiro HK stores or queues, wants to know the wait at a branch, mentions SushiPass or a store id, or says things like "list Sushiro stores near me", "which Sushiro is still issuing tickets", "what's the queue at store 1016" — or in Chinese, "壽司郎排隊", "壽司郎邊間仲派籌", "而家叫到幾多號", "等幾多組", "附近有冇壽司郎開緊", "取籌情況" — even casually. Generated from the sushiro-ai/mcp MCP server (tools list_stores, get_store_queue); no MCP hosting required.
---

# Sushiro HK Scraper

Generated from `sushiro-ai/mcp` (`mcp/src/sushiro_mcp/server.py`, Python MCP SDK v2)
on 2026-08-31. Original MCP tools: `list_stores`, `get_store_queue`. All fetching is
done by you, the agent, through the per-tool recipes below — no server to connect to.

**Unofficial notice:** this skill comes from an independent educational/research
project, not affiliated with or endorsed by Sushiro Hong Kong (壽司郎). "Sushiro"
and "SushiPass" are trademarks of their respective owners, used only to identify
the service. The API data belongs to its owner; the licence covers the code and
docs only. The polite-use limits below are part of the deal — keep them (no
unauthorized access, no abuse, no excessive traffic, no circumvention of security
controls). Full notices: NOTICE.md / DISCLAIMER.md at the source repo root.

**Upstream:** `https://sushipass.sushiro.com.hk/api/2.0` — Sushiro Hong Kong's free
public official SushiPass endpoint. No auth, no key, no login. It is a real
production ticketing system: every call costs someone else's infrastructure, so
follow the Politeness rules without exception.

**Verified reachable:** 2026-08-31, single `curl -sI` probe on the storelist
endpoint returned HTTP 200 with `content-type: application/json`.

## Quick reference

| Data (was MCP tool) | Public? | Preferred layer | Fallback order |
|---|---|---|---|
| `list_stores` — stores near a point, closest first, with ticket-issuing status and wait | yes | L0 (direct GET) | L1 → L2 → L4 → L5 |
| `get_store_queue` — one store's live ticket queue (`storeQueue[0]` = next ticket served) | yes | L0 (direct GET) | L1 → L2 → L4 → L5 |

Both tools hit the same host and API, so they share one ladder and one politeness budget.

## list_stores — List Sushiro Hong Kong stores near a point, closest first

Always queries up to 100 stores. Each store includes: `id` (needed for
`get_store_queue`), `name`, `name_en`, `store_status` (`OPEN` or a closed
status), `net_ticket_status` (`OFFLINE_MANUAL` = issuing tickets,
`OFFLINE_CLOSING`/`OFFLINE_CLOSED` = stopped issuing tickets), `wait` (number
of groups currently waiting), `address`, `area`, `latitude`, `longitude`.

**Inputs:** `latitude: float = 22.0` (centre latitude; default is the middle of
Hong Kong), `longitude: float = 114.0`, `region: str = "HK"`. All optional —
use the defaults when the user does not specify; ask only if the user's
location needs geocoding and you cannot infer it.

**Recipe (preferred, L0):**

```
GET https://sushipass.sushiro.com.hk/api/2.0/info/storelist?latitude={latitude}&longitude={longitude}&numresults=100&region={region}
Headers: Accept: application/json
User-Agent: sushiro-scraper/1.0 (personal research)
```

One plain GET, no pagination, no POST. Always send `numresults=100`.
Quick probe variant: `curl -sI -A "sushiro-scraper/1.0" "<url>"` — headers only.

**Fallbacks for this source:**

- L1 — throwaway stdlib Python script (`urllib.request` + `json`): same URL,
  headers, 30s timeout, up to 3 attempts with backoff (2s/4s/8s) on 429/5xx.
  Use when curl is unavailable or you need retry/shaping logic.
- L2 — `curl -sS --max-time 30` piped through `jq` (check `command -v jq`; else
  `python3 -m json.tool`).
- L4 — `webfetch` the recipe URL directly (plain GET JSON, should work; if your
  fetcher summarizes or mangles the JSON, say so and drop down); `websearch` to
  relocate the endpoint on 404/DNS failure.
- L5 — precise report of what failed and what is missing.

**Parsing:** response is a JSON array of store objects, closest first, up to
100. From each element keep exactly these fields:

| Output field | Source key |
|---|---|
| `id` | `id` |
| `name` | `name` |
| `name_en` | `nameEn` |
| `store_status` | `storeStatus` |
| `net_ticket_status` | `netTicketStatus` |
| `wait` | `wait` |
| `address` | `address` |
| `area` | `area` |
| `latitude` | `latitude` |
| `longitude` | `longitude` |

`net_ticket_status` meanings: `OFFLINE_MANUAL` = issuing tickets;
`OFFLINE_CLOSING` / `OFFLINE_CLOSED` = stopped issuing tickets.

**Return format:** reply in human-readable prose and a table, not raw JSON —
a one-line summary (stores found, how many still issuing tickets) plus a
markdown table of the closest stores, closest first: Store (name + name_en),
Area, Status in words (`OPEN` → open), Tickets in words (`OFFLINE_MANUAL` →
issuing tickets; `OFFLINE_CLOSING`/`OFFLINE_CLOSED` → stopped), Waiting
(groups). More than 15 stores → show the closest 10–15, say how many more
there are, and offer the rest. Raw JSON — the exact 10-field array above —
only when the user explicitly asks for JSON/machine-readable output.

Formatting: write labels as plain text (e.g. 最快選擇：) — never use markdown
emphasis (`**bold**`); many chat surfaces print the asterisks literally
instead of rendering bold.

**Known errors:** upstream failures arrive as
`{"error": "API returned <HTTP status>", "detail": "<first 500 chars of body>"}`
or `{"error": "API request failed: <message>"}` — surface them instead of
hiding them. Empty body or HTTP 204 means `{"status": "ok"}` (no data). The
upstream timeout is 30 seconds.

## get_store_queue — Get the current ticket queue for one store

Returns the API's queue payload. `storeQueue` is the list of upcoming ticket
numbers (the first element is the ticket being served next); `boothQueue`/
`counterQueue` and the reservation variants split it by ticket type. Empty
arrays mean nobody is waiting.

**Inputs:** `store_id: int` (REQUIRED — a numeric id from `list_stores`),
`region: str = "HK"`. If `store_id` is missing, ask the user for it — never
guess a value silently.

**Recipe (preferred, L0):**

```
GET https://sushipass.sushiro.com.hk/api/2.0/remote/groupqueues?region={region}&storeid={store_id}
Headers: Accept: application/json
User-Agent: sushiro-scraper/1.0 (personal research)
```

One call per store id. Never loop over many stores in one turn; if the user
names several stores, make the calls one at a time and pause 2 seconds between
them (see Politeness).

**Fallbacks for this source:** same ladder as `list_stores` — L1 stdlib script
(with backoff on 429/5xx), L2 curl+jq, L4 webfetch/websearch, L5 report.

**Parsing:** return the payload as-is:
- `storeQueue`: upcoming ticket numbers — FIRST element = ticket served next
- `boothQueue` / `counterQueue` and reservation variants: same queue by ticket type
- empty arrays = nobody waiting

**Return format:** reply as a short human-readable summary, not raw JSON:
store name + id, the ticket being served next (`storeQueue[0]`), the next few
numbers behind it, and the queue split by type (booth / counter / reservation)
with counts; empty arrays → say nobody is waiting. Paste the raw JSON payload
(all fields kept) only when the user explicitly asks for JSON/machine-readable
output.

Formatting: write labels as plain text (e.g. 下一個叫號：) — never use markdown
emphasis (`**bold**`); many chat surfaces print the asterisks literally
instead of rendering bold.

**Known errors:** same error wrapping as `list_stores`; empty body or 204 →
`{"status": "ok"}`.

## Ladder rules

Try the preferred layer first; escalate only on a matching failure class;
first success wins, then stop climbing. Track internally which layer served
the data; mention it only when a fallback rescued the request or the user
asks.

- **L0 (direct GET):** the exact recipes above. Cheapest and most precise.
- **L1 (throwaway script):** stdlib Python only (`urllib`, `json`, `time`) —
  no pip installs. Write it to a temp/session path (e.g. `/tmp`), print JSON to
  stdout, delete after the session unless the user wants it kept. Retry up to
  3× with backoff on 429/5xx only.
- **L2 (curl+jq):** single GETs and simple field selection; keep raw responses
  with `curl -sS -o /tmp/sushiro.json "<url>"` for reuse in the session.
- **L4 (provider tools):** `webfetch` for the endpoint URLs (GET only, may
  summarize — prefer L0–L2 output for structured data); `websearch` when the
  endpoint 404s, the domain dies, or the API moved — then loop back and adopt
  the new endpoint as the preferred recipe.
- **L5 (degradation):** deliver a cached earlier result (state its age) or a
  precise failure report — layers tried, exact errors, what is missing. Never
  silently omit a failure.

Escalation triggers:

- **403/418 + challenge page** → adjust UA/headers once, then L4 webfetch.
- **429** → honor `Retry-After` or back off once; still limited → cache + L4.
- **404 / DNS failure / connection refused** → L4 `websearch` for the new
  endpoint location; if found, adopt it (see Self-healing); if none → L5.
- **401** → this API needs no key, so a 401 means the endpoint changed: L4
  websearch, don't ask the user for a key.
- **301/302 → login page** → stop and say so; the data is not public.
- **HTML where JSON expected** → wrong URL or headers; fix, then L4 if still wrong.
- One diagnosis before one retry: read the actual error/headers (`curl -sI`)
  before changing anything. Blind retries are how rate limits happen.

## Politeness

The upstream is a real production ticketing system run by Sushiro Hong Kong.
The MCP server this came from throttled itself to at most one upstream request
per second, serialized — preserve that behavior:

- At least 1–2 seconds between any two calls to `sushipass.sushiro.com.hk`;
  there must never be more than one in-flight request.
- One store per queue call; never batch-loop over the whole store list (no
  "refresh all queues", no N+1 fan-out).
- Reuse results already fetched this session (cache in `/tmp` or the session
  dir) instead of refetching the same URL.
- If the user wants live monitoring (排隊監察), re-check no more often than
  once every 30–60 seconds, and only for the stores they actually care about.
- Public data only; a login wall means stop, not bypass.
- Cap total calls per session; there is no batch endpoint, so the cap IS the
  batching.

## Self-healing

If a recipe fails and a fallback rescues it (you used a different URL, header,
or layer), edit this SKILL.md immediately so the working recipe becomes the
preferred one — the next invocation should start where the ladder should have
started. Note what changed and when in the recipe line.
