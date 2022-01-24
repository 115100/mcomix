# -*- coding: utf-8 -*-

""" Logging module for MComix. Provides a logger 'mcomix' with a few
pre-configured settings. Functions in this module are redirected to
this default logger. """

import sys
import logging
from logging import DEBUG, INFO, WARNING, ERROR


__all__ = ['debug', 'info', 'warning', 'error', 'setLevel',
           'DEBUG', 'INFO', 'WARNING', 'ERROR']

# Set up default logger.
__logger = logging.getLogger('mcomix')
__logger.setLevel(WARNING)
if not __logger.handlers:
    __handler = logging.StreamHandler(sys.stdout)
    __handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(threadName)s] %(levelname)s: %(message)s',
        '%H:%M:%S'))
    __logger.handlers = [ __handler ]

# The following functions direct all input to __logger.

debug = __logger.debug
info = __logger.info
warning = __logger.warning
error = __logger.error
setLevel = __logger.setLevel


# vim: expandtab:sw=4:ts=4
