"""Util for log manipulations."""
from datetime import datetime, timedelta

from yaml.scanner import ScannerError

from core.models.models import Event
import core.util.config_util as config_util
from core.lib.log_setup import setup_logger
from core.util import client_config

logger = setup_logger(__name__, client_config["util-log"])


def parse_log(log_path: str):
    r"""Imports log and parses by \n and returns as list of strings."""
    log_strings: list[str] = []
    with open(log_path, "r") as log:
        for line in log:
            # Remove linebreak from a current name (linebreak is the last character of each line)
            clean_string = line[:-1]
            log_strings.append(clean_string)
    return log_strings


def import_event_log(log_path: str, config_path: str):
    """Imports events from log and config file."""
    # load event configs
    try:
        config = config_util.load_yaml(config_path)
    except ScannerError:
        logger.error(
            "Unable to import event config, check formatting.(%s)", config_path
        )
        return None

    # Take in list of events
    event_strings = parse_log(log_path)
    event_list = []
    # Convert each line into an event object and add to event_list
    for line in event_strings:
        event_parts = line.split()
        event = Event()
        event.log_path = log_path
        event.type = event_parts[3]
        event.source = event_parts[5]
        event.id = event_parts[7]
        # parse time to get start time
        event.log_time = datetime.strptime(
            (event_parts[0] + " " + event_parts[1]), "%Y-%m-%d %H:%M:%S,%f"
        )
        # Add buffer info based on config file. this assumes the fromat of the yaml
        # variable name and the event.type are identical to allow for direct reference.
        try:
            event.start_buffer = timedelta(seconds=config[event.type]["start-buffer"])
            event.end_buffer = timedelta(seconds=config[event.type]["end-buffer"])
        except KeyError:
            logger.exception(
                "Unable to reference %s buffers, please check formating of %s",
                event.type,
                config_path,
            )
            return None
        event_list.append(event)
    return event_list


def remove_event_by_id(log_path: str, event_id: str):
    with open(log_path, "r+") as f:
        d = f.readlines()
        f.seek(0)
        for i in d:
            if event_id not in i:
                f.write(i)
        f.truncate()
