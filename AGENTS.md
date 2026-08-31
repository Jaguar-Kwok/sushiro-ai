# Agent guidelines

The upstream API (`https://sushipass.sushiro.com.hk/api/2.0`) is Sushiro Hong
Kong's **free public official endpoint**. It is not a paid or rate-limited-for-us
service, so every call this repo makes is a cost we impose on someone else's
production system. Treat it as fragile and be conservative with it.

**Scope:** these rules cover the whole repository — the `mcp/` server, the
chatbot prompt embedded in the root `README.md`, and the `skill/` agent skill
alike.

## Hard rules

- **Never remove, weaken, or bypass the rate limiter** in `_request` in
  `mcp/src/sushiro_mcp/server.py`. `SUSHIRO_MIN_INTERVAL_SEC` is clamped to
  >= 1.0 on purpose — keep the clamp. There must never be more than one
  in-flight upstream request.
- **Never add tools or code paths that fan out** to many upstream calls per
  invocation (N+1 patterns, per-store polling loops, "refresh all queues"
  helpers). The tool surface is intentionally two single-request tools.
- **Tests and scripts must not hit the real API in loops.** Use recorded
  JSON fixtures or mock `httpx` responses. A one-off single-request smoke
  test is acceptable; anything iterative is not.
- **During debugging, at most a single one-off curl** with a small
  `numresults` value. No polling loops, no watch scripts, no repeated
  invocations to "see if it changed".
- **Do not write examples, docs, or prompts that encourage frequent
  polling** of the API (e.g. "call every second"). If documenting polling
  behavior, recommend intervals of at least 30–60 seconds.

## Notes

- The server-side throttling protects the API even if a client misbehaves,
  but it is a backstop, not a licence: an agent that generates queued
  requests still occupies the server for the duration.
- The Vue app this API was learned from is unrelated to this repo; do not
  import or reference it here.
