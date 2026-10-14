from townplanning.core.logging import (
    configure_logging,
)


def test_logging():

    logger = configure_logging("INFO")

    logger.info("Logger OK")