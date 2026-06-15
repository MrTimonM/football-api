from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


FOOTBALL_STAT_LABELS = [
    "Kick-off",
    "First Corner Kick",
    "First Yellow Card",
    "Shots",
    "Shots On Goal",
    "Foul",
    "Corner Kicks",
    "Corner Kicks(OT)",
    "Free Kicks",
    "Offsides",
    "Own Goal",
    "Yellow Card",
    "Yellow Card(OT)",
    "Red Card",
    "Possession",
    "Heads",
    "Saves",
    "Goalkeeper Off His Line",
    "Miss",
    "Tackle Success",
    "Intercept",
    "Long Pass",
    "Short Pass",
    "Assists",
    "Pass Success",
    "First Substitution",
    "Last Substitution",
    "First Offside",
    "Last Offside",
    "Substitutions",
    "Last Corner Kick",
    "Last Yellow Card",
    "Substitution(OT)",
    "Offsides(OT)",
    "Off Target",
    "Shot on post",
    "Head Success",
    "Blocked",
    "Tackles",
    "Dribbles",
    "Throw ins",
    "Pass",
    "Pass Success",
    "Attack",
    "Dangerous attack",
    "Corner Kicks(HT)",
    "Possession(HT)",
]

EVENT_KIND_LABELS = {
    1: "Goal",
    2: "Red Card",
    3: "Yellow Card",
    7: "Penalty",
    8: "Own goal",
    9: "2 Yellow Cards→1 Red Card",
    11: "Substitution",
    13: "Penalty missed",
    15: "VAR",
}


def iso_from_ms(value: Any) -> str | None:
    try:
        ms = int(value)
    except (TypeError, ValueError):
        return None
    if ms <= 0:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def clean_score(value: Any) -> int | None:
    if value in ("", None):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def status_from_state(state: Any, live_state: Any = None) -> str:
    try:
        state_num = int(state)
    except (TypeError, ValueError):
        state_num = 0

    try:
        live_state_num = int(live_state)
    except (TypeError, ValueError):
        live_state_num = 0

    if state_num == 0:
        return "scheduled"
    if state_num < 0:
        return "finished"
    if live_state_num > 0 or state_num > 0:
        return "live"
    return "unknown"


def name_from_slug(slug: str | None, side: str) -> str | None:
    if not slug or "-vs-" not in slug:
        return None
    home, away = slug.split("-vs-", 1)
    value = home if side == "home" else away
    return " ".join(part.capitalize() for part in value.split("-") if part)


def normalize_match(item: dict[str, Any], sport: str = "football") -> dict[str, Any]:
    home_name = item.get("homeName") or name_from_slug(item.get("teamLink"), "home")
    away_name = item.get("awayName") or name_from_slug(item.get("teamLink"), "away")

    return {
        "id": str(item.get("matchId")),
        "sport": sport,
        "status": status_from_state(item.get("state"), item.get("liveState")),
        "state": item.get("state"),
        "liveState": item.get("liveState"),
        "kickoff": iso_from_ms(item.get("matchTime_t")),
        "startTime": iso_from_ms(item.get("startTime_t")),
        "league": {
            "id": item.get("leagueId"),
            "name": item.get("leagueEn") or ("World Cup 2026" if sport == "world-cup" else None),
            "country": item.get("countryEn") or ("World" if sport == "world-cup" else None),
            "logo": item.get("leagueLogo"),
        },
        "group": item.get("grouping"),
        "round": item.get("round"),
        "home": {
            "id": item.get("homeId"),
            "name": home_name,
            "logo": item.get("homeLogoUrl"),
        },
        "away": {
            "id": item.get("awayId"),
            "name": away_name,
            "logo": item.get("awayLogoUrl"),
        },
        "score": {
            "home": clean_score(item.get("homeScore")),
            "away": clean_score(item.get("awayScore")),
        },
        "halfTimeScore": {
            "home": clean_score(item.get("homeHalfScore")),
            "away": clean_score(item.get("awayHalfScore")),
        },
        "cards": {
            "homeRed": clean_score(item.get("homeRed")),
            "awayRed": clean_score(item.get("awayRed")),
            "homeYellow": clean_score(item.get("homeYellow")),
            "awayYellow": clean_score(item.get("awayYellow")),
        },
        "corners": {
            "home": clean_score(item.get("homeCorner")),
            "away": clean_score(item.get("awayCorner")),
        },
        "season": item.get("season"),
        "location": item.get("location"),
        "weather": item.get("weather"),
        "teamLink": item.get("teamLink"),
        "hasChannel": item.get("hasChannel"),
        "isVipOnly": item.get("isVipOnly"),
        "raw": item,
    }


def parse_technic_count(value: str | None) -> list[dict[str, Any]]:
    if not value:
        return []

    stats: list[dict[str, Any]] = []
    for row in value.split(";"):
        parts = row.split(",")
        if len(parts) < 3:
            continue
        try:
            code = int(parts[0])
        except ValueError:
            continue
        label = FOOTBALL_STAT_LABELS[code] if 0 <= code < len(FOOTBALL_STAT_LABELS) else f"Stat {code}"
        stats.append(
            {
                "code": code,
                "name": label,
                "home": parts[1],
                "away": parts[2],
            }
        )
    return stats


def normalize_event(item: dict[str, Any]) -> dict[str, Any]:
    try:
        kind = int(item.get("kind"))
    except (TypeError, ValueError):
        kind = None

    return {
        "id": item.get("id"),
        "team": "home" if item.get("isHome") else "away",
        "minute": item.get("time"),
        "kind": kind,
        "type": EVENT_KIND_LABELS.get(kind, f"Event {kind}" if kind is not None else "Event"),
        "player": item.get("nameEn") or item.get("nameChs"),
        "playerId": item.get("playerId"),
        "relatedPlayerId": item.get("playerId2"),
        "overtime": item.get("overtime"),
        "raw": item,
    }


def normalize_detail(data: dict[str, Any], sport: str = "football") -> dict[str, Any]:
    match = normalize_match(data["match"], sport=sport) if data.get("match") else None
    events = [normalize_event(item) for item in data.get("event") or []]

    return {
        "match": match,
        "hasEvents": bool(data.get("hasEvents")),
        "events": events,
        "hasStats": bool(data.get("hasTechnicCount")),
        "stats": parse_technic_count(data.get("technicCount")),
        "lineup": data.get("lineup"),
        "extension": data.get("extension"),
        "raw": data,
    }


def filter_matches(
    matches: list[dict[str, Any]],
    *,
    live: bool = False,
    query: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    filtered = matches
    if live:
        filtered = [match for match in filtered if match["status"] == "live"]
    if status:
        filtered = [match for match in filtered if match["status"] == status]
    if query:
        needle = query.lower()

        def matches_query(match: dict[str, Any]) -> bool:
            values = (
                match.get("league", {}).get("name"),
                match.get("league", {}).get("country"),
                match.get("home", {}).get("name"),
                match.get("away", {}).get("name"),
                match.get("teamLink"),
            )
            return needle in " ".join(str(value or "") for value in values).lower()

        filtered = [match for match in filtered if matches_query(match)]
    return filtered
