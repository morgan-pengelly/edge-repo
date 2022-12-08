"""Schedule Library reference project: https://github.com/danirus/async-apscheduler-fastapi"""
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import core.util as util
import core.util.log_util as log

client_config = util.client_config
logger = log.setup_logger(__name__, client_config["scheduler-log"])


async def scheduler_heartbeat():
    """Test Method"""
    logger.info("Scheduler Heartbeat")


class SchedulerService:
    """Scheduler for creating task scheduling."""

    def __init__(self) -> None:
        self.queue = asyncio.Queue()
        SchedulerService.sch = AsyncIOScheduler()

    def start(self):
        """Run heartbeat job."""
        self.sch.start()
        self.sch.add_job(
            scheduler_heartbeat,
            "interval",
            seconds=10,
            # Using max_instances=1 guarantees that only one job
            # runs at the same time (in this event loop).
            max_instances=1,
        )


if __name__ == "__main__":
    print("Test")
