"""This module is used for handling all video conversion and modification actions to servers."""
import asyncio
from queue import Queue
from fastapi import status, APIRouter
import core.util as util
from custom.lib.ffmpeg_manager import FfmpegManager, EventVideoJob, FramesJob
from core.models.models import Event, Camera

# Import configuration YAML file as global config variable.
client_config = util.client_config
# Establish Router with designated module prefixes.
router = APIRouter(prefix="/video")
# Create Objecs needed by all upload functions
logger = util.log.setup_logger(__name__, client_config["api-log"])
job_queue = Queue()
job_manager = FfmpegManager(job_queue)


@router.on_event("startup")
async def startup_event():
    """Start Upload Processes"""
    # Launch thread to monitor all file changes in config['db-path']
    job_manager.start()
    logger.info("Ffmpeg Manager Started")


@router.get("/geteventjobs", status_code=status.HTTP_202_ACCEPTED, tags=["video"])
async def get_event_jobs():
    """Fill job with all event jobs queue"""
    events: list[Event] = util.log.import_event_log(
        client_config["event-log"], "./custom/eventConfig.yml"
    )
    for event in events:
        logger.info("Adding Event: %s to job queue", event.id)
        job_queue.put(EventVideoJob(event.get_files(), event))

    return f"Job Queue containts {job_queue.qsize()}"


@router.get("/getframejobs", status_code=status.HTTP_202_ACCEPTED, tags=["video"])
async def get_frame_jobs():
    """Fill job with all frame generation jobs queue"""
    cameras: list[Camera] = util.config.load_cameras("./custom/cameras.yml")
    for camera in cameras:
        # Get all files generated by camera in last 24 hours.
        camera_files = camera.get_files()
        for file in camera_files:
            job_queue.put(FramesJob(file, camera))
    return f"Job Queue containts {job_queue.qsize()}"


@router.get("/runjobs", status_code=status.HTTP_202_ACCEPTED, tags=["video"])
async def run_jobs():
    """Process queue"""
    job_manager.enable()
    while job_manager.enabled:
        asyncio.sleep(1)
    return f"Job Queue containts {job_queue.qsize()}"
