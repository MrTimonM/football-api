# 808fubo808 Football API

A lightweight Python API for football match schedules, live scores, World Cup fixtures, match details, events, lineups, and stats.

This project is designed to run as a simple local or VPS-hosted JSON API. It uses only the Python standard library, so setup is quick and there are no package dependencies to install.

## Features

- Football match schedule API
- Live match API
- Basketball and merged sports feed support
- World Cup fixture endpoint
- Match details with events, lineups, and stats
- Clean JSON response format
- Team and league logo proxy
- 20-second in-memory cache for faster repeated requests

## Project Structure

```text
808fubo808/
  app.py
  fubo808_parser.py
  README.md
  HOSTING.md
```

## Requirements

- Python 3.10+
- Internet access

No external Python packages are required.

## Run Locally

```powershell
git clone https://github.com/MrTimonM/football-api.git
cd football-api
python app.py
```

The API will run at:

```text
http://127.0.0.1:8001
```

Health check:

```powershell
Invoke-RestMethod "http://127.0.0.1:8001/api/health" | ConvertTo-Json -Depth 6
```

## API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/` | API information |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/matches` | Match schedule |
| `GET` | `/api/live` | Live matches |
| `GET` | `/api/world-cup` | World Cup fixtures |
| `GET` | `/api/matches/{id}` | Single match by ID |
| `GET` | `/api/matches/{id}/details` | Match details, events, lineup, and stats |
| `GET` | `/api/image?url=...` | Logo/image proxy |

## Query Parameters

| Parameter | Example | Description |
| --- | --- | --- |
| `sport` | `?sport=football` | Feed type: `football`, `basketball`, `merge`, or `score` |
| `q` | `?q=mexico` | Search by team, league, country, or slug |
| `league` | `?league=premier` | Same search behavior as `q` |
| `status` | `?status=live` | Filter by `scheduled`, `live`, `finished`, or `unknown` |
| `refresh` | `?refresh=true` | Skip cache and fetch fresh data |
| `raw` | `?raw=true` | Include original raw fields for debugging |

## Example Requests

Get all football matches:

```powershell
Invoke-RestMethod "http://127.0.0.1:8001/api/matches" | ConvertTo-Json -Depth 8
```

Get live matches:

```powershell
Invoke-RestMethod "http://127.0.0.1:8001/api/live" | ConvertTo-Json -Depth 8
```

Search matches:

```powershell
Invoke-RestMethod "http://127.0.0.1:8001/api/matches?q=mexico" | ConvertTo-Json -Depth 8
```

Get one match:

```powershell
Invoke-RestMethod "http://127.0.0.1:8001/api/matches/2990785" | ConvertTo-Json -Depth 8
```

Get match details:

```powershell
Invoke-RestMethod "http://127.0.0.1:8001/api/matches/2990785/details" | ConvertTo-Json -Depth 12
```

## Example Match Response

```json
{
  "id": "2990785",
  "sport": "football",
  "status": "live",
  "kickoff": "2026-06-10T17:00:00+00:00",
  "league": {
    "id": 222,
    "name": "Maurice Revello Tournament",
    "country": "International",
    "logo": "/api/image?url=..."
  },
  "home": {
    "id": "23611",
    "name": "Colombia U19",
    "logo": "/api/image?url=..."
  },
  "away": {
    "id": "5328",
    "name": "Tunisia U23",
    "logo": "/api/image?url=..."
  },
  "score": {
    "home": 0,
    "away": 0
  },
  "cards": {
    "homeRed": 0,
    "awayRed": 0,
    "homeYellow": 2,
    "awayYellow": 2
  },
  "corners": {
    "home": 14,
    "away": 4
  }
}
```

## Example Detail Response

```json
{
  "match": {
    "id": "2990785",
    "sport": "football",
    "status": "live"
  },
  "hasEvents": true,
  "events": [
    {
      "id": 14798422,
      "team": "away",
      "minute": "6",
      "kind": 3,
      "type": "Yellow Card",
      "player": "Youssef Herch"
    }
  ],
  "hasStats": true,
  "stats": [
    {
      "code": 14,
      "name": "Possession",
      "home": "65%",
      "away": "35%"
    }
  ],
  "lineup": {},
  "extension": null
}
```

## Status Values

| Status | Meaning |
| --- | --- |
| `scheduled` | Match has not started |
| `live` | Match is currently active |
| `finished` | Match is complete |
| `unknown` | Status could not be mapped |

## Common Stat Labels

| Code | Name |
| --- | --- |
| `3` | Shots |
| `4` | Shots On Goal |
| `5` | Foul |
| `6` | Corner Kicks |
| `9` | Offsides |
| `11` | Yellow Card |
| `13` | Red Card |
| `14` | Possession |
| `34` | Off Target |
| `37` | Blocked |
| `38` | Tackles |
| `43` | Attack |
| `44` | Dangerous attack |

## Event Labels

| Kind | Type |
| --- | --- |
| `1` | Goal |
| `2` | Red Card |
| `3` | Yellow Card |
| `7` | Penalty |
| `8` | Own goal |
| `11` | Substitution |
| `13` | Penalty missed |
| `15` | VAR |

## Host On A VPS

See [HOSTING.md](HOSTING.md) for a full VPS setup guide using Python, systemd, and Nginx.

## Documentation Page

A polished documentation page is available at [docs/index.html](docs/index.html).

After GitHub Pages is enabled, the public documentation link will be:

```text
https://mrtimonm.github.io/football-api/
```

To enable it, open the repository settings and set:

```text
Settings -> Pages -> Build and deployment
Source: Deploy from a branch
Branch: main
Folder: /docs
```

## Check Python Syntax

```powershell
python -m py_compile app.py fubo808_parser.py
```

## Error Format

```json
{
  "error": "Message describing the problem"
}
```

Common status codes:

| Status | Meaning |
| --- | --- |
| `400` | Bad request or unsupported sport |
| `404` | Match/detail not found |
| `500` | Local server error |
| `502` | Data source request failed |

## Development

When changing the API:

1. Update route or fetch logic in `app.py`.
2. Update parsing logic in `fubo808_parser.py`.
3. Run `python -m py_compile app.py fubo808_parser.py`.

## Credits

Football icon used for `shoot.png`: [Football icons created by Freepik - Flaticon](https://www.flaticon.com/free-icons/football).

## Views

![Profile views](https://komarev.com/ghpvc/?username=MrTimonM&label=Repository%20views&color=2563eb&style=flat)
