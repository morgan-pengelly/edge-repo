from datetime import datetime
import sqlite3
import os
from sqlite3 import Error
from core.lib.log_setup import setup_logger
from core.util import client_config

logger = setup_logger(__name__, client_config["util-log"])


class Database(object):
    """Database object for local storage of tabular information."""

    def __init__(self, path: str):

        self.path = path
        try:
            self.connection = sqlite3.connect(self.path)
            # logger.info("Connection to SQLite DB %s successful.", self.path)
        except Error as excp:
            logger.exception("Error Occured connecting to %s: %s", path, excp)

    def execute_query(self, query):
        """Execute Query on table."""
        cursor = self.connection.cursor()
        try:
            cursor.execute(query)
            self.connection.commit()
        except Error as excp:
            logger.exception("Error Occured: %s", excp)

    def execute_read_query(self, query):
        """Execute read query on table."""
        cursor = self.connection.cursor()
        result = None
        try:
            cursor.execute(query)
            result = cursor.fetchall()
            return result
        except Error as excp:
            logger.exception("Error Occured: %s", excp)
            return None

    def table_exists(self, table_name: str):
        cursor = self.connection.cursor()
        result = None
        # Check if the table exists
        # Execute the query to check if the table exists
        cursor.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
        )
        result = cursor.fetchall()
        if result:
            return True
        else:
            return False

    def create_upload_table(self):
        if self.table_exists("files"):
            return
        """Create Table for tracking file paths and accessed dates."""
        create_files_table = """
        CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT NOT NULL,
        last_uploaded TEXT,
        version TEXT DEFAULT '1.0'
        );
        """
        self.execute_query(create_files_table)

    def create_config_table(self):
        if self.table_exists("configs"):
            return
        """Create Table for tracking file paths and accessed dates."""
        create_configs_table = """
        CREATE TABLE configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT NOT NULL,
        path TEXT NOT NULL,
        last_downloaded TEXT DEFAULT ''
        );
        """
        # TODO Handle already exists exception to not polut log.
        self.execute_query(create_configs_table)

    def add_data_file(self, path):
        """Add a file to database as processed."""
        query = f"""
        INSERT INTO
            files (path, last_uploaded )
        VALUES
            ('{path}','{datetime.now().isoformat()}')
        """
        self.execute_query(query)

    def add_config_file(
        self,
        key,
        path,
        last_downloaded: datetime = datetime.fromisoformat("0001-01-01T00:00:00+00:00"),
    ):
        """Add a file to database as processed."""
        query = f"""
        INSERT INTO
            configs (key, path, last_downloaded )
        VALUES
            ('{key}','{path}','{last_downloaded.isoformat()}')
        """
        self.execute_query(query)

    def update_config_file(
        self,
        key,
        path,
        last_downloaded: datetime = datetime.fromisoformat("0001-01-01T00:00:00+00:00"),
    ):
        """Add a file to database as processed."""
        query = f"""
        INSERT INTO
            configs (key, path, last_downloaded )
        VALUES
            ('{key}','{path}','{last_downloaded.isoformat()}')
        """
        self.execute_query(query)

    def is_update_needed(self, key: str, last_updated: str):
        """Return exists, update_needed if in db, return None if not in db
        :key is a filename with suffix
        :last_updated datetime as isoformatted string."""
        search_files = f"""
        SELECT last_downloaded 
        FROM configs
        WHERE key = '{key}'"""
        files = self.execute_read_query(search_files)
        # Handle duplicate entries and return the most recently added1
        if files is not None:
            exists = True
            updated_needed = True
            # If there is an entry of a file update that occured after the last time
            # the cloud file was modified no update is needed.
            for file in files:
                file_time = datetime.fromisoformat(file[0])
                if file_time > datetime.fromisoformat(last_updated):
                    updated_needed = False
        else:
            exists = False
            updated_needed = False
        return exists, updated_needed

    def get_file_upload_time(self, path: str):
        """Return datetime if in db, return None if not in db"""
        select_files = f"""
        SELECT last_uploaded 
        FROM files
        WHERE path = '{path}'"""
        files = self.execute_read_query(select_files)
        most_recent_time: datetime = datetime.fromisoformat("0001-01-01T00:00:00")
        # Handle duplicate entries and return the most recently added1
        for file in files:
            file_time = datetime.fromisoformat(file[0])
            if file_time > most_recent_time:
                most_recent_time = file_time
        # TODO if duplicates exist clean up before returing time
        return most_recent_time

    def remove_all_duplicates(self, table: str):
        """Remove all duplicates from Databased based on path and highest id"""
        remove_duplicates = f"""
        DELETE FROM {table}
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM {table}
            GROUP BY path
        )
        """
        self.execute_query(remove_duplicates)

    def remove_dead_links(self):
        """Remove files that no longer exist in data/upload"""
        path_list: list[str] = []
        for root, _dirs, files in os.walk("data/upload"):
            for file in files:
                full_path = os.path.join(root, file)
                path_list.append(full_path)
        formatted_list = "',\n            '".join(path_list)
        remove_deadlinks = f"""
        DELETE FROM files
        WHERE path NOT IN (
            '{formatted_list}'
        )
        """
        self.execute_query(remove_deadlinks)


if __name__ == "__main__":
    database = Database("data/local_db.sqlite")
    database.create_upload_table()
    database.add_data_file("test123")
    database.remove_dead_links()

    # database.get_file_upload_time("test/test/try.mp4")

    # connection = create_connection("data/upload.sqlite")
    # execute_query(connection, create_files_table)
    # execute_query(connection, file_query(".data/test"))
