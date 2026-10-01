#    Author: Alex Savatieiev (a.savex@gmail.com)
#    April-May 2023
import sys
import unittest

from unittest import TextTestResult, TextTestRunner
from tests.test_base import tests_dir


class MyTestResult(TextTestResult):
    # overide test name in output
    def getDescription(self, test):
        if self.descriptions and test.shortDescription():
            return "\n".join((str(test),
                              test.shortDescription()))  # type: ignore
        else:
            return f"{test.__class__.__module__}." \
                   f"{test.__class__.__name__}.{test._testMethodName}"


class MyTestRunner(TextTestRunner):
    resultclass = MyTestResult  # type: ignore


def _cleanup():
    pass


if __name__ == '__main__':
    # remove old files if exists
    _cleanup()

    # start tests
    suite = unittest.TestLoader().discover(tests_dir, "test_*", tests_dir)
    runner = MyTestRunner(verbosity=3)
    result = runner.run(suite)

    # cleanup after testrun
    _cleanup()

    # non-zero exit code so CI can detect failures
    sys.exit(not result.wasSuccessful())
