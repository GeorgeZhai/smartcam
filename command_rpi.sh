#!/bin/bash

docker run --name smartcam -idt --log-driver json-file --log-opt max-size=10m --device /dev/video0:/dev/video0 -v /home/pi/workspace/smartcam:/app -e "TZ=Australia/Sydney" --restart unless-stopped georgezhai/rpi_python2_opencv:v0.1 bash start.sh

#docker run --name smartcam -idt --log-driver json-file --log-opt max-size=10m --device /dev/video0:/dev/video0 -v /home/pi/workspace/smartcam:/app -e "TZ=Australia/Sydney" --restart unless-stopped georgezhai/rpi_python2_opencv:v0.1 bash start_debug.sh
