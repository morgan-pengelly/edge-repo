import ffmpeg
import os


def record_stream():

    stream_path = "rtsp://admin:LegoBird3!@10.10.10.120:554"
    output_path = os.path.join(os.sys.path[0], "%Y-%m-%d_%H-%M-%S.mp4")

    try:
        (
            ffmpeg.input(stream_path, rtsp_transport="tcp", stimeout="1000000")
            # We need images of uniform size for training.
            .filter("scale", width="1280", height="720")
            # .filter("boxblur","'min(min(cw/2\,ch/2)\,10)'[b0];[bg][b0]overlay=20*W/800:10*W/800")
            # .filter("boxblur", luma_power="1", chroma_radius= "min(cw,ch)/20", chroma_power="1[bg][0:v]overlay=(W-w)/2:(H-h)/2") #, overlay="(W-w)/2:(H-h)/2"
            # .filter("crop", out_w = "400", out_h = "200", x = "400", y = "300")
            .drawbox(
                x="400",
                y="400",
                width="400",
                height="400",
                color="0x000000",
                thickness="fill",
            )
            .output(
                output_path,
                f="segment",  # Video output will segment
                strftime="1",  # enable strftime segment naming
                segment_time="00:00:10",  # define segment length
                reset_timestamps="1",  # reset timestamps in each segment
                segment_format="mp4",  # output format
                preset="ultrafast",
            )
            .run(capture_stdout=False, capture_stderr=False)
        )
    except ffmpeg.Error as excp:
        print(
            "FFMPEG error during RecordStream captured stderr:"
            + excp.stderr.decode("utf8")
        )


if __name__ == "__main__":
    record_stream()
    print("DONE")
