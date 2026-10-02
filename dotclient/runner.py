import sys

from dotclient import __version__
from dotclient.arguments import parse_args, parse_config_path
from dotclient.config import load_settings
from dotclient.const import title
from dotclient.dota2cl import Dota2Client
from dotclient.exceptions import ConfigError, DotClientError
from dotclient.log import logger_cli, logger, set_log_level, setup_log_file
from dotclient.reporter import TopTeamsReport


def run() -> None:
    # Settings are loaded first, as they are the defaults
    # for command line options
    try:
        settings, config_path = load_settings(parse_config_path())
    except ConfigError as e:
        logger_cli.error(f"Invalid configuration: {e}")
        sys.exit(2)
    args = parse_args(settings)

    log_path = setup_log_file(settings["logging"]["file"])
    # Logged before levels are applied, so every log file records the version
    logger.info(f"{title} version {__version__}")
    # Setting log levels befor any output happens,
    # so the log level is respected for all log messages
    set_log_level(logger, args.loglevel)
    set_log_level(logger_cli, args.cliloglevel)
    logger_cli.info(f"# Running {title} {__version__}\n"
                    f"# Using config file '{config_path}'\n"
                    f"# Using log file '{log_path}'\n"
                    f"# Using log level '{args.loglevel}'\n"
                    f"# Using CLI log level '{args.cliloglevel}'")

    api = settings["api"]
    if api["key"]:
        logger_cli.info("Using API key")
    else:
        logger_cli.warning("API key is not set, using anonymous access "
                           "(lower rate limits)")

    # Generate report
    try:
        TopTeamsReport(
            args,
            api_client=Dota2Client(
                api_key=api["key"] or None,
                throttle=args.throttle,
                base_url=api["base_url"],
                timeout_sec=api["timeout_sec"],
                throttle_timeout_sec=api["throttle_timeout_sec"],
                max_retries=api["max_retries"],
                retry_backoff_sec=api["retry_backoff_sec"],
                cache_timeout_sec=api["cache_timeout_sec"],
            )
        )()
    except DotClientError as e:
        logger_cli.error(f"Failed to generate report: {e}")
        sys.exit(1)

    logger_cli.debug("...done")
    return
