import sys
from unittest import mock

from tests.test_base import DotClientTestBase


class TestArguments(DotClientTestBase):
    """
    Command line argument parsing.
    """
    def _parse(self, args_list):
        from dotclient.arguments import parse_args
        with mock.patch.object(sys, "argv", ["dotclient"] + args_list):
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
