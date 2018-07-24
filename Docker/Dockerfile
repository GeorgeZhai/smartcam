FROM 	armv7/armhf-ubuntu:16.04

LABEL maintainer="George Zhai"

RUN 	apt-get update && apt-get upgrade -y

RUN		apt-get install -y --no-install-recommends build-essential

RUN		apt-get install -y --no-install-recommends cmake git libgtk2.0-dev pkg-config libavcodec-dev libavformat-dev libswscale-dev
RUN		apt-get install -y --no-install-recommends python2.7-dev python-pip python-setuptools
RUN		apt-get install -y --no-install-recommends libtbb2 libtbb-dev libjpeg-dev libpng-dev libtiff-dev libjasper-dev libdc1394-22-dev

RUN  	pip install --upgrade pip
RUN  	pip install numpy

#RUN		apt-get install -y --no-install-recommends python2.7-dev python3-dev python-pip build-essential cmake git pkg-config
#RUN		apt-get install -y --no-install-recommends libjpeg-dev libjpeg8-dev libtiff5-dev libjasper-dev libpng12-dev libgtk2.0-dev libavcodec-dev libavformat-dev libswscale-dev libv4l-dev libxvidcore-dev libx264-dev libatlas-base-dev libgtk-3-dev gfortran libavresample-dev libgphoto2-dev libgstreamer-plugins-base1.0-dev libdc1394-22-dev
#RUN    apt-get install --reinstall python-setuptools -y


RUN		cd /opt && \
		git clone https://github.com/opencv/opencv_contrib.git && \
		cd opencv_contrib && \
		git checkout 3.4.1 && \
		cd /opt && \
		git clone https://github.com/opencv/opencv.git && \
		cd opencv && \
		git checkout 3.4.1 && \
		mkdir build && \
		cd build && \
		cmake 	-D CMAKE_BUILD_TYPE=RELEASE \
			-D BUILD_NEW_PYTHON_SUPPORT=ON \
			-D CMAKE_INSTALL_PREFIX=/usr/local \
			-D INSTALL_C_EXAMPLES=OFF \
			-D INSTALL_PYTHON_EXAMPLES=OFF \
			-D OPENCV_EXTRA_MODULES_PATH=/opt/opencv_contrib/modules \
			-D PYTHON_EXECUTABLE=/usr/bin/python2.7 \
			-D BUILD_EXAMPLES=OFF /opt/opencv && \
		make -j $(nproc) && \
		make install && \
		ldconfig

RUN		apt-get purge -y git && \
		apt-get clean && rm -rf /var/lib/apt/lists/* && \
		rm -rf /opt/opencv*

RUN  	pip install face_recognition boto3 tzlocal imutils

# Create app directory
RUN   mkdir /app

# Define the working directory
WORKDIR   /app

CMD ["/bin/bash"]
