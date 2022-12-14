import logging
from logging.handlers import TimedRotatingFileHandler

# sets up log file as unique file that will grow for ever
def setup_timed_rotating_logger(name, log_file, level=logging.INFO):

    name = '[' + name
    name = name + ']'
    extra={'myApp': name}
    formatter = logging.Formatter('%(myApp)s - %(asctime)s %(levelname)s %(message)s')
    #setting up an independant logger for multiple log files
    handler = logging.FileHandler(log_file, mode='a')
    handler.setFormatter(formatter)
    
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        logger.addHandler(handler)
        logger = logging.LoggerAdapter(logger, extra)
    else:
        logger.setLevel(level)
        logger = logging.LoggerAdapter(logger, extra)

    return logger

    
