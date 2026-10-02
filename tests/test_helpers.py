import logging
import sys

from tests.test_base import DotClientTestBase


class TestBaseHelpers(DotClientTestBase):
    """
    Helpers in DotClientTestBase.
    """
    def test_safe_run_success(self):
        self.assertEqual(self._safe_run(lambda x: x * 2, 4), (8, ""))

    def test_safe_run_catches_exception(self):
        def _fail():
            raise ValueError("bad value")
        _result, _msg = self._safe_run(_fail)
        self.assertIsNone(_result)
        self.assertIn("ValueError: bad value", _msg)

    def test_safe_import_module(self):
        _msg, _module = self._safe_import_module("json")
        self.assertEqual(_msg, "")
        self.assertEqual(_module.__name__, "json")

    def test_safe_import_missing_module(self):
        _msg, _module = self._safe_import_module("no_such_module_xyz")
        self.assertIsNone(_module)
        self.assertIn("no_such_module_xyz", _msg)

    def test_safe_import_class(self):
        _msg, _cls = self._safe_import("dota2cl.client.Dota2Client")
        self.assertEqual(_msg, "")
        self.assertEqual(_cls.__name__, "Dota2Client")
        _msg, _cls = self._safe_import("dota2cl.client.NoSuchClass")
        self.assertIsNone(_cls)
        self.assertIn("NoSuchClass", _msg)

    def test_redirect_output_restores_on_error(self):
        _stdout, _stderr = sys.stdout, sys.stderr
        _disabled = logging.root.manager.disable
        with self.assertRaises(RuntimeError):
            with self.redirect_output():
                raise RuntimeError("inside")
        self.assertIs(sys.stdout, _stdout)
        self.assertIs(sys.stderr, _stderr)
        # Logging is enabled again after the block
        self.assertEqual(logging.root.manager.disable, _disabled)

    def test_save_arguments_restores_on_error(self):
        _argv = list(sys.argv)
        with self.assertRaises(RuntimeError):
            with self.save_arguments():
                sys.argv = ["changed"]
                raise RuntimeError("inside")
        self.assertEqual(sys.argv, _argv)

    def test_run_main_exit_codes(self):
        # Both exit before the log file is created
        self.assertEqual(self.run_main(["--version"]), 0)
        self.assertEqual(self.run_main(["--config", "/no/such.conf"]), 2)
