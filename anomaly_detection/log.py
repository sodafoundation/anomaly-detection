# Copyright 2019 The OpenSDS Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import inspect
import logging
import logging.handlers
import os
import platform
import sys

try:
    import syslog
except ImportError:
    syslog = None
from anomaly_detection import units

CRITICAL = logging.CRITICAL
FATAL = logging.FATAL
ERROR = logging.ERROR
WARNING = logging.WARNING
WARN = logging.WARNING
INFO = logging.INFO
DEBUG = logging.DEBUG
NOTSET = logging.NOTSET
AUDIT = logging.INFO + 1
TRACE = 5

logging.addLevelName(TRACE, 'TRACE')

LOG_ROTATE_INTERVAL_MAPPING = {
    'seconds': 's',
    'minutes': 'm',
    'hours': 'h',
    'days': 'd',
    'weekday': 'w',
    'midnight': 'midnight'
}
_LOG_FILE = "anomaly_detection.log"


class Config(object):
    log_rotate_interval_type = "weekday"
    log_rotate_interval = 4
    max_logfile_count = 10
    max_logfile_size_mb = 200
    log_rotation_type = "interval"
    log_file = None
    log_dir = None
    log_date_format = "%Y-%m-%d %H:%M:%S"
    logging_default_format_string = \
        "%(asctime)s - %(levelname)s - %(filename)s[:%(lineno)d] - %(message)s"
    debug = True
    use_stderr = None
    use_eventlog = None


class ColorHandler(logging.StreamHandler):
    """Log handler that sets the 'color' key based on the level

    To use, include a '%(color)s' entry in the logging_context_format_string.
    There is also a '%(reset_color)s' key that can be used to manually reset
    the color within a log line.
    """
    LEVEL_COLORS = {
        TRACE: '\033[00;35m',  # MAGENTA
        logging.DEBUG: '\033[00;32m',  # GREEN
        logging.INFO: '\033[00;36m',  # CYAN
        AUDIT: '\033[01;36m',  # BOLD CYAN
        logging.WARN: '\033[01;33m',  # BOLD YELLOW
        logging.ERROR: '\033[01;31m',  # BOLD RED
        logging.CRITICAL: '\033[01;31m',  # BOLD RED
    }

    def format(self, record):
        record.color = self.LEVEL_COLORS[record.levelno]
        record.reset_color = '\033[00m'
        return logging.StreamHandler.format(self, record) + record.reset_color


class BaseLoggerAdapter(logging.LoggerAdapter):

    warn = logging.LoggerAdapter.warning

    @property
    def handlers(self):
        return self.logger.handlers

    def trace(self, msg, *args, **kwargs):
        self.log(TRACE, msg, *args, **kwargs)


class KeywordArgumentAdapter(BaseLoggerAdapter):
    """Logger adapter to add keyword arguments to log record's extra data

    Keywords passed to the log call are added to the "extra"
    dictionary passed to the underlying logger so they are emitted
    with the log message and available to the format string.

    Special keywords:

    extra
      An existing dictionary of extra values to be passed to the
      logger. If present, the dictionary is copied and extended.
    resource
      A dictionary-like object containing a ``name`` key or ``type``
       and ``id`` keys.

    """

    def process(self, msg, kwargs):
        # Make a new extra dictionary combining the values we were
        # given when we were constructed and anything from kwargs.
        extra = {}
        extra.update(self.extra)
        if 'extra' in kwargs:
            extra.update(kwargs.pop('extra'))
        # Move any unknown keyword arguments into the extra
        # dictionary.
        for name in list(kwargs.keys()):
            if name == 'exc_info':
                continue
            extra[name] = kwargs.pop(name)
        # NOTE(dhellmann): The gap between when the adapter is called
        # and when the formatter needs to know what the extra values
        # are is large enough that we can't get back to the original
        # extra dictionary easily. We leave a hint to ourselves here
        # in the form of a list of keys, which will eventually be
        # attributes of the LogRecord processed by the formatter. That
        # allows the formatter to know which values were original and
        # which were extra, so it can treat them differently (see
        # JSONFormatter for an example of this). We sort the keys so
        # it is possible to write sane unit tests.
        extra['extra_keys'] = list(sorted(extra.keys()))
        # Place the updated extra values back into the keyword
        # arguments.
        kwargs['extra'] = extra

        # NOTE(jdg): We would like an easy way to add resource info
        # to logging, for example a header like 'volume-<uuid>'
        # Turns out Nova implemented this but it's Nova specific with
        # instance.  Also there's resource_uuid that's been added to
        # context, but again that only works for Instances, and it
        # only works for contexts that have the resource id set.
        resource = kwargs['extra'].get('resource', None)
        if resource:

            # Many OpenStack resources have a name entry in their db ref
            # of the form <resource_type>-<uuid>, let's just use that if
            # it's passed in
            if not resource.get('name', None):

                # For resources that don't have the name of the format we wish
                # to use (or places where the LOG call may not have the full
                # object ref, allow them to pass in a dict:
                # resource={'type': volume, 'id': uuid}

                resource_type = resource.get('type', None)
                resource_id = resource.get('id', None)

                if resource_type and resource_id:
                    kwargs['extra']['resource'] = ('[' + resource_type +
                                                   '-' + resource_id + '] ')
            else:
                # FIXME(jdg): Since the name format can be specified via conf
                # entry, we may want to consider allowing this to be configured
                # here as well
                kwargs['extra']['resource'] = ('[' + resource.get('name', '')
                                               + '] ')

        return msg, kwargs


def _find_facility(facility):
    # NOTE(jd): Check the validity of facilities at run time as they differ
    # depending on the OS and Python version being used.
    valid_facilities = [f for f in
                        ["LOG_KERN", "LOG_USER", "LOG_MAIL",
                         "LOG_DAEMON", "LOG_AUTH", "LOG_SYSLOG",
                         "LOG_LPR", "LOG_NEWS", "LOG_UUCP",
                         "LOG_CRON", "LOG_AUTHPRIV", "LOG_FTP",
                         "LOG_LOCAL0", "LOG_LOCAL1", "LOG_LOCAL2",
                         "LOG_LOCAL3", "LOG_LOCAL4", "LOG_LOCAL5",
                         "LOG_LOCAL6", "LOG_LOCAL7"]
                        if getattr(syslog, f, None)]

    facility = facility.upper()

    if not facility.startswith("LOG_"):
        facility = "LOG_" + facility

    if facility not in valid_facilities:
        raise TypeError('syslog facility must be one of: %s' %
                        ', '.join("'%s'" % fac
                                  for fac in valid_facilities))

    return getattr(syslog, facility)


def _get_binary_name():
    return os.path.basename(inspect.stack()[-1][1])


def _get_log_file_path(conf, binary=None):
    logfile = conf.log_file
    logdir = conf.log_dir

    if logfile and not logdir:
        return logfile

    if logfile and logdir:
        return os.path.join(logdir, logfile)

    if logdir:
        binary = binary or _get_binary_name()
        return '%s.log' % (os.path.join(logdir, binary),)

    return None


def _setup_logging_from_conf(conf, project, version):
    log_root = getLogger(None).logger

    # Remove all handlers
    for handler in list(log_root.handlers):
        log_root.removeHandler(handler)

    logpath = _get_log_file_path(conf)
    if logpath:
        # On Windows, in-use files cannot be moved or deleted.
        if conf.log_rotation_type.lower() == "interval":
            file_handler = logging.handlers.TimedRotatingFileHandler
            when = conf.log_rotate_interval_type.lower()
            interval_type = LOG_ROTATE_INTERVAL_MAPPING[when]
            # When weekday is configured, "when" has to be a value between
            # 'w0'-'w6' (w0 for Monday, w1 for Tuesday, and so on)'
            if interval_type == 'w':
                interval_type = interval_type + str(conf.log_rotate_interval)
            filelog = file_handler(logpath,
                                   when=interval_type,
                                   interval=conf.log_rotate_interval,
                                   backupCount=conf.max_logfile_count)
        elif conf.log_rotation_type.lower() == "size":
            file_handler = logging.handlers.RotatingFileHandler
            maxBytes = conf.max_logfile_size_mb * units.Mi
            filelog = file_handler(logpath,
                                   maxBytes=maxBytes,
                                   backupCount=conf.max_logfile_count)
        else:
            file_handler = logging.handlers.WatchedFileHandler
            filelog = file_handler(logpath)

        log_root.addHandler(filelog)

    if conf.use_stderr:
        streamlog = ColorHandler()
        log_root.addHandler(streamlog)

    if conf.use_eventlog:
        if platform.system() == 'Windows':
            eventlog = logging.handlers.NTEventLogHandler(project)
            log_root.addHandler(eventlog)
        else:
            raise RuntimeError("Windows Event Log is not available on this platform.")

    # if None of the above are True, then fall back to standard out
    if not logpath and not conf.use_stderr:
        # pass sys.stdout as a positional argument
        # python2.6 calls the argument strm, in 2.7 it's stream
        streamlog = ColorHandler(sys.stdout)
        log_root.addHandler(streamlog)

    _refresh_root_level(conf.debug)

    datefmt = conf.log_date_format
    for handler in log_root.handlers:
        handler.setFormatter(logging.Formatter(
            fmt="%(asctime)s - %(levelname)s - %(filename)s[:%(lineno)d] - %(message)s",
            datefmt=datefmt))


def _refresh_root_level(debug):
    """Set the level of the root logger.

    :param debug: If 'debug' is True, the level will be DEBUG.
     Otherwise the level will be INFO.
    """
    log_root = getLogger(None).logger
    if debug:
        log_root.setLevel(logging.DEBUG)
    else:
        log_root.setLevel(logging.INFO)


def _create_logging_excepthook(product_name):
    def logging_excepthook(exc_type, value, tb):
        extra = {'exc_info': (exc_type, value, tb)}
        getLogger(product_name).critical('Unhandled error', **extra)
    return logging_excepthook


_loggers = {}


def get_loggers():
    """Return a copy of the oslo loggers dictionary."""
    return _loggers.copy()


def getLogger(name=None, project='unknown', version='unknown'):
    """Build a logger with the given name.

    :param name: The name for the logger. This is usually the module
                 name, ``__name__``.
    :type name: string
    :param project: The name of the project, to be injected into log
                    messages. For example, ``'nova'``.
    :type project: string
    :param version: The version of the project, to be injected into log
                    messages. For example, ``'2014.2'``.
    :type version: string
    """

    if name not in _loggers:
        _loggers[name] = KeywordArgumentAdapter(logging.getLogger(name),
                                                {'project': project,
                                                 'version': version})
    return _loggers[name]


def setup(conf, product_name, version='unknown'):
    """Setup logging for the current application."""
    _setup_logging_from_conf(conf, product_name, version)
    sys.excepthook = _create_logging_excepthook(product_name)