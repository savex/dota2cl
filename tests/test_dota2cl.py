import json
from unittest import mock

from tests.test_base import DotClientTestBase
from tests.mocks import mocked_requests_get, _handle_proPlayers, \
    _handle_teams, _handle_team, _handle_map, load_from_res


class TestDota2Client(DotClientTestBase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @mock.patch(
        'requests.get',
        side_effect=mocked_requests_get
    )
    def test_get_proPlayers(self, mock_get):
        _m = self._try_import("dotclient.dota2cl")
        if _m is None:
            self.skipTest("dota2cl module not available")
        else:
            try:
                _dt2cl = _m.dota2cl.dota2cl()
            except Exception as e:
                self.fail(f"Failed to initialize dota2cl client: {e}")
            else:
                _expected = json.loads(
                    load_from_res(_handle_map[_handle_proPlayers]))
                _errors = []

                # Call the method with patched data
                _buf, _msg = self._safe_run(
                    _dt2cl.get_pro_players
                )
                if _msg:
                    _errors.append(_msg)

                self.assertNotEqual(
                    len(_buf),
                    0,
                    "Empty buffer returned by '_handle_proPlayers'"
                )
                self.assertEqual(
                    _buf,
                    _expected,
                    "Incorrect content returned by 'get_pro_players'"
                )

    @mock.patch(
        'requests.get',
        side_effect=mocked_requests_get
    )
    def test_get_teams(self, mock_get):
        _m = self._try_import("dotclient.dota2cl")
        if _m is None:
            self.skipTest("dota2cl module not available")
        else:
            _dt2cl = _m.dota2cl.dota2cl()
            _expected = json.loads(
                load_from_res(_handle_map[_handle_teams]))
            _errors = []

            # Call the method with patched data
            _buf, _msg = self._safe_run(
                _dt2cl.get_teams
            )
            if _msg:
                _errors.append(_msg)

            self.assertNotEqual(
                len(_buf),
                0,
                "Empty buffer returned by '_handle_teams'"
            )
            self.assertEqual(
                _buf,
                _expected,
                "Incorrect content returned by 'get_teams'"
            )

    @mock.patch(
        'requests.get',
        side_effect=mocked_requests_get
    )
    def test_get_team_by_id(self, mock_get):
        _m = self._try_import("dotclient.dota2cl")
        if _m is None:
            self.skipTest("dota2cl module not available")
        else:
            _dt2cl = _m.dota2cl.dota2cl()
            _expected = json.loads(
                load_from_res(_handle_map[_handle_team]))
            _errors = []

            # Call the method with patched data
            _buf, _msg = self._safe_run(
                _dt2cl.get_team_by_id,
                1
            )
            if _msg:
                _errors.append(_msg)

            self.assertNotEqual(
                len(_buf),
                0,
                "Empty buffer returned by '_handle_team'"
            )
            self.assertEqual(
                _buf,
                _expected,
                "Incorrect content returned by 'get_team_by_id'"
            )
