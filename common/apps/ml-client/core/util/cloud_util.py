"""This module is used for handling all upload actions to servers."""
import requests
from azure.storage.blob import ContainerClient, BlobClient
import core.util as util
from core.util import client_config
from core.lib.log_setup import setup_logger
import json
from datetime import datetime
import pathlib
from core.models.models import BlobType

logger = setup_logger(__name__, client_config["util-log"])


def get_config_list():
    try:
        headers = {"accept": "application/json"}
        url = f"{util.client.get_server_address()}:8080/config/filelist?site_id={client_config['site-id']}&device_id={client_config['device-id']}"
        response = requests.get(url, headers=headers, timeout=5)
        # Parse json response
        if response is not None:
            data = response._content
        return data
    except ConnectionRefusedError:
        logger.error("Connection Refused By ML-Server")
        return None
    except:
        logger.error("Unable to Reach ML-Server:")
        return None


def get_file_blob_url(file_name: str):
    try:
        headers = {"accept": "application/json"}
        url = f"{util.client.get_server_address()}:8080/config/blob-url?site_id={client_config['site-id']}&device_id={client_config['device-id']}&key={file_name}"
        response = requests.get(url, headers=headers, timeout=5)
        if response is not None:
            data = response.content
        return data
    except:
        logger.exception("Error Occured.")
        return None


def get_container_url():
    try:
        headers = {"accept": "application/json"}
        url = f"{util.client.get_server_address()}:8080/upload/container-url?site_id={client_config['site-id']}&device_id={client_config['device-id']}"
        response = requests.get(url, headers=headers, timeout=5)
        if response is not None:
            data = response.content
        return data
    except:
        logger.exception("Error Occured.")
        return None


def update_config_file(file_name: str):
    # https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/storage/azure-storage-blob/samples/blob_samples_authentication.py#L75
    print(f"Update needed for: {file_name}")
    try:
        blob_url = json.loads(get_file_blob_url(file_name))
    except TypeError:
        logger.warning("Config update failed, using local files.")
        return
    path = f"custom/config/{file_name}"
    print(blob_url)
    blob_client = BlobClient.from_blob_url(blob_url)
    with open(path, "wb") as my_blob:
        download_stream = blob_client.download_blob()
        my_blob.write(download_stream.readall())
    print(f"Updated: {path}")


def build_blob_name(filepath: str, blob_type: BlobType = BlobType.OTHER):
    """Build string for container architecture."""
    # Save File Suffix
    suffix = pathlib.Path(filepath).suffix
    stem = pathlib.Path(filepath).stem
    # Use db sub directory as source, I.E .db/test/example.txt returns test
    source = str(pathlib.Path(filepath).parents[0])
    source = source[len(str(pathlib.Path(filepath).parents[1])) :]
    file_id = (
        datetime.now().strftime("%b_%d_%Y_%H-%M-%S_")
        + client_config["site-id"]
        + stem
        + suffix
    )

    # shorten file length if exceeds recomended max of 255.
    if len(file_id + suffix) >= 255:
        file_id = file_id[: (254 - len(suffix))]
        # logger.warning('file_id too long, file_id shortened to %s',file_id)

    blob_name = (
        client_config["site-id"]
        + "/"
        + client_config["device-id"]
        + source
        + "/"
        + file_id
    )
    return blob_name
