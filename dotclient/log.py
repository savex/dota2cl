#    Author: Alex Savatieiev (a.savex@gmail.com)
#    Copyright 2019-2025

# usage:
# logger - log file class, with date and etc
# logger_cli - class for output to console and logger class

import logging
import os
import sys

from dotclient.const import app_name, log_file_name, title
from dotclient.utils import secrets_filter


def color_me(color):
    RESET_SEQ = "\033[0m"
    COLOR_SEQ = "\033[1;%dm"

    color_seq = COLOR_SEQ % (30 + color)

    def closure(msg):
        return color_seq + msg + RESET_SEQ
    return closure


def stream_supports_color(stream) -> bool:
    """
    Escape codes are only useful on a terminal. Setting NO_COLOR
    (https://no-color.org) or TERM=dumb turns them off.
    """
    if os.getenv("NO_COLOR") or os.getenv("TERM") == "dumb":
        return False
    isatty = getattr(stream, "isatty", None)
    try:
        return bool(isatty and isatty())
    except ValueError:
        # Closed stream
        return False


class ColoredFormatter(logging.Formatter):
    BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

    colors = {
        'INFO': color_me(WHITE),
        'WARNING': color_me(YELLOW),
        'DEBUG': color_me(BLUE),
        'CRITICAL': color_me(YELLOW),
        'ERROR': color_me(RED)
    }

    def __init__(self, msg, use_color=True, datefmt=None):
        logging.Formatter.__init__(self, msg, datefmt=datefmt)
        self.use_color = use_color

    def format(self, record):
        orig = record.__dict__
        record.__dict__ = record.__dict__.copy()
        levelname = record.levelname

        prn_name = levelname + ' ' * (8 - len(levelname))
        if self.use_color and levelname in self.colors:
            record.levelname = self.colors[levelname](prn_name)
        else:
            record.levelname = prn_name

        # super doesn't work here in 2.6 O_o
        res = logging.Formatter.format(self, record)

        # res = super(ColoredFormatter, self).format(record)

        # restore record, as it will be used by other formatters
        record.__dict__ = orig
        return res


def setup_loggers(name, def_level=logging.DEBUG):

    # Stream Handler
    sh = logging.StreamHandler()
    sh.setLevel(def_level)
    log_format = '%(message)s'
    colored_formatter = ColoredFormatter(
        log_format,
        use_color=stream_supports_color(sh.stream),
        datefmt="%H:%M:%S")
    sh.setFormatter(colored_formatter)
    sh.addFilter(secrets_filter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    # File handler is added later by setup_log_file().
    # Until then, keep messages from going to stderr via
    # logging's last resort handler.
    if len(logger.handlers) == 0:
        logger.addHandler(logging.NullHandler())
    logger.propagate = False

    logger_cli = logging.getLogger(name + ".cli")
    logger_cli.setLevel(logging.INFO)
    if len(logger_cli.handlers) == 0:
        logger_cli.addHandler(sh)

    return logger, logger_cli


def user_cache_dir() -> str:
    """
    Per-user cache folder for the application.
    """
    if sys.platform == "win32":
        _base = os.getenv("LOCALAPPDATA") or \
            os.path.expanduser(os.path.join("~", "AppData", "Local"))
    elif sys.platform == "darwin":
        _base = os.path.expanduser(os.path.join("~", "Library", "Caches"))
    else:
        _base = os.getenv("XDG_CACHE_HOME") or \
            os.path.expanduser(os.path.join("~", ".cache"))
    return os.path.join(_base, app_name)


def setup_log_file(log_fname: str | None = None) -> str | None:
    """
    Start writing the log file.
    Without a path, the log goes to the user cache folder, or to the
    current folder if the cache folder can't be used.
    Returns the log file path, or None if no log file could be opened.
    """
    if log_fname:
        _candidates = [log_fname]
    else:
        _candidates = [os.path.join(user_cache_dir(), log_file_name),
                       os.path.join(os.getcwd(), log_file_name)]

    for _path in _candidates:
        _path = os.path.abspath(os.path.expanduser(_path))
        try:
            os.makedirs(os.path.dirname(_path), exist_ok=True)
            fh = logging.FileHandler(_path)
        except OSError as e:
            logger_cli.warning(f"Can't write log file '{_path}': {e}")
            continue
        log_format = '%(asctime)s - %(levelname)8s - %(name)-15s - %(message)s'
        fh.setFormatter(logging.Formatter(log_format, datefmt="%H:%M:%S"))
        fh.setLevel(logging.DEBUG)
        fh.addFilter(secrets_filter)
        # Replace the file handler if this is called again
        for _handler in list(logger.handlers):
            if isinstance(_handler, (logging.FileHandler,
                                     logging.NullHandler)):
                logger.removeHandler(_handler)
                _handler.close()
        logger.addHandler(fh)
        return _path

    logger_cli.warning("Log file is disabled")
    return None


def set_log_level(mylogger, log_level_name) -> None:
    mylogger.setLevel(log_level_name)
    return


# init instances of logger to be used by all other modules
# The log file is not created here, it is opened in run()
logger, logger_cli = setup_loggers(title)
