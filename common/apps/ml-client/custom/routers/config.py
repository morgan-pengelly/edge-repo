"""This module is used for distributing configuration files to other containers/services."""
from fastapi import status, APIRouter, Response
import core.util as util
from core.util import client_config
from core.models.Configuration import Configuration


# Establish Router with designated module prefixes.
router = APIRouter(prefix="/config")
# Create Objects needed by all update functions
logger = util.log.setup_logger(__name__, client_config["api-log"])
config = Configuration()


@router.on_event("startup")
async def startup_event():
    """Load Config Data"""
    config.load()
    # Launch thread to monitor all file changes in config['db-path']
    # logger.info("FileMonitor Started")


@router.get("/{config_id}", tags=["config"])
async def return_config(config_id: str, response: Response):
    """Uses configuration's loaded files to return any config file it has loaded."""
    try:
        return config.data[config_id]
    except:
        response.status_code = status.HTTP_404_NOT_FOUND
        return None
