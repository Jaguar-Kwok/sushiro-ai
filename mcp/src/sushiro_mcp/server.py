"""MCP server exposing the Sushiro Hong Kong SushiPass queue API as tools.

The upstream API (https://sushipass.sushiro.com.hk/api/2.0) is a free public
official endpoint with no authentication. To keep the impact on it minimal,
every upstream request is throttled to at most one call per second
(SUSHIRO_MIN_INTERVAL_SEC, clamped to >= 1.0) and requests are serialized.

Serves MCP over streamable HTTP by default (http://127.0.0.1:8000/mcp); run
with --transport stdio to serve over standard input/output instead.
"""

import argparse
import asyncio
import json
import os
import time
from typing import Annotated, Any

import httpx
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

# --- Configuration (all overridable via environment) ------------------------

API_BASE_URL = os.environ.get("SUSHIRO_BASE_URL", "https://sushipass.sushiro.com.hk/api/2.0")

MCP_NAME = "sushiro"
MCP_HOST = os.environ.get("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.environ.get("MCP_PORT", "8000"))


def _min_interval() -> float:
    """Minimum seconds between upstream requests. Clamped to >= 1.0 so the
    env var can only protect the official API further, never hammer it."""
    raw = os.environ.get("SUSHIRO_MIN_INTERVAL_SEC", "1.0")
    try:
        return max(float(raw), 1.0)
    except ValueError:
        return 1.0


_REQUEST_INTERVAL = _min_interval()
_RATE_LOCK = asyncio.Lock()
_LAST_REQUEST_AT = -_REQUEST_INTERVAL


def _transport_security() -> TransportSecuritySettings | None:
    """Build TransportSecuritySettings from MCP_ALLOWED_HOSTS / MCP_ALLOWED_ORIGINS.

    Unset -> None -> the SDK's safe localhost-only default. Behind a real
    hostname you MUST set MCP_ALLOWED_HOSTS or every request gets a 421.
    """
    hosts = [h.strip() for h in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]
    origins = [o.strip() for o in os.environ.get("MCP_ALLOWED_ORIGINS", "").split(",") if o.strip()]
    if not hosts:
        return None
    return TransportSecuritySettings(allowed_hosts=hosts, allowed_origins=origins)


# --- Upstream API helper ------------------------------------------------------


async def _request(method: str, path: str, **kwargs: Any) -> Any:
    """Call the upstream API at most once per second, serialized.

    Returns parsed JSON, or {"error": ...} the model can read. The lock is
    held across the sleep and the request itself, so there is never more
    than one in-flight upstream call.
    """
    global _LAST_REQUEST_AT
    async with _RATE_LOCK:
        wait = _LAST_REQUEST_AT + _REQUEST_INTERVAL - time.monotonic()
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0) as client:
                resp = await client.request(method, path, headers={"Accept": "application/json"}, **kwargs)
                resp.raise_for_status()
                if resp.status_code == 204 or not resp.content:
                    return {"status": "ok"}
                return resp.json()
        except httpx.HTTPStatusError as exc:
            return {"error": f"API returned {exc.response.status_code}", "detail": exc.response.text[:500]}
        except httpx.RequestError as exc:
            return {"error": f"API request failed: {exc}"}
        finally:
            _LAST_REQUEST_AT = time.monotonic()


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, default=str, ensure_ascii=False)


def _trim_store(store: dict[str, Any]) -> dict[str, Any]:
    """Project a store object down to the fields that matter for queue watching."""
    return {
        "id": store.get("id"),
        "name": store.get("name"),
        "name_en": store.get("nameEn"),
        "store_status": store.get("storeStatus"),
        "net_ticket_status": store.get("netTicketStatus"),
        "wait": store.get("wait"),
        "address": store.get("address"),
        "area": store.get("area"),
        "latitude": store.get("latitude"),
        "longitude": store.get("longitude"),
    }


# --- Server and tools ---------------------------------------------------------


mcp = MCPServer(MCP_NAME)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
async def list_stores(
    latitude: Annotated[float, Field(description="Centre latitude to search around. Defaults to the middle of Hong Kong.")] = 22.0,
    longitude: Annotated[float, Field(description="Centre longitude to search around. Defaults to the middle of Hong Kong.")] = 114.0,
    region: Annotated[str, Field(description="Region code. The Sushiro Hong Kong site uses 'HK'.")] = "HK",
) -> str:
    """List Sushiro Hong Kong stores near a point, closest first.

    Always queries up to 100 stores. Each store includes: id (needed for
    get_store_queue), name, name_en, store_status ('OPEN' or closed),
    net_ticket_status ('OFFLINE_MANUAL' = issuing tickets,
    'OFFLINE_CLOSING'/'OFFLINE_CLOSED' = stopped issuing tickets), wait
    (number of groups currently waiting), address, area, latitude, longitude.
    """
    data = await _request(
        "GET",
        "/info/storelist",
        params={"latitude": latitude, "longitude": longitude, "numresults": 100, "region": region},
    )
    if isinstance(data, dict) and "error" in data:
        return _json(data)
    stores = data if isinstance(data, list) else []
    return _json([_trim_store(store) for store in stores])


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True))
async def get_store_queue(
    store_id: Annotated[int, Field(description="Numeric store id from list_stores.")],
    region: Annotated[str, Field(description="Region code. The Sushiro Hong Kong site uses 'HK'.")] = "HK",
) -> str:
    """Get the current ticket queue for one store.

    Returns the API's queue payload. storeQueue is the list of upcoming
    ticket numbers (the first element is the ticket being served next);
    boothQueue/counterQueue and reservation variants split it by ticket
    type. Empty arrays mean nobody is waiting.
    """
    return _json(await _request("GET", "/remote/groupqueues", params={"region": region, "storeid": store_id}))


# --- Plain HTTP routes (never authenticated; for liveness probes) --------------


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> Response:
    return JSONResponse({"status": "ok"})


# --- Entrypoint -----------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="sushiro-mcp",
        description="MCP server for the Sushiro Hong Kong SushiPass queue API.",
    )
    parser.add_argument(
        "--transport",
        choices=["http", "stdio"],
        default=None,
        help="Transport to serve on (overrides MCP_TRANSPORT; default: http).",
    )
    args = parser.parse_args()
    transport = (args.transport or os.environ.get("MCP_TRANSPORT", "http")).strip().lower()
    if transport not in ("http", "stdio"):
        parser.error(f"invalid transport: {transport!r} (expected 'http' or 'stdio')")
    if transport == "stdio":
        mcp.run(transport="stdio")
        return
    mcp.run(
        transport="streamable-http",
        host=MCP_HOST,
        port=MCP_PORT,
        transport_security=_transport_security(),
    )


if __name__ == "__main__":
    main()
