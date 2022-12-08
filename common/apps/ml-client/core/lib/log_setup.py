"""Default Log Setup"""
import logging
from datetime import time
from logging.handlers import TimedRotatingFileHandler

formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
# sets up log file as unique file that will grow for ever
def my_namer(default_name):
    # This will be called when doing the log rotation
    # default_name is the default filename that would be assigned, e.g. Rotate_Test.txt.YYYY-MM-DD
    # Do any manipulations to that name here, for example this changes the name to Rotate_Test.YYYY-MM-DD.txt
    base_filename, ext, date = default_name.split(".")
    return f"{base_filename}{date}.{ext}"


def setup_logger(name: str, log_path: str, level=logging.INFO, stream=True):
    """Perform initial logger setup with file and console/"stream" outputs."""
    # Create Logger instance referenced by name
    new_logger = logging.getLogger(name)
    #'midnight' triggers rollover based on atTime, is not actually midnight
    handler = TimedRotatingFileHandler(
        log_path,
        when="midnight",
        # This time needs to be tested, but system does rollover.
        atTime=time(hour=13, minute=26),
        backupCount=10,
    )
    handler.setFormatter(formatter)
    new_logger.setLevel(level)
    handler.namer = my_namer
    new_logger.addHandler(handler)
    if stream:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        new_logger.addHandler(stream_handler)
    return new_logger
