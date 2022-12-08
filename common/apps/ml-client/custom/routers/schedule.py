"""API for all Scheduler tasks."""
from fastapi import APIRouter, Response, status

import core.util as util
import core.util.log_util as log  # Library for all logging utilities using "logging"

from custom.lib import scheduler
from custom.routers import video
from custom.routers import upload
from custom.routers import update

# Import configuration YAML file as global config variable.
client_config = util.client_config

# create Router for schedule commands
router = APIRouter(prefix="/schedule")
logger = log.setup_logger(__name__, client_config["api-log"])
sch_srv = scheduler.SchedulerService()

# STARTUP MOVED TO USE FUNCTIONS DEFINED IN MODULE.
async def end_of_day_routine():
    try:
        await video.get_event_jobs()
        await video.get_frame_jobs()
        await video.run_jobs()
        await upload.upload_all_data(Response())
        await update.update_configs(Response())
    except:
        pass


@router.get("/run-end-of-day", status_code=status.HTTP_202_ACCEPTED, tags=["upload"])
def eod():
    end_of_day_routine()


@router.on_event("startup")
def startup_event():
    """Add all scheduled tasks here."""
    sch_srv.sch.add_job(
        end_of_day_routine,
        "cron",
        hour=21,
        # Using max_instances=1 guarantees that only one job
        # runs at the same time (in this event loop).
        max_instances=1,
    )
    sch_srv.start()
