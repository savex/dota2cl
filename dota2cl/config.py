#    Author: Alex Savatieiev (a.savex@gmail.com)
#    October 2026
# Application settings.
# Settings are applied in this order, each one overriding the previous:
#   application defaults < config file < environment variables
# Command line options override all of them, see arguments.py.
import configparser
import os
import shutil

from copy import deepcopy

from dota2cl.const import api_client_max_retries, \
    api_client_retry_backoff_sec, api_client_throttle_timeout_sec, \
    config_env_var, config_file_name, default_log_level, \
    default_num_teams, default_report_format, env_var_prefix, log_levels, \
    opendota_api_base_url, opendota_api_key_env_var, \
    report_formats, requests_timeout_sec, resource_cache_timeout_sec
from dota2cl.exceptions import ConfigError
from dota2cl.log import logger_cli

# Default config bundled with the package
package_config_path = os.path.join(os.path.dirname(__file__),
                                   config_file_name)
# Config folder on Linux-like systems
system_config_dir = "/etc"

# Application defaults. The type of each value is also the type
# that config file and environment variable values are converted to.
DEFAULTS: dict[str, dict] = {
    "api": {
        "base_url": opendota_api_base_url,
        "key": "",
        "timeout_sec": float(requests_timeout_sec),
        "throttle": False,
        "throttle_timeout_sec": float(api_client_throttle_timeout_sec),
        "max_retries": api_client_max_retries,
        "retry_backoff_sec": float(api_client_retry_backoff_sec),
        "cache_timeout_sec": float(resource_cache_timeout_sec),
    },
    "report": {
        "num_teams": default_num_teams,
        "preload_teams": False,
        "format": default_report_format,
    },
    "logging": {
        "file": "",
        "level": default_log_level,
        "cli_level": default_log_level,
    },
}


def is_linux_like() -> bool:
    return os.name == "posix"


def default_config_path() -> str:
    """
    On Linux-like systems the config is /etc/dota2cl.conf. If it is missing
    and /etc is writable, it is created from the bundled config. Otherwise
    the bundled config is used, as it is on all other systems.
    """
    if not is_linux_like():
        return package_config_path
    system_path = os.path.join(system_config_dir, config_file_name)
    if os.path.isfile(system_path):
        return system_path
    if os.access(system_config_dir, os.W_OK):
        try:
            shutil.copyfile(package_config_path, system_path)
            logger_cli.info(f"Created default config file '{system_path}'")
            return system_path
        except OSError as e:
            logger_cli.warning(
                f"Failed to create config file '{system_path}': {e}")
    return package_config_path


def env_var_name(section: str, key: str) -> str:
    return f"{env_var_prefix}_{section}_{key}".upper()


def _convert(value: str, default, name: str):
    """
    Convert a string value to the type of the default value.
    """
    # bool is a subclass of int, so it is checked first
    if isinstance(default, bool):
        _states = configparser.ConfigParser.BOOLEAN_STATES
        _value = value.strip().lower()
        if _value not in _states:
            raise ConfigError(f"'{name}' must be true or false, "
                              f"got '{value}'")
        return _states[_value]
    if isinstance(default, (int, float)):
        try:
            return type(default)(value)
        except ValueError:
            raise ConfigError(f"'{name}' must be a number, "
                              f"got '{value}'") from None
    return value.strip()


def _apply_config_file(settings: dict, path: str) -> None:
    parser = configparser.ConfigParser(interpolation=None)
    try:
        with open(path) as f:
            parser.read_file(f)
    except (OSError, configparser.Error) as e:
        raise ConfigError(
            f"Failed to read config file '{path}': {e}") from None
    for section in parser.sections():
        if section not in settings:
            logger_cli.warning(
                f"Unknown section [{section}] in '{path}', ignored")
            continue
        for key, value in parser.items(section):
            if key not in settings[section]:
                logger_cli.warning(
                    f"Unknown setting '{key}' in section [{section}] "
                    f"of '{path}', ignored")
                continue
            settings[section][key] = _convert(
                value, DEFAULTS[section][key], f"{section}.{key}")


def _apply_env(settings: dict, environ) -> None:
    # Kept for compatibility, DOTA2CL_API_KEY overrides it
    if environ.get(opendota_api_key_env_var):
        settings["api"]["key"] = environ[opendota_api_key_env_var].strip()
    for section, values in settings.items():
        for key in values:
            _name = env_var_name(section, key)
            if _name in environ:
                values[key] = _convert(
                    environ[_name], DEFAULTS[section][key], _name)


def _validate(settings: dict) -> None:
    if settings["report"]["num_teams"] < 1:
        raise ConfigError("'report.num_teams' must be at least 1")
    _format = settings["report"]["format"].lower()
    if _format not in report_formats:
        raise ConfigError(f"'report.format' must be one of "
                          f"{', '.join(report_formats)}, got '{_format}'")
    settings["report"]["format"] = _format
    for key in ("level", "cli_level"):
        _level = settings["logging"][key].upper()
        if _level not in log_levels:
            raise ConfigError(f"'logging.{key}' must be one of "
                              f"{', '.join(log_levels)}, got '{_level}'")
        settings["logging"][key] = _level
    for key, value in settings["api"].items():
        if not isinstance(value, bool) and \
                isinstance(value, (int, float)) and value < 0:
            raise ConfigError(f"'api.{key}' must not be negative")


def load_settings(config_path: str | None = None,
                  environ=None) -> tuple[dict, str]:
    """
    Load settings from the config file and environment variables.
    The config file is config_path, the DOTA2CL_CONFIG variable,
    or the default location, in this order.
    Returns the settings and the path of the config file used.
    Raises ConfigError for missing files and invalid values.
    """
    environ = os.environ if environ is None else environ
    config_path = config_path or environ.get(config_env_var)
    if config_path:
        if not os.path.isfile(config_path):
            raise ConfigError(f"Config file '{config_path}' not found")
    else:
        config_path = default_config_path()

    settings = deepcopy(DEFAULTS)
    _apply_config_file(settings, config_path)
    _apply_env(settings, environ)
    _validate(settings)
    return settings, config_path
