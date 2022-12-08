"""Class for monitoring all changes in a directory."""
import time
import threading
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import core.util as util
from core.lib.log_setup import setup_logger

# Import configuration YAML file as global config variable.
config = util.client_config
logger = setup_logger(__name__, config["file-monitor-log"], stream=False)


class FileMonitor(threading.Thread):
    """This creates a thread to monitor all files at the specified location.
    https://www.geeksforgeeks.org/create-a-watchdog-in-python-to-look-for-filesystem-changes/"""

    def __init__(self, lock: threading.Lock):
        super().__init__()
        # Path to be monitored
        self.lock = lock
        self.event_handler = FileChangeHandler(lock)
        self.event_handler.load_change_log()
        self.observer = Observer()

    def run(self):
        # add all observed paths to monitor
        for path in config["monitor-paths"].split():
            self.observer.schedule(self.event_handler, path, recursive=True)
        self.observer.start()
        while True:
            # Seconds between file checks.
            time.sleep(5)


class FileChangeHandler(PatternMatchingEventHandler):
    """Handles file change events"""

    def __init__(self, lock: threading.Lock):
        self.changelist = []
        self.lock = lock
        super(FileChangeHandler, self).__init__(
            ignore_patterns=config["ignore-list"].split()
        )

    def load_change_log(self):
        """Load ChangeLog into file list using: https://pynative.com/python-write-list-to-file/"""
        self.lock.acquire()
        try:
            self.changelist = util.log.parse_log(config["change-log-path"])
            logger.info(
                "ChangeLog loaded successfully from %s.", config["change-log-path"]
            )
        except FileNotFoundError:
            # If file not found create file.
            new_log = open(config["change-log-path"], "w")
            new_log.close()
            logger.info("New Changelog Created \n")
        finally:
            self.lock.release()

    def add_to_list(self, src_path: str):
        """Add src_path of event to changeLog file."""
        self.lock.acquire()  # grab semaphore for file change
        change_log = open(config["change-log-path"], "a")
        change_log.write(f"{src_path}\n")
        change_log.close()
        self.lock.release()  # release semaphore at end of file change.
        self.changelist.append(src_path)
        logger.info("Added: " + src_path + " to changeList.")

    def remove_from_list(self, src_path: str):
        """Remove src_path of event to changeLog file. (Assumes self.filelist is current)"""
        self.lock.acquire()  # grab semaphore for file change
        self.changelist.remove(src_path)
        with open(config["change-log-path"], "w") as log:
            for item in self.changelist:
                # write each item on a new line
                log.write(f"{item}\n")
        log.close()
        self.lock.release()  # release semaphore at end of file change.
        logger.info("Added:" + src_path + "to changeList")

    # if files is modified add to list of files to upload
    def on_modified(self, event):
        if event.src_path not in self.changelist and not event.is_directory:
            FileChangeHandler.add_to_list(self, event.src_path)

    # add to list of files to upload
    def on_created(self, event):
        if event.src_path not in self.changelist and not event.is_directory:
            FileChangeHandler.add_to_list(self, event.src_path)

    # remove from list of files to upload
    def on_deleted(self, event):
        if event.src_path in self.changelist and not event.is_directory:
            FileChangeHandler.remove_from_list(self, event.src_path)

    def on_moved(self, event):
        # remove old path
        if event.src_path in self.changelist and not event.is_directory:
            FileChangeHandler.remove_from_list(self, event.src_path)
        # add new path
        if event.dest_path not in self.changelist and not event.is_directory:
            FileChangeHandler.add_to_list(self, event.dest_path)


# Code for running tests in sandbox
if __name__ == "__main__":
    test_lock = threading.Lock()
    monitor = FileMonitor(lock=test_lock)
    monitor.start()
