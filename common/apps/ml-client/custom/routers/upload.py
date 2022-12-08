"""This module is used for handling all upload actions to servers."""
import threading
import os
import json
import requests
from datetime import datetime, timedelta
from fastapi import status, APIRouter, Response
from azure.storage.blob import ContainerClient, BlobClient
import custom.lib.file_monitor as filemonitor
import core.util as util
from core.util import client_config
from core.models.Database import Database
from core.models.models import BlobType


# Establish Router with designated module prefixes.
router = APIRouter(prefix="/upload")
# Create Objecs needed by all upload functions
logger = util.log.setup_logger(__name__, client_config["api-log"])
change_list_lock = threading.Lock()
fileMonitor = filemonitor.FileMonitor(change_list_lock)
database = Database("./data/upload.sqlite")
database.create_upload_table()


@router.on_event("startup")
async def startup_event():
    """Start Upload Processes"""
    # Launch thread to monitor all file changes in config['db-path']
    fileMonitor.start()
    logger.info("FileMonitor Started")


@router.get("/alldata", status_code=status.HTTP_202_ACCEPTED, tags=["upload"])
def upload_all_data(response: Response):
    # Get all files in the upload directory
    try:
        container_url = json.loads(util.cloud.get_container_url())
    except:
        logger.error("Unable to get get container URL.")
        response.status_code = status.HTTP_400_BAD_REQUEST
        return "Failure"
    logger.info(f"Container Url: {container_url}")
    container_client: ContainerClient = ContainerClient.from_container_url(
        container_url
    )
    for root, _dirs, files in os.walk("data/upload"):
        for file in files:
            # Check when file was last uploaded
            full_path = os.path.join(root, file)
            last_upload_time = database.get_file_upload_time(full_path)
            # get last modified time as datetime
            m_time = datetime.fromtimestamp(os.path.getmtime(full_path))
            if m_time > last_upload_time:
                logger.info("Uploding:" + full_path)
                with open(full_path, "rb") as data:
                    blob_client = container_client.upload_blob(
                        name=util.cloud.build_blob_name(full_path), data=data
                    )

                database.add_data_file(full_path)
    # Remove all duplicates in database
    database.remove_all_duplicates("files")
    util.file.remove_files_by_mtime(
        "data/upload", timedelta(days=client_config["file-persist-days"])
    )
    database.remove_dead_links()
    return "Success"
