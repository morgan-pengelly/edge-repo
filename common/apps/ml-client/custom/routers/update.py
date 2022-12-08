"""This module is used for handling all update actions to servers."""
from datetime import datetime
import pathlib
from fastapi import APIRouter, Response, status
import core.util as util
from core.util import client_config
from core.models.Database import Database
from azure.storage.blob import ContainerClient, BlobClient
import json


# Establish Router with designated module prefixes.
router = APIRouter(prefix="/update")
# Create Objects needed by all update functions
logger = util.log.setup_logger(__name__, client_config["api-log"])
database = Database("./data/config.sqlite")
# Create upload table if it does not exist.
database.create_upload_table()


@router.get("/all-configs", status_code=status.HTTP_202_ACCEPTED, tags=["update"])
async def update_configs(response: Response):
    """Pull latest config files from server"""
    logger.info("Contacting server for config file updates...")
    try:
        file_list = json.loads(util.cloud.get_config_list())
    except TypeError:
        response.status_code = status.HTTP_404_NOT_FOUND
        logger.warning("Config update failed, using local files.")
        return
    # file dict is list of lists [[fileName,lastUpdated],...]
    for file in file_list:
        # Get file name from blob name
        file_name = pathlib.Path(file[0]).name
        last_updated = file[1]
        if database.is_update_needed(file_name, last_updated):
            util.cloud.update_config_file(file_name)
            database.add_config_file(
                file_name, util.config.get_file_path(file_name), datetime.utcnow()
            )
    database.remove_all_duplicates("configs")

    logger.info("Config Files Checked for Updates")


@router.on_event("startup")
async def startup_event():
    """Start Update Processes"""
    await update_configs(response=Response())
