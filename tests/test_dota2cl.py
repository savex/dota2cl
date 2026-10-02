import json
from unittest import mock

from tests.test_base import DotClientTestBase
from tests.mocks import MockResponse, mocked_requests_get, \
    _handle_pro_players, \
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
    def test_get_pro_players(self, mock_get):
        _m = self._try_import("dotclient.dota2cl")
        if _m is None:
            self.skipTest("dota2cl module not available")
        else:
            try:
                _dt2cl = _m.dota2cl.Dota2Client()
            except Exception as e:
                self.fail(f"Failed to initialize dota2cl client: {e}")
            else:
                _expected = json.loads(
                    load_from_res(_handle_map[_handle_pro_players]))
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
                    "Empty buffer returned by '_handle_pro_players'"
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
            _dt2cl = _m.dota2cl.Dota2Client()
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
            _dt2cl = _m.dota2cl.Dota2Client()
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

    @mock.patch(
        'requests.get',
        side_effect=mocked_requests_get
    )
    def test_invalid_endpoint_raises(self, mock_get):
        from dotclient.dota2cl import Dota2Client
        from dotclient.exceptions import InvalidEndpointError
        _dt2cl = Dota2Client()
        _calls = mock_get.call_count

        # Plain and paginated requests to an unknown endpoint must raise
        # instead of returning an error payload that looks like data
        with self.assertRaises(InvalidEndpointError):
            _dt2cl.get("noSuchEndpoint")
        with self.assertRaises(InvalidEndpointError):
            _dt2cl._get_cached_item("noSuchEndpoint", page_size=1000)

        # Nothing is sent to the API and nothing is cached
        self.assertEqual(mock_get.call_count, _calls)
        self.assertNotIn("noSuchEndpoint", _dt2cl._cache)


class TestDota2ClientErrors(DotClientTestBase):
    """
    Errors raised by the client for failed requests and bad responses.
    """
    _fake_key = "secret-key-123"

    def _make_client(self, **kwargs):
        from dotclient.dota2cl import Dota2Client
        with mock.patch('requests.get', side_effect=mocked_requests_get):
            return Dota2Client(**kwargs)

    def test_client_options(self):
        _dt2cl = self._make_client(
            timeout_sec=5, throttle_timeout_sec=0.5, max_retries=1,
            retry_backoff_sec=0.1, cache_timeout_sec=600)
        self.assertEqual(_dt2cl.timeout_sec, 5)
        self.assertEqual(_dt2cl.throttle_timeout_sec, 0.5)
        self.assertEqual(_dt2cl.max_retries, 1)
        self.assertEqual(_dt2cl.retry_backoff_sec, 0.1)
        self.assertEqual(_dt2cl.cache_request_timeout_sec, 600)
        with mock.patch('requests.get',
                        side_effect=mocked_requests_get) as _get:
            _dt2cl.get_pro_players()
        self.assertEqual(_get.call_args.kwargs["timeout"], 5)

    def test_schema_load_failure_disables_validation(self):
        from dotclient.dota2cl import Dota2Client
        from requests.exceptions import ConnectionError
        with mock.patch('requests.get', side_effect=ConnectionError("down")):
            with self.redirect_output():
                _dt2cl = Dota2Client()
        self.assertEqual(_dt2cl.schema, {})
        self.assertFalse(_dt2cl.rest_handle_validation)

    def test_not_found(self):
        from dotclient.exceptions import NotFoundError
        _dt2cl = self._make_client()
        with mock.patch('requests.get',
                        return_value=MockResponse(None, 404)):
            with self.assertRaises(NotFoundError) as ctx:
                _dt2cl.get("teams/999", id_name="team_id")
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.endpoint, "teams/999")

    def test_http_error(self):
        from dotclient.exceptions import ApiRequestError, NotFoundError
        _dt2cl = self._make_client()
        with mock.patch('requests.get',
                        return_value=MockResponse(None, 500)):
            with self.assertRaises(ApiRequestError) as ctx:
                _dt2cl.get("proPlayers")
        self.assertNotIsInstance(ctx.exception, NotFoundError)
        self.assertEqual(ctx.exception.status_code, 500)

    @mock.patch('dotclient.dota2cl.time.sleep')
    def test_rate_limit_retry_then_success(self, mock_sleep):
        _dt2cl = self._make_client()
        _responses = [
            MockResponse(None, 429, headers={"Retry-After": "5"}),
            MockResponse(None, 429),
            MockResponse([{"account_id": 1}], 200),
        ]
        with mock.patch('requests.get', side_effect=_responses):
            with self.redirect_output():
                _buf = _dt2cl.get("proPlayers")
        self.assertEqual(_buf, [{"account_id": 1}])
        # Retry-After header first, then exponential backoff
        self.assertEqual(
            [c.args[0] for c in mock_sleep.call_args_list],
            [5.0, _dt2cl.retry_backoff_sec * 2])

    @mock.patch('dotclient.dota2cl.time.sleep')
    def test_throttle_skips_first_request(self, mock_sleep):
        _dt2cl = self._make_client(throttle=True, throttle_timeout_sec=10)
        _ok = MockResponse([{"account_id": 1}], 200)
        with mock.patch('requests.get', return_value=_ok):
            with self.redirect_output():
                _dt2cl.get("proPlayers")
                # Nothing was requested before, so no wait
                mock_sleep.assert_not_called()
                _dt2cl.get("proPlayers")
        # Second request comes right after the first one
        mock_sleep.assert_called_once()
        self.assertAlmostEqual(mock_sleep.call_args.args[0], 10, delta=1)

    @mock.patch('dotclient.dota2cl.time.sleep')
    def test_throttle_uses_monotonic_clock(self, mock_sleep):
        # A wall clock change must not affect the wait time
        _dt2cl = self._make_client(throttle=True, throttle_timeout_sec=10)
        _ok = MockResponse([{"account_id": 1}], 200)
        with mock.patch('requests.get', return_value=_ok), \
                mock.patch('dotclient.dota2cl.time.monotonic',
                           side_effect=[100.0, 104.0, 110.0]):
            with self.redirect_output():
                _dt2cl.get("proPlayers")
                _dt2cl.get("proPlayers")
        mock_sleep.assert_called_once_with(6.0)

    @mock.patch('dotclient.dota2cl.time.sleep')
    def test_rate_limit_exhausted(self, mock_sleep):
        from dotclient.exceptions import RateLimitError
        _dt2cl = self._make_client()
        with mock.patch('requests.get',
                        return_value=MockResponse(None, 429)) as _get:
            with self.redirect_output():
                with self.assertRaises(RateLimitError) as ctx:
                    _dt2cl.get("proPlayers")
        self.assertEqual(_get.call_count, _dt2cl.max_retries + 1)
        self.assertEqual(ctx.exception.status_code, 429)

    def test_connection_error_hides_api_key(self):
        from dotclient.exceptions import ApiRequestError
        from requests.exceptions import ConnectionError
        _dt2cl = self._make_client(api_key=self._fake_key)
        _err = ConnectionError(
            f"Max retries exceeded with url: /api/proPlayers"
            f"?key={self._fake_key}")
        with mock.patch('requests.get', side_effect=_err):
            with self.assertRaises(ApiRequestError) as ctx:
                _dt2cl.get("proPlayers")
        self.assertNotIn(self._fake_key, str(ctx.exception))
        # Original exception is not shown in tracebacks
        self.assertTrue(ctx.exception.__suppress_context__)
        self.assertIsNone(ctx.exception.__cause__)

    def test_invalid_json(self):
        from dotclient.exceptions import InvalidResponseError
        _dt2cl = self._make_client()
        with mock.patch('requests.get',
                        return_value=MockResponse("<html>", 200)):
            with self.assertRaises(InvalidResponseError):
                _dt2cl.get("proPlayers")

    def test_paginated_non_list_response(self):
        from dotclient.exceptions import InvalidResponseError
        _dt2cl = self._make_client()
        with mock.patch('requests.get',
                        return_value=MockResponse({"rows": []}, 200)):
            with self.redirect_output():
                with self.assertRaises(InvalidResponseError):
                    _dt2cl.get_teams()
