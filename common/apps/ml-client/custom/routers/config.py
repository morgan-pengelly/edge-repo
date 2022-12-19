"""This module is used for distributing configuration files to other containers/services."""
from datetime import datetime
import pathlib
import inspect
import json
import os
import copy
from typing import Optional
from fastapi import status, APIRouter, Response
import core.util as util
from core.util import client_config
from core.models.Database import Database
from core.models.Configuration import Configuration


# Establish Router with designated module prefixes.
router = APIRouter(prefix="/config")
local_db = Database("./data/local_db.sqlite")
config = Configuration()
logger = util.log.setup_logger(__name__, client_config["api-log"])


@router.get("/update-all", status_code=status.HTTP_202_ACCEPTED, tags=["update"])
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
        if local_db.is_update_needed(file_name, last_updated):
            util.cloud.update_config_file(file_name)
            local_db.add_config_file(
                file_name, util.config.get_file_path(file_name), datetime.utcnow()
            )
    local_db.remove_all_duplicates("configs")

    logger.info("Config Files Checked for Updates")


@router.on_event("startup")
async def startup_event():

    local_db.create_config_table()
    """Load Config Data"""
    await update_configs(response=Response())
    config.load()
    # Launch thread to monitor all file changes in config['db-path']
    # logger.info("FileMonitor Started")


@router.get("", tags=["Configuration"])
def get_configuration():
    return ApiResponse(config.data)


@router.get("/reload", tags=["Configuration"])
async def reload_configuration():
    await update_configs(response=Response())
    config.load()
    return ApiResponse(config.data)


@router.get("/{config_id}", tags=["Configuration"])
async def return_config(config_id: str, response: Response):
    """Uses configuration's loaded files to return any config file it has loaded."""
    try:
        return ApiResponse(config.data[config_id])
    except:
        response.status_code = status.HTTP_404_NOT_FOUND
        return None


def ApiResponse(data="", error="", code=200):
    success = True if not error else False
    response = {}
    response["success"] = success
    response["timestamp"] = datetime.now()
    response["function"] = inspect.stack()[1][3]
    if success:
        response["data"] = data
    else:
        data["reason"] = error
        response["error"] = data
    return response
