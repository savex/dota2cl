import contextlib
import io
import sys
from unittest import mock

from tests.test_base import DotClientTestBase


class TestArguments(DotClientTestBase):
    """
    Command line argument parsing.
    """
    def _parse(self, args_list):
        from dota2cl.arguments import parse_args
        with mock.patch.object(sys, "argv", ["dota2cl"] + args_list):
            return parse_args()

    def test_defaults(self):
        _args = self._parse([])
        self.assertEqual(_args.num_teams, 5)
        self.assertFalse(_args.throttle)
        self.assertFalse(_args.preload_teams)

    def test_throttle_flag(self):
        self.assertTrue(self._parse(["--throttle"]).throttle)

    def test_num_teams_positive(self):
        self.assertEqual(self._parse(["-n", "3"]).num_teams, 3)
        for _bad in ("0", "-1", "abc"):
            with self.redirect_output():
                with self.assertRaises(SystemExit):
                    self._parse(["-n", _bad])

    def test_version_flag(self):
        from dota2cl import __version__
        _out = io.StringIO()
        with contextlib.redirect_stdout(_out):
            with self.assertRaises(SystemExit) as _exit:
                self._parse(["--version"])
        self.assertEqual(_exit.exception.code, 0)
        self.assertEqual(_out.getvalue().strip(), f"dota2cl {__version__}")

    def test_defaults_from_settings(self):
        from copy import deepcopy
        from dota2cl.arguments import parse_args
        from dota2cl.config import DEFAULTS
        _settings = deepcopy(DEFAULTS)
        _settings["report"]["num_teams"] = 8
        _settings["api"]["throttle"] = True
        _args = parse_args(_settings, argv=[])
        self.assertEqual(_args.num_teams, 8)
        self.assertTrue(_args.throttle)
        # Command line overrides settings
        _args = parse_args(_settings, argv=["-n", "2", "--no-throttle"])
        self.assertEqual(_args.num_teams, 2)
        self.assertFalse(_args.throttle)

    def test_config_path(self):
        from dota2cl.arguments import parse_config_path
        self.assertIsNone(parse_config_path(["-n", "3"]))
        self.assertEqual(
            parse_config_path(["-n", "3", "--config", "/tmp/x.conf"]),
            "/tmp/x.conf")
