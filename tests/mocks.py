#    Author: Alex Savatieiev (a.savex@gmail.com)
#    November 2025

import json
import os
import urllib.parse as urlparse

from requests.exceptions import HTTPError

from dotclient.const import opendota_api_base_url

from tests.test_base import tests_dir


# Prepare fake filenames and files
_res_dir = os.path.join(tests_dir, 'res')


# preload file from res
def load_from_res(_filename, mode='rt'):
    fake_file_path = os.path.join(_res_dir, _filename)
    _patch_buf = []
    with open(fake_file_path, mode) as _f:
        _patch_buf = _f.read()

    return _patch_buf


_handle_pro_players = urlparse.urljoin(
    opendota_api_base_url + "/", "proPlayers")
_handle_teams = urlparse.urljoin(opendota_api_base_url + "/", "teams")
_handle_team = urlparse.urljoin(opendota_api_base_url + "/", "teams/1")

_handle_map = {
    _handle_pro_players: "_fake_players.json",
    _handle_teams: "_fake_teams.json",
    _handle_team: "_fake_team.json"
}


class MockResponse:
    def __init__(self, _buffer: str | bytes | dict | None, status_code,
                 headers: dict | None = None):
        if _buffer is None:
            self._content = _buffer
            self._text = _buffer
            self._json = _buffer
        elif isinstance(_buffer, bytes):
            self._content = _buffer
            self._text = None
            self._json = None
        elif isinstance(_buffer, dict):
            _dumped = json.dumps(_buffer)
            self._content = _dumped
            self._text = _dumped
            self._json = _buffer
        else:
            self._content = _buffer
            self._text = _buffer
            self._json = None

        self.status_code = status_code
        self.headers = headers or {}
        self._reason = "OK" if self.status_code == 200 else "FAIL"

    @property
    def content(self) -> bytes | dict | str | None:
        return self._content

    @property
    def text(self) -> str | bytes | None:
        return self._text

    def json(self) -> dict | list | None:
        if not self._json:
            try:
                if self._text is None:
                    return None
                elif isinstance(self._text, bytes) or \
                        isinstance(self._text, str):
                    _j = json.loads(self._text)
                elif isinstance(self._text, list):
                    _j = self._text
                else:
                    raise Exception("Unsupported type for json parsing")
            except Exception:
                # requests raises JSONDecodeError, a ValueError subclass
                raise ValueError("Failed to create json {}".format(self.text))
            return _j
        else:
            return self._json

    @property
    def reason(self) -> str:
        return self._reason

    def ok(self):
        return True if self.status_code == 200 else False

    def cookies(self):
        return None

    def raise_for_status(self):
        if not self.ok():
            raise HTTPError(f"HTTP Error: {self.status_code} {self.reason}")


def mocked_requests_get(*args, **kwargs):
    if args[0] in _handle_map.keys():
        return MockResponse(
            json.loads(load_from_res(_handle_map[args[0]])), 200)
    elif args[0] == opendota_api_base_url:
        return MockResponse(
            json.loads(load_from_res("_fake_api_schema.json")), 200)

    return MockResponse(None, 404)
