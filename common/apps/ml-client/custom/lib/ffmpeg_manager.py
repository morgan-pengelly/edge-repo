"""Thread and Jobs for submission to Ffmpeg for processing."""
## Currently uses FFMPEG for core functionality but does not use GPU acceleration:
# https://docs.nvidia.com/video-technologies/video-codec-sdk/ffmpeg-with-nvidia-gpu/
import threading
import os
import time
from queue import Queue
import ffmpeg
import core.util as util
from core.models.models import Camera, DataFile, Event


client_config = util.client_config
logger = util.log.setup_logger(__name__, client_config["ffmpeg-log"])


class FramesJob(object):
    """Job for extracting frames from videos using ffmpeg."""

    def __init__(self, file: DataFile, camera: Camera = None):
        self.file: DataFile = file
        self.camera = camera
        # If framerate is undefined return single frame from video.
        if camera is not None:
            self.framerate = camera.frames_per_day / (8 * 60 * 60)
        else:
            self.framerate = 0.0000001

    def run(self):
        """ """
        output_folder = self.file.start_time.strftime("%Y-%m-%d")
        output_name = self.file.start_time.strftime("%H-%M-%S") + r"_frm-%d.jpg"
        output_location = f"data/upload/frames/{self.file.source}/{output_folder}/"
        if not os.path.exists(output_location):
            os.makedirs(output_location)
        output_location = output_location + output_name
        print(output_location)
        try:
            (
                ffmpeg.input(self.file.path)
                .filter("fps", fps=self.framerate)
                # We need images of uniform size for training.
                .filter("scale", width="1280", height="720")
                .output(
                    output_location,
                    start_number=0,
                    preset="ultrafast",
                )
                .run(capture_stdout=True, capture_stderr=True)
            )
        except ffmpeg.Error as excp:
            logger.error(
                "FFMPEG error during FramesJob captured stderr:"
                + excp.stderr.decode("utf8")
            )


class EventVideoJob(object):
    def __init__(self, videos: list[DataFile], event: Event, quiet: bool = True):
        self.videos = videos
        self.event = event
        self.quiet = quiet

    def run(self):
        """Trim a list of videos based on given event"""
        input_file = ffmpeg.input(self.videos[0].path)

        trim_start = (
            self.event.start_time() - self.videos[0].start_time
        ).total_seconds()
        trim_end = (self.event.end_time() - self.videos[0].start_time).total_seconds()
        # print(f"trim_start = {trim_start} seconds")
        # print(f"trim_end = {trim_end} seconds")

        pts = "PTS-STARTPTS"
        trim = input_file.trim(start=trim_start, end=trim_end).setpts(pts)

        # If there is more than one video file
        if len(self.videos) > 1:
            # Ensure list of videos to trim isnt passed more than 2 files.
            if len(self.videos) != 2:
                raise Exception
            # print("Concatinating")
            input_file_opt = ffmpeg.input(self.videos[1].path)
            trim_opt_end = (
                self.event.end_time() - self.videos[1].start_time
            ).total_seconds()
            # print(f"trim_opt_end = {trim_opt_end} seconds")
            trim_opt = input_file_opt.trim(start=0, end=trim_opt_end).setpts(pts)
            output = ffmpeg.concat(trim, trim_opt)
        else:
            output = trim

        # Ensure directory for ffmpeg output exists otherwise will fail.
        output_dest = f"./data/upload/events/{self.videos[0].source}/"
        if not os.path.exists(output_dest):
            os.makedirs(output_dest)
        # Create output file
        output_path = f"{output_dest}event{self.event.id}_output.mp4"
        output_file = ffmpeg.output(
            output, output_path, format="mp4", vcodec="libx264", preset="ultrafast"
        )
        try:
            ffmpeg.run(
                output_file,
                overwrite_output=True,
                quiet=False,
                capture_stdout=True,
                capture_stderr=True,
            )
        except ffmpeg.Error as excp:
            logger.info("stdout: %s", excp.stdout.decode("utf8"))
            logger.info("stderr: %s", excp.stderr.decode("utf8"))
            time.sleep(1)
            raise excp
        self.event.delete_from_log()


class FfmpegManager(threading.Thread):
    """Manages ffmpeg jobs for video file processing."""

    def __init__(self, job_queue: Queue):
        self.enabled = False
        self.job_queue = job_queue
        super().__init__()

    def run(self):
        while True:
            if self.enabled:
                time.sleep(1)
                if not self.job_queue.empty():
                    job = self.job_queue.get()
                    job.run()
                else:
                    logger.info("ALL JOBS FINISHED")
                    self.disable()

    def enable(self):
        """Enables thread to begin processing job que"""
        self.enabled = True

    def disable(self):
        """Disables thread from starting another job."""
        self.enabled = False


if __name__ == "__main__":
    q = Queue()
    events: list[Event] = util.log.import_event_log(
        "./logs/EventTest.log", "./custom/eventConfig.yml"
    )
    manager = FfmpegManager(q)
    manager.start()

    for event in events:
        print(event.get_files())
        q.put(EventVideoJob(event.get_files(), event))

    manager.enable()
    q.join()

    # q.put(EventVideoJob())
    # worker = FfmpegManager(q)
    # worker.start()
    # print("Created Video Worker...")
    # print("Waiting to enable q")
    # time.sleep(3)
    # print(Fore.GREEN + "enabling worker" + Fore.RESET)
    # worker.enable()
    # time.sleep(20)
