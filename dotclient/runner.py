import os
import sys

from dotclient import __version__
from dotclient.arguments import parse_args
from dotclient.const import title, opendota_api_key_env_var
from dotclient.dota2cl import dota2cl
from dotclient.exceptions import DotClientError
from dotclient.log import logger_cli, logger, set_log_level
from dotclient.reporter import topTeamsReport


def load_api_key(env_var: str = opendota_api_key_env_var) -> str | None:
    api_key = (os.getenv(env_var) or "").strip()
    if not api_key:
        logger_cli.warning(f"API key not found in environment variable "
                           f"'{env_var}', using anonymous access "
                           "(lower rate limits)")
        return None
    logger_cli.info(f"Using API key from environment variable '{env_var}'")
    return api_key


def run() -> None:
    args = parse_args()
    # Logged before levels are applied, so every log file records the version
    logger.info(f"{title} version {__version__}")
    # Setting log levels befor any output happens,
    # so the log level is respected for all log messages
    set_log_level(logger, args.loglevel)
    set_log_level(logger_cli, args.cliloglevel)
    logger_cli.info(f"# Running {title} {__version__}\n"
                    f"# Using log level '{args.loglevel}'\n"
                    f"# Using CLI log level '{args.cliloglevel}'")

    # Generate report
    try:
        topTeamsReport(
            args,
            api_client=dota2cl(
                throttle=args.throttle,
                api_key=load_api_key()
            )
        )()
    except DotClientError as e:
        logger_cli.error(f"Failed to generate report: {e}")
        sys.exit(1)

    logger_cli.debug("...done")
    return
