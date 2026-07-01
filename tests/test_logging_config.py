import logging

from news_agent.logging_config import configure_logging


def _reset_logger() -> logging.Logger:
    logger = logging.getLogger("news_agent")
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)
    return logger


def test_configure_logging_verbose_sets_info_level():
    logger = _reset_logger()

    configure_logging(verbose=True)

    assert logger.level == logging.INFO
    assert len(logger.handlers) == 1


def test_configure_logging_default_sets_warning_level():
    logger = _reset_logger()

    configure_logging(verbose=False)

    assert logger.level == logging.WARNING


def test_configure_logging_is_idempotent():
    logger = _reset_logger()

    configure_logging()
    configure_logging()

    assert len(logger.handlers) == 1  # repeated calls do not stack handlers


def test_configure_logging_writes_to_stderr():
    logger = logging.getLogger("news_agent")
    logger.handlers.clear()  # handler is only attached when none exist
    configure_logging()
    handler = logger.handlers[0]
    assert handler.console.stderr is True  # RichHandler must target stderr, not stdout
    logger.handlers.clear()
