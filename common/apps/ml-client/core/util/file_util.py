"""Utilities for file handling"""
import os
import re
import pathlib
from datetime import datetime, timedelta
from core.lib.log_setup import setup_logger
from core.models.models import DataFile
from core.util import client_config

logger = setup_logger(__name__, client_config["util-log"])


def get_timestamped_files(directory: str, suffix: str, source: str):
    """Returns a list of DataFile objects from a given directory,
    parsing path for date and start/end times. Assumes date is year
    month day, and time is hour minute second. Delimeters can be any of ._,-"""
    file_list: list[DataFile] = []
    for root, _dirs, files in os.walk(directory):
        for file in files:
            sfile_date: str = None
            file_time = []
            sfile_time = []
            if pathlib.Path(file).suffix == suffix:
                data_file: DataFile = DataFile()
                data_file.source = source
                data_file.path = os.path.join(root, file)
                try:
                    sfile_date = re.search(
                        r"2[0-9][0-9][0-9][._,-][0-9][0-9][._,-][0-9][0-9]",
                        data_file.path,
                    ).group(0)
                except ValueError:
                    continue
                except AttributeError:
                    print(f"Unable to find date in file path: {data_file.path}")
                    continue
                sfile_time.extend(re.findall(r"..[._,-]..[._,-]..", data_file.path))
                for string in sfile_time:
                    try:
                        file_time.append(
                            # build datetime based on string structure.
                            datetime(
                                year=int(sfile_date[0:4]),
                                month=int(sfile_date[5:7]),
                                day=int(sfile_date[8:10]),
                                hour=int(string[0:2]),
                                minute=int(string[3:5]),
                                second=int(string[6:]),
                            )
                        )
                    except Exception as excp:
                        print(excp)
                # Get two closest times.
                span: timedelta = None
                for time1 in file_time:
                    for time2 in file_time:
                        if time1 != time2:
                            # Find smallest span in time files.
                            if span is None or abs(time1 - time2) < span:
                                span = abs(time1 - time2)
                                data_file.start_time = min(time1, time2)
                                data_file.end_time = max(time1, time2)
                # append file to list
                file_list.append(data_file)
    # for file in file_list:
    #     print(f"{__name__}:{file.path}")
    return file_list


def filter_by_time_window(
    files: list[DataFile], start: datetime, end: datetime = datetime.now()
):
    """Filter list by t"""
    for i in range(len(files) - 1, -1, -1):
        if files[i].start_time > end or files[i].end_time < start:
            del files[i]
    # Sort files by start time in case there are more than one file.
    files.sort(key=lambda x: x.start_time)
    return files


def remove_files_by_mtime(
    path: str,
    cutoff: timedelta,
):
    """Remove all files that have not been modified in ___ days"""
    for root, _dirs, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            m_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            if datetime.now() - m_time > cutoff:
                os.remove(file_path)
                print(f"Removing: {file}")
