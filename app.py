from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen

from fubo808_parser import filter_matches, normalize_detail, normalize_match


BASE_URL = "https://cfapi.aifvfjuf56juh.cfd"
SITE_URL = "https://www.808fubo808.com"
DEFAULT_PORT = 8001
CACHE_TTL_SECONDS = 20
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) 808FuboPersonalAPI/1.0"
PUBLIC_API_PREFIX = os.environ.get("PUBLIC_API_PREFIX", "/api").rstrip("/") or "/api"

SPORT_PATHS = {
    "football": "/api/ftb/schedules",
    "basketball": "/api/bsk/schedules",
    "merge": "/api/merge/schedules",
    "score": "/api/score/schedules?lang=3&d=www.808fubo808.com&live=1",
}

_cache: dict[str, dict[str, Any]] = {}
_image_cache: dict[str, dict[str, Any]] = {}
IMAGE_CACHE_TTL_SECONDS = 86400
ALLOWED_IMAGE_HOSTS = {"zq.win007.com", "zq.titan007.com"}


class ApiError(Exception):
    def __init__(self, message: str, status: int = 500) -> None:
        super().__init__(message)
        self.status = status


def fetch_json(path: str, *, refresh: bool = False) -> Any:
    now = time.time()
    cached = _cache.get(path)
    if cached and not refresh and now - cached["at"] < CACHE_TTL_SECONDS:
        return cached["data"]

    request = Request(
        f"{BASE_URL}{path}",
        headers={
            "User-Agent": USER_AGENT,
            "Referer": f"{SITE_URL}/",
            "Origin": SITE_URL,
            "Accept": "application/json,text/plain,*/*",
        },
    )

    try:
        with urlopen(request, timeout=20) as response:
            body_bytes = response.read()
            content_type = response.headers.get("Content-Type", "")
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise ApiError(f"Upstream returned HTTP {error.code}: {body[:200]}", 502) from error
    except URLError as error:
        raise ApiError(f"Could not reach upstream: {error.reason}", 502) from error

    if "application/x-msgpack" in content_type:
        data = MsgpackReader(body_bytes).read()
    else:
        body = body_bytes.decode("utf-8", errors="replace")
        try:
            data = json.loads(body)
        except json.JSONDecodeError as error:
            raise ApiError(f"Upstream returned non-JSON data: {body[:200]}", 502) from error

    _cache[path] = {"data": data, "at": now}
    return data


class MsgpackReader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.index = 0

    def read_byte(self) -> int:
        value = self.data[self.index]
        self.index += 1
        return value

    def read_exact(self, length: int) -> bytes:
        value = self.data[self.index : self.index + length]
        self.index += length
        return value

    def read_uint(self, length: int) -> int:
        return int.from_bytes(self.read_exact(length), "big", signed=False)

    def read_int(self, length: int) -> int:
        return int.from_bytes(self.read_exact(length), "big", signed=True)

    def read(self) -> Any:
        marker = self.read_byte()

        if marker <= 0x7F:
            return marker
        if 0x80 <= marker <= 0x8F:
            return self.read_map(marker & 0x0F)
        if 0x90 <= marker <= 0x9F:
            return self.read_array(marker & 0x0F)
        if 0xA0 <= marker <= 0xBF:
            return self.read_string(marker & 0x1F)
        if marker >= 0xE0:
            return marker - 0x100

        if marker == 0xC0:
            return None
        if marker == 0xC2:
            return False
        if marker == 0xC3:
            return True
        if marker == 0xCA:
            import struct

            return struct.unpack(">f", self.read_exact(4))[0]
        if marker == 0xCB:
            import struct

            return struct.unpack(">d", self.read_exact(8))[0]
        if marker == 0xCC:
            return self.read_uint(1)
        if marker == 0xCD:
            return self.read_uint(2)
        if marker == 0xCE:
            return self.read_uint(4)
        if marker == 0xCF:
            return self.read_uint(8)
        if marker == 0xD0:
            return self.read_int(1)
        if marker == 0xD1:
            return self.read_int(2)
        if marker == 0xD2:
            return self.read_int(4)
        if marker == 0xD3:
            return self.read_int(8)
        if marker == 0xD9:
            return self.read_string(self.read_uint(1))
        if marker == 0xDA:
            return self.read_string(self.read_uint(2))
        if marker == 0xDB:
            return self.read_string(self.read_uint(4))
        if marker == 0xDC:
            return self.read_array(self.read_uint(2))
        if marker == 0xDD:
            return self.read_array(self.read_uint(4))
        if marker == 0xDE:
            return self.read_map(self.read_uint(2))
        if marker == 0xDF:
            return self.read_map(self.read_uint(4))
        if marker == 0xC4:
            return self.read_exact(self.read_uint(1))
        if marker == 0xC5:
            return self.read_exact(self.read_uint(2))
        if marker == 0xC6:
            return self.read_exact(self.read_uint(4))

        raise ApiError(f"Unsupported MessagePack marker: 0x{marker:02x}", 502)

    def read_string(self, length: int) -> str:
        return self.read_exact(length).decode("utf-8", errors="replace")

    def read_array(self, length: int) -> list[Any]:
        return [self.read() for _ in range(length)]

    def read_map(self, length: int) -> dict[Any, Any]:
        return {self.read(): self.read() for _ in range(length)}


def get_matches(sport: str = "football", *, refresh: bool = False) -> list[dict[str, Any]]:
    if sport not in SPORT_PATHS:
        raise ApiError("sport must be football, basketball, merge, or score", 400)
    data = fetch_json(SPORT_PATHS[sport], refresh=refresh)
    return [normalize_match(item, sport=sport) for item in data.get("matchList", [])]


def get_world_cup(*, refresh: bool = False) -> list[dict[str, Any]]:
    data = fetch_json("/api/worldcup/list", refresh=refresh)
    return [normalize_match(item, sport="world-cup") for item in data.get("matchs", [])]


def get_detail(match_id: str, *, sport: str = "football", refresh: bool = False) -> dict[str, Any]:
    if sport == "basketball":
        path = f"/api/bsk/detail?id={match_id}"
    elif sport in {"football", "world-cup", "merge"}:
        path = f"/api/ftb/detail?id={match_id}"
    else:
        raise ApiError("sport must be football, basketball, world-cup, or merge", 400)
    data = fetch_json(path, refresh=refresh)
    return normalize_detail(data, sport="basketball" if sport == "basketball" else "football")


def public_match(match: dict[str, Any], include_raw: bool = False) -> dict[str, Any]:
    if include_raw:
        return match
    clean = {key: value for key, value in match.items() if key != "raw"}
    rewrite_match_logos(clean)
    return clean


def public_matches(matches: list[dict[str, Any]], include_raw: bool = False) -> list[dict[str, Any]]:
    return [public_match(match, include_raw=include_raw) for match in matches]


def public_detail(detail: dict[str, Any], include_raw: bool = False) -> dict[str, Any]:
    if include_raw:
        return detail
    clean = {key: value for key, value in detail.items() if key != "raw"}
    clean["events"] = [
        {key: value for key, value in event.items() if key != "raw"}
        for event in clean.get("events", [])
    ]
    if clean.get("match"):
        clean["match"] = public_match(clean["match"])
    return clean


def json_response(handler: BaseHTTPRequestHandler, payload: Any, status: int = 200) -> None:
    body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def image_response(handler: BaseHTTPRequestHandler, body: bytes, content_type: str, status: int = 200) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", f"public, max-age={IMAGE_CACHE_TTL_SECONDS}")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def normalize_image_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc == "zq.win007.com":
        return parsed._replace(scheme="https", netloc="zq.titan007.com").geturl()
    if parsed.netloc == "zq.titan007.com" and parsed.scheme == "http":
        return parsed._replace(scheme="https").geturl()
    return url


def proxy_image_url(url: str | None) -> str | None:
    if not url:
        return None
    fixed = normalize_image_url(url)
    return f"{PUBLIC_API_PREFIX}/image?url={quote(fixed, safe='')}"


def rewrite_match_logos(match: dict[str, Any]) -> None:
    for side in ("home", "away", "league"):
        item = match.get(side)
        if isinstance(item, dict):
            item["logo"] = proxy_image_url(item.get("logo"))


def fetch_image(url: str) -> tuple[bytes, str]:
    fixed = normalize_image_url(url)
    parsed = urlparse(fixed)
    if parsed.netloc not in ALLOWED_IMAGE_HOSTS:
        raise ApiError("Image host is not allowed", 400)

    now = time.time()
    cached = _image_cache.get(fixed)
    if cached and now - cached["at"] < IMAGE_CACHE_TTL_SECONDS:
        return cached["body"], cached["content_type"]

    request = Request(
        fixed,
        headers={
            "User-Agent": USER_AGENT,
            "Referer": "https://zq.titan007.com/",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        },
    )

    try:
        with urlopen(request, timeout=20) as response:
            body = response.read()
            content_type = response.headers.get("Content-Type", "image/png")
    except HTTPError as error:
        raise ApiError(f"Image upstream returned HTTP {error.code}", 502) from error
    except URLError as error:
        raise ApiError(f"Could not reach image upstream: {error.reason}", 502) from error

    _image_cache[fixed] = {"body": body, "content_type": content_type, "at": now}
    return body, content_type


def first(params: dict[str, list[str]], key: str) -> str | None:
    values = params.get(key)
    return values[0] if values else None


class Fubo808ApiHandler(BaseHTTPRequestHandler):
    server_version = "808FuboPersonalAPI/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        try:
            self.route_get()
        except ApiError as error:
            json_response(self, {"error": str(error)}, error.status)
        except Exception as error:
            json_response(self, {"error": f"Unexpected server error: {error}"}, 500)

    def route_get(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        params = parse_qs(parsed.query)
        refresh = (first(params, "refresh") or "false").lower() in {"1", "true", "yes"}
        include_raw = (first(params, "raw") or "false").lower() in {"1", "true", "yes"}
        sport = first(params, "sport") or "football"

        if path == "/":
            json_response(
                self,
                {
                    "name": "808fubo808 Personal API",
                    "source": SITE_URL,
                    "endpoints": [
                        "/api/health",
                        "/api/matches",
                        "/api/live",
                        "/api/world-cup",
                        "/api/matches/{id}",
                        "/api/matches/{id}/details",
                    ],
                },
            )
            return

        if path == "/api/health":
            matches = get_matches(sport=sport, refresh=refresh)
            json_response(
                self,
                {
                    "ok": True,
                    "source": SITE_URL,
                    "upstream": BASE_URL,
                    "sport": sport,
                    "matchCount": len(matches),
                    "cacheTtlSeconds": CACHE_TTL_SECONDS,
                },
            )
            return

        if path == "/api/image":
            url = first(params, "url")
            if not url:
                json_response(self, {"error": "Missing image url"}, 400)
                return
            body, content_type = fetch_image(url)
            image_response(self, body, content_type)
            return

        if path == "/api/matches":
            matches = get_matches(sport=sport, refresh=refresh)
            matches = filter_matches(
                matches,
                query=first(params, "q") or first(params, "league"),
                status=first(params, "status"),
            )
            json_response(self, {"count": len(matches), "matches": public_matches(matches, include_raw)})
            return

        if path == "/api/live":
            matches = filter_matches(
                get_matches(sport=sport, refresh=refresh),
                live=True,
                query=first(params, "q") or first(params, "league"),
            )
            json_response(self, {"count": len(matches), "matches": public_matches(matches, include_raw)})
            return

        if path == "/api/world-cup":
            matches = get_world_cup(refresh=refresh)
            matches = filter_matches(
                matches,
                query=first(params, "q"),
                status=first(params, "status"),
            )
            json_response(self, {"count": len(matches), "matches": public_matches(matches, include_raw)})
            return

        if path.startswith("/api/matches/") and path.endswith("/details"):
            match_id = path.split("/")[-2]
            detail = get_detail(match_id, sport=sport, refresh=refresh)
            if detail.get("match") is None:
                json_response(self, {"error": f"Details for match {match_id} were not found"}, 404)
                return
            json_response(self, public_detail(detail, include_raw))
            return

        if path.startswith("/api/matches/"):
            match_id = path.rsplit("/", 1)[-1]
            matches = get_world_cup(refresh=refresh) + get_matches(sport=sport, refresh=refresh)
            match = next((item for item in matches if item["id"] == match_id), None)
            if match is None:
                json_response(self, {"error": f"Match {match_id} was not found"}, 404)
                return
            json_response(self, public_match(match, include_raw))
            return

        json_response(self, {"error": "Not found"}, 404)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", DEFAULT_PORT), Fubo808ApiHandler)
    print(f"808fubo808 Personal API running at http://127.0.0.1:{DEFAULT_PORT}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
