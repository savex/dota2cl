#    Author: Alex Savatieiev (a.savex@gmail.com)
#    July 2025
# Basic Test base class with all common functionality for all tests.
# This includes:
# - Safe import of modules and classes
# - Safe execution of functions and methods
# - Redirecting stdout and stderr to capture output for assertions
# - Saving and restoring command line arguments for tests that modify them

import contextlib
import importlib
import io
import os
import sys
import unittest
import logging

from copy import deepcopy

tests_dir = os.path.dirname(__file__)
tests_dir = os.path.normpath(tests_dir)
tests_dir = os.path.abspath(tests_dir)


class DotClientTestBase(unittest.TestCase):
    dummy_base_var = 0
    last_stderr = ""
    last_stdout = ""

    def _safe_import(self, _str):
        """
        Import a module by name, or a class if the name is dotted,
        e.g. 'json' or 'dota2cl.client.Dota2Client'.
        Returns (error message, imported object).
        """
        if "." not in _str:
            return self._safe_import_module(_str)
        else:
            return self._safe_import_class(_str)

    def _safe_import_class(self, _str):
        _module_name, _, _class_name = _str.rpartition(".")
        _import_msg, _module = self._safe_import_module(_module_name)
        if _import_msg:
            return _import_msg, None
        try:
            return "", getattr(_module, _class_name)
        except AttributeError as e:
            return str(e), None

    @staticmethod
    def _safe_import_module(_str):
        """
        Import a module, e.g. 'dota2cl.client', and return it.
        Returns (error message, module), the module is None on error.
        """
        _import_msg = ""
        _module = None

        try:
            _module = importlib.import_module(_str)
        except ImportError as e:
            _import_msg = str(e)

        return _import_msg, _module

    @staticmethod
    def _safe_run(_obj, *args, **kwargs):
        """
        Call _obj and catch any exception.
        Returns (result, error message), the result is None on error.
        """
        _r = None
        _m = ""
        try:
            _r = _obj(*args, **kwargs)
        except Exception as ex:
            _m = f"{_obj}: {type(ex).__name__}: {ex or '<no message>'}"
        return _r, _m

    def run_main(self, args_list):
        """
        Run the application with the given command line arguments.
        Returns the exit code, 0 if it finished without exiting.
        Note: a full run creates the log file, see setup_log_file().
        """
        from dota2cl.runner import run
        with self.save_arguments():
            with self.redirect_output():
                sys.argv = ["dota2cl"] + args_list
                try:
                    run()
                except SystemExit as e:
                    # sys.exit() and sys.exit(None) mean success
                    return e.code or 0
        return 0

    @contextlib.contextmanager
    def redirect_output(self):
        """
        Capture stdout and stderr, and turn off logging.
        Everything is restored, even if the block raises.
        """
        save_stdout = sys.stdout
        save_stderr = sys.stderr
        save_disable = logging.root.manager.disable
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        logging.disable(logging.CRITICAL)
        try:
            yield
        finally:
            sys.stdout = save_stdout
            sys.stderr = save_stderr
            logging.disable(save_disable)

    @contextlib.contextmanager
    def save_arguments(self):
        _argv = deepcopy(sys.argv)
        try:
            yield
        finally:
            sys.argv = _argv

    def _try_import(self, module_name):
        with self.redirect_output():
            _msg, _m = self._safe_import_module(module_name)

        self.assertEqual(
            len(_msg),
            0,
            "Error importing '{}': {}".format(
                module_name,
                _msg
            )
        )

        return _m
