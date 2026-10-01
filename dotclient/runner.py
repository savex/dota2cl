import os

from dotclient.arguments import parse_args
from dotclient.const import title, opendota_api_key_env_var
from dotclient.dota2cl import dota2cl
from dotclient.log import logger_cli, logger, set_log_level
from dotclient.reporter import topTeamsReport


def load_api_key(env_var: str | None) -> str | None:
    api_key = None
    if env_var is None:
        logger_cli.info(
            f"Using environment variable '{opendota_api_key_env_var}'")
        api_key = os.getenv(opendota_api_key_env_var)
        if api_key is None:
            logger_cli.warning(f"API key not found in environment variable "
                               f"'{opendota_api_key_env_var}'")
    return api_key


def run() -> None:
    args = parse_args()
    # Setting log levels befor any output happens,
    # so the log level is respected for all log messages
    set_log_level(logger, args.loglevel)
    set_log_level(logger_cli, args.cliloglevel)
    logger_cli.info(f"# Running {title}\n"
                    f"# Using log level '{args.loglevel}'\n"
                    f"# Using CLI log level '{args.cliloglevel}'")

    # Generate report
    topTeamsReport(
        args,
        api_client=dota2cl(
            trottle=args.trottle,
            api_key=load_api_key(opendota_api_key_env_var)
        )
    )()

    logger_cli.debug("...done")
    return
