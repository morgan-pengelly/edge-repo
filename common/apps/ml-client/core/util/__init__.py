"""Imports all utilities files to form Utilities Package."""
import yaml


def load_client_config():
    """Loads custom/clientConfig.yml"""
    with open("config/mlclient.yml", "r") as stream:
        client_config = yaml.safe_load(stream)
        return client_config


client_config = load_client_config()

from . import file_util as file
from . import video_util as video
from . import client_util as client
from . import config_util as config
from . import log_util as log
from . import cloud_util as cloud
