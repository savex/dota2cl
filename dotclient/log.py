#    Author: Alex Savatieiev (a.savex@gmail.com)
#    Copyright 2019-2025

# usage:
# logger - log file class, with date and etc
# logger_cli - class for output to console and logger class

import logging
import os

from dotclient.const import title
from dotclient.utils import secrets_filter

pkg_dir = os.path.dirname(__file__)
pkg_dir = os.path.join(pkg_dir, os.pardir)
pkg_dir = os.path.normpath(pkg_dir)
pkg_dir = os.path.abspath(pkg_dir)


def color_me(color):
    RESET_SEQ = "\033[0m"
    COLOR_SEQ = "\033[1;%dm"

    color_seq = COLOR_SEQ % (30 + color)

    def closure(msg):
        return color_seq + msg + RESET_SEQ
    return closure


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
        if levelname in self.colors:
            record.levelname = self.colors[levelname](prn_name)
        else:
            record.levelname = prn_name

        # super doesn't work here in 2.6 O_o
        res = logging.Formatter.format(self, record)

        # res = super(ColoredFormatter, self).format(record)

        # restore record, as it will be used by other formatters
        record.__dict__ = orig
        return res


def setup_loggers(name, def_level=logging.DEBUG, log_fname=None):

    # Stream Handler
    sh = logging.StreamHandler()
    sh.setLevel(def_level)
    log_format = '%(message)s'
    colored_formatter = ColoredFormatter(log_format, datefmt="%H:%M:%S")
    sh.setFormatter(colored_formatter)
    sh.addFilter(secrets_filter)

    # File handler
    if log_fname is not None:
        fh = logging.FileHandler(log_fname)
        log_format = '%(asctime)s - %(levelname)8s - %(name)-15s - %(message)s'
        formatter = logging.Formatter(log_format, datefmt="%H:%M:%S")
        fh.setFormatter(formatter)
        fh.setLevel(logging.DEBUG)
        fh.addFilter(secrets_filter)
    else:
        fh = None

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    if len(logger.handlers) == 0 and fh is not None:
        logger.addHandler(fh)
    logger.propagate = False

    logger_cli = logging.getLogger(name + ".cli")
    logger_cli.setLevel(logging.INFO)
    if len(logger_cli.handlers) == 0:
        logger_cli.addHandler(sh)

    return logger, logger_cli


def set_log_level(mylogger, log_level_name) -> None:
    mylogger.setLevel(log_level_name)
    return


# init instances of logger to be used by all other modules
logger, logger_cli = setup_loggers(
    title,
    log_fname=os.path.join(
        pkg_dir,
        os.getenv('LOGFILE', title+'.log')
    )
)
