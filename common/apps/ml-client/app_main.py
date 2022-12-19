"""Main Launching point, and contains base class for FastAPI framework."""
import os
import datetime
from urllib import response

# import speedtest
import requests
from fastapi import FastAPI, status, Response
from custom.routers import update
from custom.routers import upload
from custom.routers import schedule
from custom.routers import video
from custom.routers import config
import uvicorn
import core.util as util


# Start Main API
app = FastAPI()
# Add Modules
app.include_router(update.router)
app.include_router(upload.router)
app.include_router(schedule.router)
app.include_router(video.router)
app.include_router(config.router)

# Start Logger
# Import configuration YAML file as global config variable.
config = util.client_config
logger = util.log.setup_logger(__name__, config["api-log"])


@app.on_event("startup")
async def startup_event():
    """Client Initialization"""
    # Checks internet speed but adds 10-20 seconds to startup.
    # if config["speed-test"]:
    #     try:
    #         #TODO Get reliable speed test.
    #         logger.info("Starting New Speed Test (may take 30")
    #         speed_test = speedtest.Speedtest()
    #         download_speed = round(
    #             speed_test.download() / (1024 * 1024), 2
    #         )  # bytes to mb
    #         logger.info("Download Speed: %s mbps", download_speed)
    #         upload_speed = round(speed_test.upload() / (1024 * 1024), 2)  # bytes to mb
    #         logger.info("Upload Speed: %s mbps", upload_speed)
    #     except Exception as e:
    #         logger.exception("Speed Test Failed %s", e)


@app.get("/info")
def info():
    """Returns Device ID"""
    logger.info("This is ml-client on device: %s", config["device-id"])
    return {f"This is ml-client on device: {config['device-id']}"}


@app.get("/testserver", tags=["server"])
def ping_server(response: Response):
    """Simple method to test server connectivity."""
    try:
        headers = {"accept": "application/json"}
        req = requests.get(
            util.client.get_server_address() + ":8080/info", headers=headers, timeout=5
        )  # Currently hardcoded for WSL Test Enviornment
        return req.content
    except requests.exceptions.ConnectTimeout:
        logger.exception("exception")
        response.status_code = status.HTTP_408_REQUEST_TIMEOUT
        return "error"
    except ConnectionRefusedError:
        logger.exception("exception")
        response.status_code = status.HTTP_403_FORBIDDEN
        return "error"


# @app.get("/config/camsys/lastmodified")
# def send_config():
#     """Sends camsys config's last modified time."""
#     mtime = datetime.datetime.fromtimestamp(
#         os.path.getmtime("custo/mcamsys.yml"), datetime.timezone.utc
#     )
#     return f"{mtime} UTC"


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
