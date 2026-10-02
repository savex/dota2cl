#    Author: Alex Savatieiev (a.savex@gmail.com)
#    November 2025
from argparse import ArgumentParser, ArgumentTypeError, \
    BooleanOptionalAction, FileType
from sys import stdout

from dotclient import __version__
from dotclient.config import DEFAULTS
from dotclient.const import config_env_var, config_file_name, log_levels


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


def parse_config_path(argv: list[str] | None = None) -> str | None:
    """
    Get only the --config option from command line.
    Settings must be loaded before the full parser is built,
    as they provide its defaults.
    """
    parser = ArgumentParser(add_help=False)
    parser.add_argument("--config")
    known, _ = parser.parse_known_args(argv)
    return known.config


def parse_args(settings: dict | None = None,
               argv: list[str] | None = None):
    """
    Retrieve args from command line.
    Defaults come from settings, so the options given on
    command line override the config file and environment.
    """
    settings = settings or DEFAULTS
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
    # Handled by parse_config_path(), listed here for help output
    parser.add_argument(
        "--config",
        metavar="PATH",
        help=f"Config file. Can also be set with {config_env_var}. "
             f"(default: /etc/{config_file_name} on Linux-like systems, "
             "otherwise the one bundled with the package)",
    )
    parser.add_argument(
        "-n",
        "--num-teams",
        type=positive_int,
        default=settings["report"]["num_teams"],
        help="number of teams in output (default: %(default)s)",
    )
    parser.add_argument(
        "-l",
        "--loglevel",
        choices=log_levels,
        default=settings["logging"]["level"],
        help="Only write internal log messages of this severity or above "
             "to the log file. Console messages are always copied to the "
             "log file as well. (default: %(default)s)",
    )
    # to have a flexible way of showing or not showing debug logs in CLI
    parser.add_argument(
        "--cliloglevel",
        choices=log_levels,
        default=settings["logging"]["cli_level"],
        help="Only print console messages of this severity or above. "
             "Writes to stderr. (default: %(default)s)",
    )
    # Causes reported to preload whole teams data from API,
    # so the team id can be looked up by name instead of id.
    # This is useful for players with team_id == 0, but it can
    # be slow if there are many teams.
    # --no-preload-teams turns off a value enabled in the config file
    parser.add_argument(
        "--preload-teams",
        action=BooleanOptionalAction,
        default=settings["report"]["preload_teams"],
        help="Preload teams data from API (default: %(default)s)",
    )
    # To avoid hitting API rate limits, enable request throttle.
    # The wait time is set with api.throttle_timeout_sec in the config.
    parser.add_argument(
        "--throttle",
        action=BooleanOptionalAction,
        default=settings["api"]["throttle"],
        help="Enable request throttling to avoid hitting API rate limits "
             "(default: %(default)s)",
    )
    return parser.parse_args(argv)
