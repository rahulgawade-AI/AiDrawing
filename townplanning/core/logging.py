from loguru import logger
import sys


def configure_logging(level="INFO"):

    logger.remove()

    logger.add(
        sys.stdout,
        level=level,
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    return logger
