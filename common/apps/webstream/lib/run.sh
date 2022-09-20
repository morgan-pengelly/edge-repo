#!/bin/sh
cd /home/edge/lib
exec gst-launch-1.0 -q rtspsrc location="rtsp://user:pass@jetson:554/ds-test" latency=10 ! queue ! rtpvp9depay ! webmmux streamable=true ! tcpserversink host="0.0.0.0" port="8080" recover-policy=keyframe sync-method=latest-keyframe  >/dev/null 2>&1
