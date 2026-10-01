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
