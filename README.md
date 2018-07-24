# smartcam
Use Mac or RaspberryPi camera to detect and recognise faces in realtime and notify users by email

This app:
  1. Recognise faces in real-time from camera.
  2. Trigger events on the faces recognised
      default actions are: (depends on MODE: 'LOGGING' | 'SURVEILANCE' | 'DEFAULT')
          a. sends email notification when known faces detected first time of the day (can be used for automated check-in ... LOGGING mode)
          b. sends email notification whenever unknown faces detected. (can be used for neighbourhood surveillance SURVEILANCE mode)
          c. or both (DEFAULT mode)
  3. Optimised for RaspberryPi performance:
          a. Use multiple cores with queues and multiples preprocessors - auto adjust frame shrinking rate to avoid high latency
          b. Motion triggered frame process - auto adjust threshold to avoid long queueing
          c. Auto select sharper frames to avoid processing too much frames

This app has been tested in MacBookPro and RaspberryPi 2 and 3


This app uses:
  face_recognition for face recognition
  OpenCV for webcam
  Smtplib for sending email. (Optionally can use boto3 for using AWS S3/SES to send Email)

This app improves the recognition accuracy by:
  a. Auto adjust face matching tolerance
  b. Use multiple photos to improve the recognition rate
  c. Use multi frames to decrease the false matching


HOW TO USE:

1.	Edit start.sh or conf/default.py to add configuration for SMTP_SERVER, SMTP_PORT, EMAIL_USER, EMAIL_PASS, EMAIL_LIST(comma separated string for multiple emails)
2.	Add users photos into facephotos/<names>/ (multiple names and multiple photos per name are supported, JPG and PNG are supported)

For MAC users:
3.	pip install -r requirements.txt
4.	./start.sh

For RaspberryPi users:
3.	Install Docker on Raspbian
4.	Copy or checkout code into /home/pi/workspace/smartcam (remember to edit EMAIL configure)
5.	docker run --name smartcam -idt --log-driver json-file --log-opt max-size=10m --device /dev/video0:/dev/video0 -v /home/pi/workspace/smartcam:/app -e "TZ=Australia/Sydney" --restart unless-stopped georgezhai/rpi_python2_opencv:v0.1 bash start.sh

Docker images:
	The image preinstalled opencv and other required packages for the armv7, Dockerfile is here:  https://github.com/GeorgeZhai/rpi_python2_opencv

Future plans:

 	Server code to use API instead of SMTP or local AWS configuration.
	Closed loop to let user tag unknow or mismatched photos.
	Video Streaming and recording function to the cloud.
	Remote software update from cloud
	Support more powerful hardware to use GPU for fast processing
