import logging
import os
import sys
import tempfile
from unittest import mock

from tests.test_base import DotClientTestBase


class TestConfig(DotClientTestBase):
    """
    Settings precedence: defaults < config file < environment.
    """
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def _write_config(self, text, name="dota2cl.conf"):
        _path = os.path.join(self.tmp_dir, name)
        with open(_path, "w") as f:
            f.write(text)
        return _path

    def _load(self, text="", environ=None):
        from dotclient.config import load_settings
        _path = self._write_config(text)
        with self.redirect_output():
            settings, _ = load_settings(_path, environ=environ or {})
        return settings

    def test_bundled_config_matches_defaults(self):
        # The shipped config documents every setting with its default value
        from dotclient.config import DEFAULTS, load_settings, \
            package_config_path
        settings, _path = load_settings(package_config_path, environ={})
        self.assertEqual(settings, DEFAULTS)

    def test_config_overrides_defaults(self):
        _settings = self._load(
            "[api]\nthrottle = yes\ncache_timeout_sec = 5\n"
            "[report]\nnum_teams = 10\n"
            "[logging]\nlevel = debug\n")
        self.assertTrue(_settings["api"]["throttle"])
        self.assertEqual(_settings["api"]["cache_timeout_sec"], 5.0)
        self.assertEqual(_settings["report"]["num_teams"], 10)
        self.assertEqual(_settings["logging"]["level"], "DEBUG")
        # Not set in the file, so the default is kept
        self.assertEqual(_settings["api"]["max_retries"], 3)

    def test_env_overrides_config(self):
        _settings = self._load(
            "[report]\nnum_teams = 10\n[api]\nkey = from_file\n",
            environ={"DOTA2CL_REPORT_NUM_TEAMS": "7",
                     "DOTA2CL_API_THROTTLE": "true"})
        self.assertEqual(_settings["report"]["num_teams"], 7)
        self.assertTrue(_settings["api"]["throttle"])
        self.assertEqual(_settings["api"]["key"], "from_file")

    def test_api_key_env_vars(self):
        _config = "[api]\nkey = from_file\n"
        _settings = self._load(
            _config, environ={"OPENDOTA_API_KEY": "opendota"})
        self.assertEqual(_settings["api"]["key"], "opendota")
        _settings = self._load(
            _config, environ={"OPENDOTA_API_KEY": "opendota",
                              "DOTA2CL_API_KEY": "dota2cl"})
        self.assertEqual(_settings["api"]["key"], "dota2cl")

    def test_config_env_var_selects_file(self):
        from dotclient.config import load_settings
        _path = self._write_config("[report]\nnum_teams = 9\n", "other.conf")
        _settings, _used = load_settings(
            environ={"DOTA2CL_CONFIG": _path})
        self.assertEqual(_used, _path)
        self.assertEqual(_settings["report"]["num_teams"], 9)

    def test_invalid_values_raise(self):
        from dotclient.exceptions import ConfigError
        for _text in ("[api]\nthrottle = maybe\n",
                      "[api]\nmax_retries = many\n",
                      "[api]\ntimeout_sec = -1\n",
                      "[report]\nnum_teams = 0\n",
                      "[logging]\nlevel = LOUD\n",
                      "not an ini file\n"):
            with self.assertRaises(ConfigError, msg=_text):
                self._load(_text)
        with self.assertRaises(ConfigError):
            self._load(environ={"DOTA2CL_REPORT_NUM_TEAMS": "ten"})

    def test_missing_config_file_raises(self):
        from dotclient.config import load_settings
        from dotclient.exceptions import ConfigError
        with self.assertRaises(ConfigError):
            load_settings(os.path.join(self.tmp_dir, "missing.conf"),
                          environ={})

    def test_unknown_settings_ignored(self):
        _settings = self._load("[api]\ncolour = blue\n[extra]\na = 1\n")
        self.assertNotIn("colour", _settings["api"])
        self.assertNotIn("extra", _settings)


class TestConfigLocation(DotClientTestBase):
    """
    Default config file location.
    """
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.etc_dir = self._tmp.name
        self._patch = mock.patch("dotclient.config.system_config_dir",
                                 self.etc_dir)
        self._patch.start()

    def tearDown(self):
        self._patch.stop()
        self._tmp.cleanup()

    def _default_path(self, linux_like=True):
        from dotclient import config
        with mock.patch.object(config, "is_linux_like",
                               return_value=linux_like):
            with self.redirect_output():
                return config.default_config_path()

    def test_linux_creates_system_config(self):
        from dotclient.config import package_config_path
        _path = self._default_path()
        self.assertEqual(_path, os.path.join(self.etc_dir, "dota2cl.conf"))
        with open(_path) as f, open(package_config_path) as b:
            self.assertEqual(f.read(), b.read())

    def test_linux_keeps_existing_system_config(self):
        _path = os.path.join(self.etc_dir, "dota2cl.conf")
        with open(_path, "w") as f:
            f.write("[report]\nnum_teams = 2\n")
        self.assertEqual(self._default_path(), _path)
        with open(_path) as f:
            self.assertEqual(f.read(), "[report]\nnum_teams = 2\n")

    def test_linux_unwritable_uses_bundled_config(self):
        from dotclient.config import package_config_path
        with mock.patch("dotclient.config.os.access", return_value=False):
            self.assertEqual(self._default_path(), package_config_path)
        self.assertEqual(os.listdir(self.etc_dir), [])

    def test_other_systems_use_bundled_config(self):
        from dotclient.config import package_config_path
        self.assertEqual(self._default_path(linux_like=False),
                         package_config_path)
        self.assertEqual(os.listdir(self.etc_dir), [])


class TestLogFile(DotClientTestBase):
    """
    Log file placement.
    """
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = self._tmp.name

    def tearDown(self):
        from dotclient.log import logger
        for _handler in list(logger.handlers):
            if isinstance(_handler, logging.FileHandler):
                logger.removeHandler(_handler)
                _handler.close()
        self._tmp.cleanup()

    def _file_handlers(self):
        from dotclient.log import logger
        return [h for h in logger.handlers
                if isinstance(h, logging.FileHandler)]

    def test_no_log_file_on_import(self):
        self.assertEqual(self._file_handlers(), [])

    def test_default_log_in_user_cache_dir(self):
        from dotclient import log
        _cache = os.path.join(self.tmp_dir, "cache", "dota2cl")
        with mock.patch.object(log, "user_cache_dir", return_value=_cache):
            _path = log.setup_log_file()
        self.assertEqual(_path, os.path.join(_cache, "dota2cl.log"))
        self.assertTrue(os.path.isfile(_path))
        self.assertEqual(len(self._file_handlers()), 1)

    def test_falls_back_to_current_dir(self):
        from dotclient import log
        # A file where the cache folder should be makes it unusable
        _blocker = os.path.join(self.tmp_dir, "blocker")
        open(_blocker, "w").close()
        _cwd = os.path.join(self.tmp_dir, "cwd")
        os.mkdir(_cwd)
        with mock.patch.object(log, "user_cache_dir",
                               return_value=os.path.join(_blocker, "x")), \
                mock.patch.object(log.os, "getcwd", return_value=_cwd):
            with self.redirect_output():
                _path = log.setup_log_file()
        self.assertEqual(_path, os.path.join(_cwd, "dota2cl.log"))

    def test_configured_log_file(self):
        from dotclient.log import setup_log_file
        _path = os.path.join(self.tmp_dir, "logs", "app.log")
        self.assertEqual(setup_log_file(_path), _path)
        # Calling again replaces the handler instead of adding one
        setup_log_file(_path)
        self.assertEqual(len(self._file_handlers()), 1)

    def test_user_cache_dir_per_platform(self):
        from dotclient import log
        with mock.patch.object(sys, "platform", "linux"), \
                mock.patch.dict(os.environ, {"XDG_CACHE_HOME": "/xdg"}):
            self.assertEqual(log.user_cache_dir(),
                             os.path.join("/xdg", "dota2cl"))
        with mock.patch.object(sys, "platform", "darwin"):
            self.assertTrue(log.user_cache_dir().endswith(
                os.path.join("Library", "Caches", "dota2cl")))
        with mock.patch.object(sys, "platform", "win32"), \
                mock.patch.dict(os.environ, {"LOCALAPPDATA": "/local"}):
            self.assertEqual(log.user_cache_dir(),
                             os.path.join("/local", "dota2cl"))


class TestColoredOutput(DotClientTestBase):
    """
    Escape codes are used only when the output is a terminal.
    """
    class _Stream:
        def __init__(self, tty):
            self._tty = tty

        def isatty(self):
            return self._tty

    def _format(self, use_color):
        from dotclient.log import ColoredFormatter
        _formatter = ColoredFormatter("%(levelname)s%(message)s",
                                      use_color=use_color)
        _record = logging.LogRecord("t", logging.ERROR, "", 0, "msg",
                                    None, None)
        return _formatter.format(_record)

    def test_formatter_respects_use_color(self):
        self.assertIn("\033[", self._format(True))
        self.assertEqual(self._format(False), "ERROR   msg")

    def test_color_only_on_terminal(self):
        from dotclient.log import stream_supports_color
        with mock.patch.dict(os.environ, clear=True):
            self.assertTrue(stream_supports_color(self._Stream(True)))
            self.assertFalse(stream_supports_color(self._Stream(False)))
            # Streams without isatty, e.g. some wrappers
            self.assertFalse(stream_supports_color(object()))

    def test_color_disabled_by_env(self):
        from dotclient.log import stream_supports_color
        for _env in ({"NO_COLOR": "1"}, {"TERM": "dumb"}):
            with mock.patch.dict(os.environ, _env, clear=True):
                self.assertFalse(stream_supports_color(self._Stream(True)),
                                 msg=_env)
