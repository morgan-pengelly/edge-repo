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


@router.on_event("startup")
async def startup_event():
    """Start Update Processes"""
