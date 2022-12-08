# Contains all info needed to upload data to cloud.\
from datetime import datetime, timedelta, date
from enum import Enum


class ContainerConnection:
    """Connection Object For Azure Blob Storage"""

    connect_str: str
    container_name: str


class Event:
    """Standard Event Object"""

    def __init__(self) -> None:
        self.id: str
        self.log_time: datetime
        self.log_path: str
        self.source: str
        self.type: str
        self.date: date
        self.start_buffer: timedelta
        self.end_buffer: timedelta

    def start_time(self):
        return self.log_time - self.start_buffer

    def end_time(self):
        return self.log_time + self.end_buffer

    def get_files(self):
        import core.util as util

        src_config = util.config.load_yaml("./custom/cameras.yml")
        for camera in src_config["camera"]:
            if camera["id"] == self.source:
                files = util.file.get_timestamped_files(
                    camera["directory"],
                    src_config["file-pref"]["suffix"],
                    source=camera["id"],
                )
                break
        # Iterate from back to front of list so files can be removed without messing with index.
        for i in range(len(files) - 1, -1, -1):
            if (
                files[i].start_time > self.start_time()
                or files[i].end_time < self.end_time()
            ):
                del files[i]
        # Sort files by start time in case there are more than one file.
        files.sort(key=lambda x: x.start_time)
        return files

    def delete_from_log(self):
        from core.util.log_util import remove_event_by_id

        remove_event_by_id(self.log_path, self.id)


class DataFile:
    """Standard Data/Video File Object"""

    def __init__(self, source: str = None, data_type: str = None) -> None:
        self.path: str
        self.start_time: datetime
        self.end_time: datetime
        self.source = source
        self.type: data_type  # Currently not used


class Camera(object):
    """Object to house imported camera info from config files"""

    id: str = None
    url: str = None
    description: str = None
    directory: str = None
    frames_per_day: int = None

    def __init__(
        self,
        id: str = None,
        url: str = None,
        description: str = None,
        directory: str = None,
    ):
        self.id = id
        self.url = url
        self.description = description
        self.directory = directory
        self.logfile = f"./logs/{id}.log"

    def get_files(self, time: datetime = datetime.now()):
        """Get all files in the 24hrs before time provided. By Default returns all files from camera in last 24 hours"""
        import core.util as util

        src_config = util.config.load_yaml("./custom/cameras.yml")
        files = util.file.get_timestamped_files(
            self.directory,
            src_config["file-pref"]["suffix"],
            source=self.id,
        )
        # for file in files:
        #     print(
        #         f"Start: {file.start_time.isoformat()} End: {file.end_time.isoformat()}"
        #     )
        util.file.filter_by_time_window(files, (time - timedelta(days=1)))
        return files


class BlobType(Enum):
    """Enum for blob type case statements etc."""

    EVENTVIDEO = 1
    EVENTPHOTO = 2
    LOG = 3
    OTHER = 999
