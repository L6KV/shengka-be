from loguru import logger

from loguru import logger


class LogUtil:
    @staticmethod
    def info(message, **kwargs):
        logger.info(message, **kwargs)

    @staticmethod
    def debug(message, **kwargs):
        logger.debug(message, **kwargs)

    @staticmethod
    def warning(message, **kwargs):
        logger.warning(message, **kwargs)

    @staticmethod
    def error(message, **kwargs):
        logger.error(message, **kwargs)

    @staticmethod
    def critical(message, **kwargs):
        logger.critical(message, **kwargs)
    

myLogger = LogUtil()