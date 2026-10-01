#    Author: Alex Savatieiev (a.savex@gmail.com)
#    November 2025
from argparse import ArgumentParser, FileType
from sys import stdout


def parse_args():
    """
    Retrieve args from command line.
    """
    parser = ArgumentParser(
        description="Find the DOTA 2 teams with the most combined player *experience",  # noqa: E501
        epilog="*Experience is defined as the length of a player's recorded history.",  # noqa: E501
    )
    parser.add_argument(
        "output", type=FileType("w"), nargs="?", default=stdout
    )
    parser.add_argument(
        "-n",
        "--num-teams",
        type=int,
        default=5,
        help="number of teams in output",
    )
    parser.add_argument(
        "-l",
        "--loglevel",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="WARNING",
        help="Only output log messages of this severity or above. "
             "Writes to stderr. (default: %(default)s)",
    )
    # to have a flexible way of showing or not showing debug logs in CLI
    parser.add_argument(
        "--cliloglevel",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="WARNING",
        help="Only output log messages of this severity or above. "
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
    # To avoid hitting API rate limits, enable request trottle
    # So far it is hardcoded to 1 second between requests, but
    # it can be made configurable in the future.
    parser.add_argument(
        "--trottle",
        action="store_true",
        help="Enable request trottling to avoid hitting API rate limits",
    )
    return parser.parse_args()
