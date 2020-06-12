import logging

logger = logging.getLogger("manage_bgp")
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler("log.txt")

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)

logger.addHandler(fh)


def logwrap(pre, post):
    def decorate(func):
        def call(*args, **kwargs):
            pre(func)
            result = func(*args, **kwargs)
            post(func)
            return result
        return call
    return decorate


def entering(func):
    logger.debug("Start %s", func.__name__)


def exiting(func):
    logger.debug("End  %s", func.__name__)
