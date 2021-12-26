import os
from setting import BASE_PATH, IS_PUB
import logging.handlers
format_str = '[%(processName)s][%(threadName)s][%(asctime)s][%(filename)s:%(lineno)d][%(levelname)s]:%(message)s'
logger = logging.getLogger("COM")
logger.setLevel(logging.DEBUG)

try:
    log_dir = os.path.join(BASE_PATH, "tool_log")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    rf_handler = logging.handlers.RotatingFileHandler(os.path.join(log_dir, "tool.log"),
                                                      maxBytes=1024 * 1024 * 10, backupCount=10, )
    rf_handler.setFormatter(logging.Formatter(format_str))
    rf_handler.setLevel(logging.DEBUG)
    logger.addHandler(rf_handler)
    if not IS_PUB:
        str_handler = logging.StreamHandler()
        str_handler.setFormatter(logging.Formatter(format_str))
        str_handler.setLevel(logging.DEBUG)
        logger.addHandler(str_handler)
except Exception as e:
    print(e)

