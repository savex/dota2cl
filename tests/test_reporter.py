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
        from dota2cl.reporter import TopTeamsReport
        _client = mock.Mock()
        _client.get_pro_players.return_value = players
        _client.get_team_by_id.return_value = {}
        _args = SimpleNamespace(output=io.StringIO(), throttle=False,
                                num_teams=5, preload_teams=False)
        return TopTeamsReport(_args, api_client=_client)

    def test_parse_time_formats(self):
        from dota2cl.reporter import DotaReporter
        _expected = datetime(2025, 2, 21, 10, 0, 14, 982000,
                             tzinfo=timezone.utc)
        self.assertEqual(
            DotaReporter.parse_time("2025-02-21T10:00:14.982Z"), _expected)
        # No fractional seconds
        self.assertEqual(
            DotaReporter.parse_time("2025-02-21T10:00:14Z"),
            _expected.replace(microsecond=0))
        # No timezone is treated as UTC
        self.assertEqual(
            DotaReporter.parse_time("2025-02-21T10:00:14.982"), _expected)
        for _bad in ("not a date", "", None):
            with self.assertRaises((ValueError, TypeError)):
                DotaReporter.parse_time(_bad)

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
        from dota2cl.reporter import TopTeamsReport
        _client = mock.Mock()
        _client.get_pro_players.return_value = players
        _client.get_teams.return_value = self._teams
        _client.get_team_by_id.return_value = {}
        _args = SimpleNamespace(output=io.StringIO(), throttle=False,
                                num_teams=5, preload_teams=preload_teams)
        _report = TopTeamsReport(_args, api_client=_client)
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
        from dota2cl.reporter import TopTeamsReport
        _args = SimpleNamespace(output=io.StringIO(), throttle=False,
                                num_teams=5, preload_teams=False)
        return TopTeamsReport(_args, api_client=mock.Mock())

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


class TestReporterTeamDetails(DotClientTestBase):
    """
    Team details lookup for the top teams.
    """
    def test_failed_team_details_keep_team_in_report(self):
        from dota2cl.exceptions import ApiRequestError, NotFoundError
        from dota2cl.reporter import TopTeamsReport
        _history = "2025-02-21T10:00:14Z"
        _client = mock.Mock()
        _client.get_pro_players.return_value = [
            {"personaname": "a", "team_id": 1,
             "full_history_time": _history},
            {"personaname": "b", "team_id": 2,
             "full_history_time": _history},
            {"personaname": "c", "team_id": 3,
             "full_history_time": _history},
        ]
        _details = {
            1: {"name": "Alpha", "wins": 10, "losses": 2, "rating": 1500},
            2: NotFoundError("Resource 'teams/2' not found"),
            3: ApiRequestError("Request failed with HTTP 500",
                               status_code=500),
        }

        def _get_team(team_id):
            _value = _details[team_id]
            if isinstance(_value, Exception):
                raise _value
            return _value

        _client.get_team_by_id.side_effect = _get_team
        _args = SimpleNamespace(output=io.StringIO(), throttle=False,
                                num_teams=5, preload_teams=False)
        _report = TopTeamsReport(_args, api_client=_client)
        with self.redirect_output():
            _report.generate_payload()

        _teams = {t["Team ID"]: t for t in _report.payload["top_teams"]}
        # All teams are in the report, including the failed ones
        self.assertEqual(set(_teams), {1, 2, 3})
        self.assertEqual(_teams[1]["Team Name"], "Alpha")
        self.assertEqual(_teams[1]["Wins"], 10)
        for _team_id in (2, 3):
            _team = _teams[_team_id]
            for _field in ("Team Name", "Wins", "Losses", "Rating"):
                self.assertIsNone(_team[_field], msg=(_team_id, _field))
            # Data that doesn't come from team details is still there
            self.assertEqual(len(_team["Players"]), 1)
            self.assertGreater(_team["Team Experience"], 0)

    def test_other_errors_are_not_hidden(self):
        # Only API request errors are turned into empty details
        from dota2cl.reporter import TopTeamsReport
        _client = mock.Mock()
        _client.get_pro_players.return_value = [
            {"personaname": "a", "team_id": 1,
             "full_history_time": "2025-02-21T10:00:14Z"}]
        _client.get_team_by_id.side_effect = KeyError("unexpected")
        _args = SimpleNamespace(output=io.StringIO(), throttle=False,
                                num_teams=5, preload_teams=False)
        with self.assertRaises(KeyError):
            with self.redirect_output():
                TopTeamsReport(_args, api_client=_client).generate_payload()


class TestReporterFormats(DotClientTestBase):
    """
    Report output formats and destinations.
    """
    _payload = {"top_teams": [{
        "Team Name": "<Alpha>", "Team ID": 1, "Wins": 0,
        "Losses": None, "Rating": 1500.5, "Team Experience": 86400 * 3,
        "Players": [{"Personaname": "p&1", "Player Experience": 86400,
                     "Country Code": "pe"}],
    }]}

    def _make_report(self, fmt="yaml", output=None, **kwargs):
        from dota2cl.reporter import TopTeamsReport
        _args = SimpleNamespace(
            output=io.StringIO() if output is None else output,
            format=fmt, throttle=False, num_teams=5, preload_teams=False)
        return TopTeamsReport(_args, api_client=mock.Mock(), **kwargs)

    def test_yaml_default(self):
        from dota2cl.reporter import TopTeamsReport
        _args = SimpleNamespace(output=io.StringIO(), throttle=False,
                                num_teams=5, preload_teams=False)
        _report = TopTeamsReport(_args, api_client=mock.Mock())
        _report.save_payload(self._payload)
        self.assertTrue(_report.output.getvalue().startswith("---"))

    def test_html_escaped_and_complete(self):
        _report = self._make_report("html")
        _report.save_payload(self._payload)
        _out = _report.output.getvalue()
        self.assertTrue(_out.startswith("<!DOCTYPE html>"))
        self.assertIn("&lt;Alpha&gt;", _out)
        self.assertIn("p&amp;1", _out)
        self.assertIn("<dd>0</dd>", _out)
        self.assertIn("<dd>—</dd>", _out)
        self.assertIn("3 days", _out)
        self.assertIn("grid-template-columns", _out)

    def test_html_no_teams(self):
        _report = self._make_report("html")
        _report.save_payload({"top_teams": []})
        self.assertIn("No teams found", _report.output.getvalue())

    def test_output_to_path(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as _dir:
            _path = os.path.join(_dir, "report.html")
            _report = self._make_report("html", output=_path)
            with self.redirect_output():
                _report.save_payload(self._payload)
            with open(_path, encoding="utf-8") as f:
                self.assertIn("&lt;Alpha&gt;", f.read())

    def test_output_to_stdout(self):
        import contextlib
        _out = io.StringIO()
        _report = self._make_report(output="-")
        with contextlib.redirect_stdout(_out):
            _report.save_payload(self._payload)
        self.assertIn("Team Name: <Alpha>", _out.getvalue())

    def test_html_not_supported(self):
        from dota2cl.reporter import DotaReporter

        class _Report(DotaReporter):
            def generate_payload(self):
                pass

        _args = SimpleNamespace(output=io.StringIO(), format="html",
                                throttle=False)
        with self.assertRaises(NotImplementedError):
            _Report(_args).save_payload({})

    def test_jinja2_matches_builtin(self):
        from dota2cl import reporter
        if reporter.jinja2 is None:
            self.skipTest("jinja2 is not installed")
        _builtin = self._make_report("html")
        _jinja = self._make_report("html", use_jinja2=True)
        self.assertTrue(_jinja.use_jinja2)
        for _payload in (self._payload, {"top_teams": []}):
            _strip = "".join
            self.assertEqual(
                _strip(_builtin.render(_payload).split()),
                _strip(_jinja.render(_payload).split()))

    def test_jinja2_missing_falls_back(self):
        from dota2cl import reporter
        with mock.patch.object(reporter, "jinja2", None):
            with self.redirect_output():
                _report = self._make_report("html", use_jinja2=True)
        self.assertFalse(_report.use_jinja2)
        _report.save_payload(self._payload)
        self.assertIn("&lt;Alpha&gt;", _report.output.getvalue())
