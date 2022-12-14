"""Tools for handling the importing of config files (currently in yaml form)."""
import yaml
from core.models.models import Camera
from core.lib.log_setup import setup_logger
from core.util import client_config

logger = setup_logger(__name__, client_config["util-log"])


def load_objects(class_obj, path: str):
    """Takes in an object, and returns a list of object configured by the provided config file."""
    # Clean object name to be lowercase
    clean_name = (class_obj.__name__).lower() + "s"
    print(clean_name)
    try:
        with open(path, "r") as stream:
            parsed_yaml = yaml.safe_load(stream)
    except KeyError:
        logger.exception("load_objects: error reading %s", path)

    # get all class parameters
    # #https://stackoverflow.com/questions/11637293/iterate-over-object-attributes-in-python
    class_params = [a for a in dir(class_obj) if not a.startswith("__")]
    # Create empty list
    object_list = []
    for u_object in parsed_yaml[clean_name]:
        item = class_obj()
        for param in class_params:
            setattr(item, param, u_object[param])
        object_list.append(item)
    return object_list


def load_yaml(path: str):
    """Safe load any yaml file and return parsed yaml."""
    # data = {}
    try:
        with open(path, "r") as stream:
            parsed_yaml = yaml.safe_load(stream)
    except KeyError:
        logger.exception("Error reading %s", path)
    return parsed_yaml


def load_cameras(path: str):
    """Takes in an object, and returns a list of object configured by the provided config file."""
    # Clean object name to be lowercase
    clean_name = "cameras"
    try:
        with open(path, "r") as stream:
            parsed_yaml = yaml.safe_load(stream)
    except:
        logger.exception(f"load_cameras: error reading {path}")

    # get all class parameters https://stackoverflow.com/questions/11637293/iterate-over-object-attributes-in-python
    class_params = [
        # remove all
        a
        for a in dir(Camera)
        if not (a.startswith("__") or a.startswith("get"))
    ]
    # print(class_params)
    # Create empty list
    object_list = []
    for u_object in parsed_yaml[clean_name]:
        item = Camera()
        for param in class_params:
            # .yml doesnt suppot underscore(_) so all are replaced with dash(-)
            access_param = param.replace("_", "-")
            setattr(item, param, u_object[access_param])
        object_list.append(item)
    return object_list


def get_file_path(file_name: str):
    return f"custom/config/{file_name}"
