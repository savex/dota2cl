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
        _m = self._try_import("dota2cl.client")
        if _m is None:
            self.skipTest("dota2cl module not available")
        else:
            try:
                _dt2cl = _m.Dota2Client()
            except Exception as e:
                self.fail(f"Failed to initialize dota2cl client: {e}")
            else:
                _expected = json.loads(
                    load_from_res(_handle_map[_handle_pro_players]))
                _errors = []

                # Call the method with patched data
                with self.redirect_output():
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
        _m = self._try_import("dota2cl.client")
        if _m is None:
            self.skipTest("dota2cl module not available")
        else:
            _dt2cl = _m.Dota2Client()
            _expected = json.loads(
                load_from_res(_handle_map[_handle_teams]))
            _errors = []

            # Call the method with patched data
            with self.redirect_output():
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
        _m = self._try_import("dota2cl.client")
        if _m is None:
            self.skipTest("dota2cl module not available")
        else:
            _dt2cl = _m.Dota2Client()
            _expected = json.loads(
                load_from_res(_handle_map[_handle_team]))
            _errors = []

            # Call the method with patched data
            with self.redirect_output():
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
        from dota2cl.client import Dota2Client
        from dota2cl.exceptions import InvalidEndpointError
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
        from dota2cl.client import Dota2Client
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
            with self.redirect_output():
                _dt2cl.get_pro_players()
        self.assertEqual(_get.call_args.kwargs["timeout"], 5)

    def test_schema_load_failure_disables_validation(self):
        from dota2cl.client import Dota2Client
        from requests.exceptions import ConnectionError
        with mock.patch('requests.get', side_effect=ConnectionError("down")):
            with self.redirect_output():
                _dt2cl = Dota2Client()
        self.assertEqual(_dt2cl.schema, {})
        self.assertFalse(_dt2cl.rest_handle_validation)

    def test_not_found(self):
        from dota2cl.exceptions import NotFoundError
        _dt2cl = self._make_client()
        with mock.patch('requests.get',
                        return_value=MockResponse(None, 404)):
            with self.assertRaises(NotFoundError) as ctx:
                _dt2cl.get("teams/999", id_name="team_id")
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.endpoint, "teams/999")

    def test_http_error(self):
        from dota2cl.exceptions import ApiRequestError, NotFoundError
        _dt2cl = self._make_client()
        with mock.patch('requests.get',
                        return_value=MockResponse(None, 500)):
            with self.assertRaises(ApiRequestError) as ctx:
                _dt2cl.get("proPlayers")
        self.assertNotIsInstance(ctx.exception, NotFoundError)
        self.assertEqual(ctx.exception.status_code, 500)

    @mock.patch('dota2cl.client.time.sleep')
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

    @mock.patch('dota2cl.client.time.sleep')
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

    @mock.patch('dota2cl.client.time.sleep')
    def test_throttle_uses_monotonic_clock(self, mock_sleep):
        # A wall clock change must not affect the wait time
        _dt2cl = self._make_client(throttle=True, throttle_timeout_sec=10)
        _ok = MockResponse([{"account_id": 1}], 200)
        with mock.patch('requests.get', return_value=_ok), \
                mock.patch('dota2cl.client.time.monotonic',
                           side_effect=[100.0, 104.0, 110.0]):
            with self.redirect_output():
                _dt2cl.get("proPlayers")
                _dt2cl.get("proPlayers")
        mock_sleep.assert_called_once_with(6.0)

    @mock.patch('dota2cl.client.time.sleep')
    def test_rate_limit_exhausted(self, mock_sleep):
        from dota2cl.exceptions import RateLimitError
        _dt2cl = self._make_client()
        with mock.patch('requests.get',
                        return_value=MockResponse(None, 429)) as _get:
            with self.redirect_output():
                with self.assertRaises(RateLimitError) as ctx:
                    _dt2cl.get("proPlayers")
        self.assertEqual(_get.call_count, _dt2cl.max_retries + 1)
        self.assertEqual(ctx.exception.status_code, 429)

    def test_connection_error_hides_api_key(self):
        from dota2cl.exceptions import ApiRequestError
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
        from dota2cl.exceptions import InvalidResponseError
        _dt2cl = self._make_client()
        with mock.patch('requests.get',
                        return_value=MockResponse("<html>", 200)):
            with self.assertRaises(InvalidResponseError):
                _dt2cl.get("proPlayers")

    def test_paginated_non_list_response(self):
        from dota2cl.exceptions import InvalidResponseError
        _dt2cl = self._make_client()
        with mock.patch('requests.get',
                        return_value=MockResponse({"rows": []}, 200)):
            with self.redirect_output():
                with self.assertRaises(InvalidResponseError):
                    _dt2cl.get_teams()


class TestDota2ClientCache(DotClientTestBase):
    """
    Response caching and cache expiry.
    """
    def _make_client(self, **kwargs):
        from dota2cl.client import Dota2Client
        with mock.patch('requests.get', side_effect=mocked_requests_get):
            return Dota2Client(**kwargs)

    def test_cached_data_reused_before_expiry(self):
        _dt2cl = self._make_client(cache_timeout_sec=60)
        with mock.patch.object(_dt2cl, "get",
                               return_value=[{"account_id": 1}]) as _get:
            with self.redirect_output():
                _first = _dt2cl.get_pro_players()
                _second = _dt2cl.get_pro_players()
        self.assertEqual(_get.call_count, 1)
        self.assertEqual(_first, _second)

    def test_expired_cache_returns_fresh_data(self):
        # Bug 3: data was fetched again after expiry,
        # but the old cached data was returned
        _dt2cl = self._make_client(cache_timeout_sec=60)
        _old, _new = [{"account_id": 1}], [{"account_id": 2}]
        with mock.patch.object(_dt2cl, "get",
                               side_effect=[_old, _new]) as _get:
            with self.redirect_output():
                self.assertEqual(_dt2cl.get_pro_players(), _old)
                # Make the cached entry older than the timeout
                _dt2cl._cache["proPlayers"]["timestamp"] -= 61
                self.assertEqual(_dt2cl.get_pro_players(), _new)
                # The fresh data is cached as well
                self.assertEqual(_dt2cl.get_pro_players(), _new)
        self.assertEqual(_get.call_count, 2)

    def test_cache_is_per_handle(self):
        _dt2cl = self._make_client()
        with mock.patch.object(_dt2cl, "get",
                               side_effect=[{"team_id": 1},
                                            {"team_id": 2}]) as _get:
            with self.redirect_output():
                self.assertEqual(_dt2cl.get_team_by_id(1), {"team_id": 1})
                self.assertEqual(_dt2cl.get_team_by_id(2), {"team_id": 2})
                self.assertEqual(_dt2cl.get_team_by_id(1), {"team_id": 1})
        self.assertEqual(_get.call_count, 2)


class TestDota2ClientPagination(DotClientTestBase):
    """
    Paginated requests collect all pages.
    """
    def _paginate(self, pages, page_size, api_key=None):
        """
        Run a paginated request where the API returns the given pages.
        Returns the collected data and the requested page numbers.
        """
        from dota2cl.client import Dota2Client
        with mock.patch('requests.get', side_effect=mocked_requests_get):
            _dt2cl = Dota2Client(api_key=api_key)
        _requested = []

        def _fake_get(url, params=None, **kwargs):
            _requested.append(dict(params))
            _page = params["page"]
            return MockResponse(pages[_page] if _page < len(pages) else [],
                                200)

        with mock.patch('requests.get', side_effect=_fake_get):
            with self.redirect_output():
                _data = _dt2cl._get_cached_item("teams", page_size=page_size)
        return _data, _requested

    def test_collects_all_pages(self):
        _pages = [[{"team_id": 1}, {"team_id": 2}],
                  [{"team_id": 3}, {"team_id": 4}],
                  [{"team_id": 5}]]
        _data, _requested = self._paginate(_pages, page_size=2)
        self.assertEqual([t["team_id"] for t in _data], [1, 2, 3, 4, 5])
        # Stops after the short page, no extra request
        self.assertEqual([p["page"] for p in _requested], [0, 1, 2])

    def test_stops_on_empty_page(self):
        # Item count is an exact multiple of the page size,
        # so only an empty page shows the end
        _pages = [[{"team_id": 1}, {"team_id": 2}],
                  [{"team_id": 3}, {"team_id": 4}]]
        _data, _requested = self._paginate(_pages, page_size=2)
        self.assertEqual(len(_data), 4)
        self.assertEqual([p["page"] for p in _requested], [0, 1, 2])

    def test_single_short_page(self):
        _data, _requested = self._paginate([[{"team_id": 1}]], page_size=2)
        self.assertEqual(_data, [{"team_id": 1}])
        self.assertEqual(len(_requested), 1)

    def test_api_key_sent_with_every_page(self):
        _pages = [[{"team_id": 1}, {"team_id": 2}], [{"team_id": 3}]]
        _, _requested = self._paginate(_pages, page_size=2,
                                       api_key="secret-key")
        self.assertEqual([p.get("key") for p in _requested],
                         ["secret-key", "secret-key"])
