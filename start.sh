#!/bin/bash
export ENV=PROD
# export MODE=LOGGING
# export MODE=SURVEILANCE
export MODE=DEFAULT

# Email configuration below will override conf/default.py

# export SMTP_SERVER=smtp.live.com
# export SMTP_PORT=587
# export EMAIL_USER=test.user@outlook.com
# export EMAIL_PASS=password
# export EMAIL_LIST=xxx@yyy.zzz

python2.7 smartcam.py
