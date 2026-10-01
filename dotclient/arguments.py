#    Author: Alex Savatieiev (a.savex@gmail.com)
#    November 2025
from argparse import ArgumentParser, ArgumentTypeError, FileType
from sys import stdout

from dotclient import __version__

log_levels = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]


def positive_int(value: str) -> int:
    """
    Argparse type for integers greater than zero.
    """
    try:
        number = int(value)
    except ValueError:
        raise ArgumentTypeError(f"invalid int value: '{value}'")
    if number < 1:
        raise ArgumentTypeError(f"must be at least 1, got {number}")
    return number


def parse_args():
    """
    Retrieve args from command line.
    """
    parser = ArgumentParser(
        description="Find the DOTA 2 teams with the most combined player *experience",  # noqa: E501
        epilog="*Experience is defined as the length of a player's recorded history.",  # noqa: E501
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "output", type=FileType("w"), nargs="?", default=stdout
    )
    parser.add_argument(
        "-n",
        "--num-teams",
        type=positive_int,
        default=5,
        help="number of teams in output (default: %(default)s)",
    )
    parser.add_argument(
        "-l",
        "--loglevel",
        choices=log_levels,
        default="WARNING",
        help="Only write internal log messages of this severity or above "
             "to the log file. Console messages are always copied to the "
             "log file as well. (default: %(default)s)",
    )
    # to have a flexible way of showing or not showing debug logs in CLI
    parser.add_argument(
        "--cliloglevel",
        choices=log_levels,
        default="WARNING",
        help="Only print console messages of this severity or above. "
             "Writes to stderr. (default: %(default)s)",
    )
    # Causes reported to preload whole teams data from API,
    # so the team id can be looked up by name instead of id.
    # This is useful for players with team_id == 0, but it can
    # be slow if there are many teams.  # noqa: E501
    parser.add_argument(
        "--preload-teams",
        action="store_true",
        help="Preload teams data from API",
    )
    # To avoid hitting API rate limits, enable request throttle
    # So far it is hardcoded to 1 second between requests, but
    # it can be made configurable in the future.
    parser.add_argument(
        "--throttle",
        action="store_true",
        help="Enable request throttling to avoid hitting API rate limits",
    )
    return parser.parse_args()
