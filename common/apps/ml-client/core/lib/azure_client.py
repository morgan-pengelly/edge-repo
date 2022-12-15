""" This defines all functions used to interact with the Azure Cloud Storage. """
import yaml
from azure.storage.blob import (
    BlobServiceClient,
)
from core.models.models import ContainerConnection


manual: bool = True  # used to reference config files rather than remote services.


def get_connection_string():
    """Get connection string from local azureSecrets.yml."""
    try:
        if manual:
            with open("config/clientConfig.yml", "r") as file:
                config = yaml.safe_load(file)
            return config["connection-string"]
    except Exception as excp:
        print(excp)
        return None


def getConnectInfo():
    info = ContainerConnection()
    info.connect_str = get_connection_string()
    if manual:
        info.container_name = "ml-test"  # hardcoded for now.
    return info


def getSASToken():
    info = ContainerConnection()
    info.connect_str = get_connection_string()
    if manual:
        info.container_name = "ml-test"  # hardcoded for now.
    return info


def newClient(connect_str: str):
    """Create a client from connection string."""
    try:
        blob_service_client: BlobServiceClient = (
            BlobServiceClient.from_connection_string(connect_str)
        )
        return blob_service_client
    except Exception as e:
        print(e)
        return None
