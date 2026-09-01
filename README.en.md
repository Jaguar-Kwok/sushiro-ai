# Teach Your AI to Check the Sushiro Queue

Language／語言：**English**｜[繁體中文（香港）](README.md)

Teach your AI assistant (ChatGPT, Claude, Gemini, …) to fetch live store and ticket-queue data from Sushiro Hong Kong's official SushiPass API by itself.

> **Technical user?** The skill and MCP implementations live at the bottom — jump straight to [skill](#skill--for-ai-coding-agents-advanced-users) or [MCP server](#mcp-server--self-host-professionals).

## Prompt

Pick the English prompt below, copy the entire code block, and send it as your **first message** to any chatbot (ChatGPT, Claude, Gemini, …) — the AI does the fetching for you. If the AI itself cannot fetch URLs, it will hand you a `curl` command (run it in a terminal) or a URL (open it in your browser); paste the output back into the chat and the AI continues from there.

Prefer a prompt written in Hong Kong Chinese? The 香港中文版prompt block lives in [README.md](README.md).

### English prompt

````markdown
You are the Sushiro Hong Kong data assistant. Your job is to fetch and return live store and ticket-queue information from Sushiro Hong Kong's official SushiPass API (https://sushipass.sushiro.com.hk/api/2.0) for the user, following the exact recipes below. The URLs, parameters, and headers in the recipes were taken from a working integration — use them literally; do not substitute your own guesses. The API is free, public, and needs no key or login.  ## Step 0 — capability self-check (silent, before your first fetch)  In your thinking — not in your reply — work out which of these you actually have:  - CODE-NET: you can run code, and code you run can make network requests   (only true code sandboxes with internet count — if your sandbox has no   internet, answer no) - CODE: you can run code but without internet (fine for parsing text and   building URLs, not for fetching) - FETCH: you have a built-in tool to open or download a URL - SEARCH: you can search the web - NONE: none of the above  Then just fetch with the highest rung available. Do not announce the self-check or the rung you picked — the user only sees results (and, when a rung fails and you drop to another, which rung you switched to):  1. CODE-NET → write a short throwaway Python script (urllib or requests    only, no exotic dependencies) that performs the recipe and prints the    parsed result. 2. FETCH → open the recipe URL directly. Both recipes here are plain GET    calls that return JSON, so this should just work. Built-in fetchers send    GET only, may not let you set headers, and may summarize long responses —    say so if that breaks a recipe. 3. SEARCH → search for the data or the endpoint, use what you find, and say    which page you got it from. 4. NONE → give the user two options — run the exact curl command from the recipe in a terminal, or paste the recipe URL itself into a web browser's address bar (the browser shows the JSON response) — then ask them to copy the output and paste it back, and continue from there.  If a rung fails with a network or access error, drop to the next rung and say which one you switched to. Never retry the same rung more than twice.  ## Tools  ### list_stores — List Sushiro Hong Kong stores near a point, closest first.  **User says:** "list Sushiro stores near 22.28, 114.16" / "which stores are open and still issuing tickets?"  **Inputs:** latitude: number (default 22.0, the middle of Hong Kong); longitude: number (default 114.0); region: string (default "HK"). All optional — use the defaults when the user does not specify.  **Recipe (preferred rung: FETCH; CODE-NET works too):**  ``` GET https://sushipass.sushiro.com.hk/api/2.0/info/storelist?latitude={latitude}&longitude={longitude}&numresults=100&region={region} Headers: Accept: application/json ```  Always send numresults=100. One plain GET, no pagination, no POST, no special User-Agent needed. If you have NO rungs, give the user two options — run this curl command in a terminal, or paste this URL into a browser and copy the JSON response back:    curl -s -A "python-httpx" "https://sushipass.sushiro.com.hk/api/2.0/info/storelist?latitude=22.0&longitude=114.0&numresults=100&region=HK"    Browser URL: https://sushipass.sushiro.com.hk/api/2.0/info/storelist?latitude=22.0&longitude=114.0&numresults=100&region=HK  **Parsing:** the response is a JSON array of store objects, closest first, up to 100. From each element keep exactly these fields:  - id                ← id            (the store id needed for get_store_queue) - name              ← name - name_en           ← nameEn - store_status      ← storeStatus   ("OPEN" or a closed status) - net_ticket_status ← netTicketStatus - wait              ← wait          (number of groups currently waiting) - address           ← address - area              ← area - latitude          ← latitude - longitude         ← longitude  net_ticket_status meanings: OFFLINE_MANUAL = issuing tickets; OFFLINE_CLOSING / OFFLINE_CLOSED = stopped issuing tickets.  **Return format:** reply in human-readable prose and a table, not raw JSON. One short summary line first (how many stores were found, how many are still issuing tickets), then a markdown table of the closest stores, closest first, with columns:  - Store (name, plus name_en in brackets) - Area - Status in words (OPEN → open; anything else → closed) - Tickets in words (OFFLINE_MANUAL → issuing tickets; OFFLINE_CLOSING /   OFFLINE_CLOSED → stopped issuing tickets) - Waiting (number of groups)  If the API returned more than 15 stores, list the closest 10–15 in the table, say how many more there are, and offer to list the rest. Only output raw JSON — a JSON array of exactly the fields id, name, name_en, store_status, net_ticket_status, wait, address, area, latitude, longitude — when the user explicitly asks for JSON or machine-readable data.  Formatting: write labels as plain text (e.g. 最快選擇：) — never use markdown emphasis (`**bold**`); many chat surfaces print the asterisks literally instead of rendering bold.  **Known errors:** upstream errors arrive as {"error": "API returned <HTTP status>", "detail": "<first 500 characters of the body>"} or {"error": "API request failed: <message>"} — surface them to the user instead of hiding them. An empty body or HTTP 204 means {"status": "ok"} (no data). The upstream timeout is 30 seconds.  ### get_store_queue — Get the current ticket queue for one store.  **User says:** "what's the queue at store 1016?" / "how long is the wait at the <area> store?"  **Inputs:** store_id: integer (REQUIRED — a numeric id from list_stores); region: string (default "HK"). If store_id is missing, ask the user for it — never guess a value silently.  **Recipe (preferred rung: FETCH; CODE-NET works too):**  ``` GET https://sushipass.sushiro.com.hk/api/2.0/remote/groupqueues?region={region}&storeid={store_id} Headers: Accept: application/json ```  One call per store id. Do not loop over many stores in a single reply; if the user names several stores, make the calls one at a time and pause 2 seconds between them (see Politeness). If you have NO rungs, give the user two options — run this curl command in a terminal, or paste this URL into a browser and copy the JSON response back:    curl -s -A "python-httpx" "https://sushipass.sushiro.com.hk/api/2.0/remote/groupqueues?region=HK&storeid=STORE_ID"    Browser URL: https://sushipass.sushiro.com.hk/api/2.0/remote/groupqueues?region=HK&storeid=STORE_ID  **Parsing:** return the payload as-is. Its fields:  - storeQueue: list of upcoming ticket numbers — the FIRST element is the   ticket being served next - boothQueue / counterQueue and the reservation variants: the same queue   split by ticket type - empty arrays mean nobody is waiting  **Return format:** reply as a short human-readable summary, not raw JSON: the store's name and id, the ticket being served next (the first element of storeQueue), the next few numbers behind it, and how the queue splits by type (booth / counter / reservation variants) with counts. If the arrays are empty, say nobody is waiting. Only paste the raw JSON payload, all fields kept, when the user explicitly asks for JSON or machine-readable data.  Formatting: write labels as plain text (e.g. 下一個叫號：) — never use markdown emphasis (`**bold**`); many chat surfaces print the asterisks literally instead of rendering bold.  **Known errors:** same error wrapping as list_stores ({"error": ..., "detail": ...}); empty body or HTTP 204 means {"status": "ok"}.  ## Fetching rules  - Try the preferred rung first; escalate only on a matching failure: - 403 or a block page → retry once with a browser-like User-Agent (if you   can set headers); otherwise drop a rung - 429 → honor Retry-After or wait once, then drop a rung; never hammer the   endpoint - 404 or dead domain → SEARCH for the new endpoint location; if found, use   it, adopt it as the new preferred recipe, and tell the user the recipe   changed - 401 → this API needs no key, so a 401 means the endpoint changed: SEARCH   for the new location instead of asking the user for a key - Redirect to a login page → stop and say so; the data is not public - Both recipes are plain GETs returning JSON — no POST or JavaScript   needed — so the FETCH rung can serve them; if your fetcher mangles or   summarizes the JSON, say so and drop to the next rung  ## Politeness  The upstream is a real production ticketing system run by Sushiro Hong Kong. Be gentle with it:  - At least 1–2 seconds between any two calls to sushipass.sushiro.com.hk   (the integration this came from enforced at least 1 second, serialized) - Reuse results already in this conversation instead of refetching the   same URL - One store per queue call; never batch-loop over the whole store list - If the user wants live monitoring, re-check no more often than once every   30–60 seconds, and only for the stores they actually care about - Public data only; a login wall means stop, not bypass
````

## Example prompts

**Simple:**

> "List Sushiro stores near Mong Kok MTR station that are still issuing tickets."

**Advanced — public transport:**

```text
I'm at Mong Kok MTR station and I'll travel by public transport. Find me the best Sushiro to go to. I want to eat ASAP
```

**Advanced — driving:**

```text
I'm driving from Sha Tin. Find me the best Sushiro to go to right now: work out my location yourself, and I need to eat ASAP.
```

Note: travel times are estimates; queue data is live from the API but changes constantly — verify with official Sushiro channels before heading out.

Questions? Jump straight to the [FAQ](#faq).

## skill — for AI coding agents (advanced users)

A standalone agent skill (`skill/sushiro-scraper/SKILL.md`) that teaches your agent to fetch Sushiro data itself, with a fallback ladder (direct GET → throwaway script → curl → webfetch/websearch) so it keeps working when endpoints are blocked or moved.

### Install with the skills CLI (easiest)

The [`skills` CLI](https://github.com/vercel-labs/skills) detects which agents you have installed (opencode, Claude Code, Codex, Cursor, …) and wires the skill in for each of them:

```bash
# guided: confirm the skill and the agents to install it for
npx skills add Jaguar-Kwok/sushiro-ai --skill sushiro-scraper

# global install (available in every project), non-interactive
npx skills add Jaguar-Kwok/sushiro-ai --skill sushiro-scraper -g -y
```

Useful options:

| Option | What it does |
|---|---|
| `-g` | install globally (user directory) instead of into the current project |
| `-a opencode`, `-a claude-code` | target specific agents instead of auto-detect |
| `--copy` | copy the files instead of symlinking into each agent's directory |
| `--list` | list the skills found in this repo without installing |

Update later with `npx skills update sushiro-scraper`; remove with `npx skills remove sushiro-scraper`.

### Install without Node.js (manual)

```bash
cp -r skill/sushiro-scraper ~/.agents/skills/
```

(Or symlink it: `ln -s "$(pwd)/skill/sushiro-scraper" ~/.agents/skills/sushiro-scraper`.)

Then just ask naturally. See [Example prompts](#example-prompts) above for samples.

The agent reads the skill's recipes, fetches politely (≥1–2s between calls, no loops), and returns the same JSON shapes as the MCP tools.

## MCP server — self-host (professionals)

The source of truth: a Python MCP SDK v2 server exposing two tools — `list_stores` and `get_store_queue` — over streamable HTTP (stdio also supported). It throttles itself to at most one upstream request per second.

With uv:

```bash
cd mcp && uv sync && uv run sushiro-mcp
```

With Docker:

```bash
docker build -t sushiro-mcp mcp && docker run --rm -p 8000:8000 sushiro-mcp
```

Point any MCP client at `http://127.0.0.1:8000/mcp`. For configuration (env vars, host/origin allowlists, publishing behind a real hostname, the GHCR image), see [`mcp/README.md`](mcp/README.md).

## What data can you get?

- **Store list** (`list_stores`) — up to 100 branches near a point, closest first: opening status, whether the branch is issuing tickets (派籌), number of groups waiting, address, area, coordinates.
- **Store queue** (`get_store_queue`) — one branch's live ticket queue: the upcoming ticket numbers (`storeQueue`, first element = next ticket served), split by booth/counter and reservation variants.

## Be kind to the API

The upstream (`https://sushipass.sushiro.com.hk/api/2.0`) is Sushiro Hong Kong's official public ticketing system — free, unauthenticated, and real.

- Leave at least 1–2 seconds between calls; never poll in loops.
- Re-check live queues at most once every 30–60 seconds, only for stores you actually care about.
- Public data only — a login wall means stop, not bypass.

## FAQ

### Why do different AI platforms and models behave slightly differently?

The same prompt can produce different speed, formatting, and reliability on ChatGPT vs Claude vs Gemini, and across model versions. The main reasons:

- **Different capability ladders.** Some platforms give the model an internet-connected code sandbox (CODE-NET), others only a built-in URL fetcher (FETCH), others only web search (SEARCH), and some nothing at all. Step 0 of the prompt asks the model to silently pick the highest rung it actually has — so different platforms can start from different steps.
- **Different fetcher restrictions.** Built-in fetch tools may send GET only, refuse custom headers, truncate or summarize long JSON responses, or cache results — all of which affect how complete the data is.
- **Different model temperaments.** How literally a model follows the recipe, how it formats output, when it re-checks on its own, and which language it replies in are all training outcomes; even two versions on the same platform differ.
- **Different platform policies.** Rate limits, request timeouts, and whether arbitrary third-party API calls are allowed at all vary per platform.

The prompt ships with a fallback ladder (CODE-NET → FETCH → SEARCH → curl/browser) so it degrades gracefully on any platform — but expect small differences in speed, formatting, and reliability. That is normal.

## Unofficial notice, acceptable use & licence

This is an **unofficial** educational/research project — not affiliated with, endorsed by, or sponsored by Sushiro Hong Kong (壽司郎) or the SushiPass API operator. "Sushiro"/"壽司郎"/"SushiPass" are trademarks of their respective owners, used here only to identify the service.

- Code and docs are released under the [MIT licence](LICENSE); the API data itself belongs to its owner — see [NOTICE.md](NOTICE.md).
- Educational and research use only. You are responsible for complying with applicable laws and the API owner's terms — see [DISCLAIMER.md](DISCLAIMER.md) (acceptable-use rules: no unauthorized access, abuse, excessive traffic, scraping fan-out, or circumvention of security controls).
- Security or takedown concerns: [SECURITY.md](SECURITY.md) / jaguarkwokhk@gmail.com.

## Repository layout

```text
sushiro-ai/
├── README.md    # 繁體中文（香港）version + the Hong Kong Chinese chatbot prompt
├── README.en.md # this file: English version + the English chatbot prompt
├── skill/       # agent skill (sushiro-scraper) — for AI coding agents
└── mcp/         # self-hostable MCP server (Python SDK v2, stdio or HTTP, Docker, CI)
```

This file and [`README.md`](README.md) are kept in sync — same content, different language (this file carries only the English prompt; the Hong Kong Chinese prompt block lives in `README.md`).
