"""Stanard Utilities to all clients."""
import pathlib
from datetime import datetime
import inspect
from core.lib.log_setup import setup_logger
from core.util import client_config
from core.models.models import BlobType

logger = setup_logger(__name__, client_config["util-log"])


def get_server_address():
    """Returns the server address with http:// prefix but does not include port."""
    if client_config["local-test"]:
        ip = "host.docker.internal"
        return f"http://{ip}"
    return ""


# Based on edge-repo code base from Equilibrium
def api_response(data="", error="", code=200):
    """Generates General Response JSON"""
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
