import ffmpeg
from core.models.models import Event, DataFile


async def trim_videos(videos: list[DataFile], event: Event, quiet: bool = True):
    """Trim a list of videos based on given event"""
    input_file = ffmpeg.input(videos[0].path)

    trim_start = (event.start_time() - videos[0].start_time).total_seconds()
    trim_end = (event.end_time() - videos[0].start_time).total_seconds()
    # print(f"trim_start = {trim_start} seconds")
    # print(f"trim_end = {trim_end} seconds")

    pts = "PTS-STARTPTS"
    trim = input_file.trim(start=trim_start, end=trim_end).setpts(pts)

    # If there is more than one video file
    if len(videos) > 1:
        # Ensure list of videos to trim isnt passed more than 2 files.
        if len(videos) != 2:
            raise Exception
        print("Concatinating")
        input_file_opt = ffmpeg.input(videos[1].path)
        trim_opt_end = (event.end_time() - videos[1].start_time).total_seconds()
        print(f"trim_opt_end = {trim_opt_end} seconds")
        trim_opt = input_file_opt.trim(start=0, end=trim_opt_end).setpts(pts)
        output = ffmpeg.concat(trim, trim_opt)
    else:
        output = trim

    # Create output file
    output_path = f"event{event.id}_output.mp4"
    output_file = ffmpeg.output(output, output_path, format="mp4")
    await ffmpeg.run(output_file, overwrite_output=True, quiet=quiet)


if __name__ == "__main__":
    pass
