import unittest

from fubo808_parser import (
    filter_matches,
    iso_from_ms,
    normalize_detail,
    normalize_event,
    normalize_match,
    parse_technic_count,
    status_from_state,
)


class Fubo808ParserTest(unittest.TestCase):
    def test_normalize_football_match(self):
        match = normalize_match(
            {
                "matchId": 2990785,
                "leagueId": 222,
                "leagueEn": "Maurice Revello Tournament",
                "countryEn": "International",
                "matchTime_t": 1781110800000,
                "startTime_t": 1781114570000,
                "homeId": "23611",
                "awayId": "5328",
                "homeName": "Colombia U19",
                "awayName": "Tunisia U23",
                "state": 3,
                "homeScore": 0,
                "awayScore": 0,
                "homeYellow": 2,
                "awayYellow": 2,
                "teamLink": "colombia-u19-vs-tunisia-u23",
            }
        )

        self.assertEqual(match["id"], "2990785")
        self.assertEqual(match["status"], "live")
        self.assertEqual(match["home"]["name"], "Colombia U19")
        self.assertEqual(match["away"]["name"], "Tunisia U23")
        self.assertEqual(match["score"]["home"], 0)
        self.assertEqual(match["cards"]["homeYellow"], 2)

    def test_normalize_world_cup_match_from_slug(self):
        match = normalize_match(
            {
                "matchId": 2906701,
                "matchTime_t": 1781204400000,
                "homeId": 819,
                "awayId": 803,
                "homeScore": 0,
                "awayScore": 0,
                "state": 0,
                "grouping": "A",
                "round": 48,
                "teamLink": "mexico-vs-south-africa",
            },
            sport="world-cup",
        )

        self.assertEqual(match["status"], "scheduled")
        self.assertEqual(match["league"]["name"], "World Cup 2026")
        self.assertEqual(match["home"]["name"], "Mexico")
        self.assertEqual(match["away"]["name"], "South Africa")

    def test_filter_matches(self):
        matches = [
            normalize_match({"matchId": 1, "state": 1, "homeName": "A", "awayName": "B"}),
            normalize_match({"matchId": 2, "state": 0, "homeName": "Mexico", "awayName": "South Africa"}),
            normalize_match(
                {
                    "matchId": 3,
                    "state": -1,
                    "leagueEn": "Premier League",
                    "countryEn": "England",
                    "homeName": "Chelsea",
                    "awayName": "Arsenal",
                }
            ),
        ]

        self.assertEqual(len(filter_matches(matches, live=True)), 1)
        self.assertEqual(filter_matches(matches, query="mexico")[0]["id"], "2")
        self.assertEqual(filter_matches(matches, status="finished")[0]["id"], "3")
        self.assertEqual(filter_matches(matches, query="england")[0]["id"], "3")

    def test_parse_technic_count(self):
        stats = parse_technic_count("6,13,4;14,64%,36%;45,6,3")

        self.assertEqual(stats[0]["name"], "Corner Kicks")
        self.assertEqual(stats[0]["home"], "13")
        self.assertEqual(stats[1]["name"], "Possession")
        self.assertEqual(stats[1]["away"], "36%")
        self.assertEqual(stats[2]["name"], "Corner Kicks(HT)")

    def test_parse_technic_count_skips_bad_rows_and_labels_unknown_codes(self):
        stats = parse_technic_count("bad,row;999,1,2;4,5,6;7,only-two-parts")

        self.assertEqual(len(stats), 2)
        self.assertEqual(stats[0]["name"], "Stat 999")
        self.assertEqual(stats[0]["home"], "1")
        self.assertEqual(stats[1]["name"], "Shots On Goal")

    def test_normalize_detail(self):
        detail = normalize_detail(
            {
                "match": {
                    "matchId": 2990785,
                    "state": 3,
                    "homeName": "Colombia U19",
                    "awayName": "Tunisia U23",
                },
                "hasEvents": True,
                "event": [{"id": 1, "isHome": True, "kind": 3, "time": "11", "nameEn": "Player"}],
                "hasTechnicCount": True,
                "technicCount": "3,16,10",
                "lineup": {"homeArray": "4141"},
            }
        )

        self.assertEqual(detail["match"]["id"], "2990785")
        self.assertEqual(detail["events"][0]["type"], "Yellow Card")
        self.assertEqual(detail["stats"][0]["name"], "Shots")

    def test_time_score_and_status_edge_cases(self):
        self.assertIsNone(iso_from_ms(None))
        self.assertIsNone(iso_from_ms(0))
        self.assertEqual(iso_from_ms(1781110800000), "2026-06-10T17:00:00+00:00")
        self.assertEqual(status_from_state(-1), "finished")
        self.assertEqual(status_from_state("0", "2"), "scheduled")
        self.assertEqual(status_from_state("abc", None), "scheduled")

        match = normalize_match(
            {
                "matchId": "abc",
                "state": -1,
                "homeScore": "",
                "awayScore": "2",
                "homeRed": None,
                "awayYellow": "bad",
            }
        )

        self.assertEqual(match["status"], "finished")
        self.assertIsNone(match["score"]["home"])
        self.assertEqual(match["score"]["away"], 2)
        self.assertIsNone(match["cards"]["homeRed"])
        self.assertIsNone(match["cards"]["awayYellow"])

    def test_normalize_event_fallbacks(self):
        home_event = normalize_event({"id": "e1", "isHome": True, "kind": "999", "nameChs": "Fallback"})
        away_event = normalize_event({"id": "e2", "isHome": False, "kind": None})

        self.assertEqual(home_event["team"], "home")
        self.assertEqual(home_event["type"], "Event 999")
        self.assertEqual(home_event["player"], "Fallback")
        self.assertEqual(away_event["team"], "away")
        self.assertEqual(away_event["type"], "Event")


if __name__ == "__main__":
    unittest.main()
