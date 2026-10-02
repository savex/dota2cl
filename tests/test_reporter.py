import io
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from tests.test_base import DotClientTestBase


class TestReporterTime(DotClientTestBase):
    """
    Parsing of player history timestamps and experience calculation.
    """
    def _make_report(self, players):
        from dotclient.reporter import topTeamsReport
        _client = mock.Mock()
        _client.get_pro_players.return_value = players
        _client.get_team_by_id.return_value = {}
        _args = SimpleNamespace(output=io.StringIO(), throttle=False,
                                num_teams=5, preload_teams=False)
        return topTeamsReport(_args, api_client=_client)

    def test_parse_time_formats(self):
        from dotclient.reporter import dotaReporter
        _expected = datetime(2025, 2, 21, 10, 0, 14, 982000,
                             tzinfo=timezone.utc)
        self.assertEqual(
            dotaReporter.parse_time("2025-02-21T10:00:14.982Z"), _expected)
        # No fractional seconds
        self.assertEqual(
            dotaReporter.parse_time("2025-02-21T10:00:14Z"),
            _expected.replace(microsecond=0))
        # No timezone is treated as UTC
        self.assertEqual(
            dotaReporter.parse_time("2025-02-21T10:00:14.982"), _expected)
        for _bad in ("not a date", "", None):
            with self.assertRaises((ValueError, TypeError)):
                dotaReporter.parse_time(_bad)

    def test_experience_uses_utc(self):
        # History started exactly 1 hour ago in UTC, so experience must be
        # about 3600 seconds regardless of the local timezone
        _start = datetime.now(timezone.utc) - timedelta(hours=1)
        _report = self._make_report([{
            "personaname": "p1", "team_id": 1,
            "full_history_time":
                _start.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        }])
        _report.generate_payload()
        _team = _report.payload["top_teams"][0]
        self.assertAlmostEqual(_team["Team Experience"], 3600, delta=5)

    def test_invalid_history_time_skips_player(self):
        _report = self._make_report([
            {"personaname": "bad", "team_id": 1,
             "full_history_time": "yesterday"},
            {"personaname": "good", "team_id": 1,
             "full_history_time": "2025-02-21T10:00:14Z"},
        ])
        with self.redirect_output():
            _report.generate_payload()
        _players = _report.payload["top_teams"][0]["Players"]
        self.assertEqual([p["Personaname"] for p in _players], ["good"])


class TestReporterTeamLookup(DotClientTestBase):
    """
    Players reported with team_id 0 are matched to a team by name.
    """
    _history = "2025-02-21T10:00:14Z"
    _teams = [
        {"team_id": 10, "name": "Alpha"},
        {"team_id": 20, "name": "Twins"},
        {"team_id": 21, "name": "Twins"},
    ]

    def _player(self, name, team_id, team_name=None):
        return {"personaname": name, "team_id": team_id,
                "team_name": team_name,
                "full_history_time": self._history}

    def _report_players(self, players, preload_teams=True):
        from dotclient.reporter import topTeamsReport
        _client = mock.Mock()
        _client.get_pro_players.return_value = players
        _client.get_teams.return_value = self._teams
        _client.get_team_by_id.return_value = {}
        _args = SimpleNamespace(output=io.StringIO(), throttle=False,
                                num_teams=5, preload_teams=preload_teams)
        _report = topTeamsReport(_args, api_client=_client)
        with self.redirect_output():
            _report.generate_payload()
        return {t["Team ID"]: [p["Personaname"] for p in t["Players"]]
                for t in _report.payload["top_teams"]}

    def test_team_id_zero_resolved_by_name(self):
        _teams = self._report_players([
            self._player("direct", 10),
            self._player("by_name", 0, "Alpha"),
        ])
        self.assertEqual(_teams, {10: ["direct", "by_name"]})

    def test_team_id_zero_unresolved_players_skipped(self):
        _teams = self._report_players([
            self._player("direct", 10),
            self._player("ambiguous", 0, "Twins"),
            self._player("unknown", 0, "Nobody"),
            self._player("no_name", 0),
        ])
        self.assertEqual(_teams, {10: ["direct"]})

    def test_team_id_zero_skipped_without_preload(self):
        _teams = self._report_players([
            self._player("direct", 10),
            self._player("by_name", 0, "Alpha"),
        ], preload_teams=False)
        self.assertEqual(_teams, {10: ["direct"]})

    def test_missing_team_id_skipped(self):
        _teams = self._report_players([
            self._player("direct", 10),
            self._player("free_agent", None),
        ])
        self.assertEqual(_teams, {10: ["direct"]})

    def test_api_data_not_modified(self):
        # Players come from the client cache, so the report
        # must not change them
        from copy import deepcopy
        _players = [
            self._player("direct", 10),
            self._player("by_name", 0, "Alpha"),
            self._player("unknown", 0, "Nobody"),
        ]
        _original = deepcopy(_players)
        self._report_players(_players)
        self.assertEqual(_players, _original)


class TestReporterPayload(DotClientTestBase):
    """
    Report payload state and saving.
    """
    def _make_report(self):
        from dotclient.reporter import topTeamsReport
        _args = SimpleNamespace(output=io.StringIO(), throttle=False,
                                num_teams=5, preload_teams=False)
        return topTeamsReport(_args, api_client=mock.Mock())

    def test_payload_not_shared(self):
        _first = self._make_report()
        _second = self._make_report()
        _first.payload["key"] = "value"
        self.assertEqual(_second.payload, {})

    def test_save_payload_uses_argument(self):
        _report = self._make_report()
        _report.payload = {"stale": True}
        _report.save_payload({"fresh": True})
        _out = _report.output.getvalue()
        self.assertIn("fresh", _out)
        self.assertNotIn("stale", _out)
