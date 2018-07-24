#!/usr/bin/env python
import os


def setenv(env_viriable,value,override=False):
    if env_viriable not in os.environ:
        print 'setting ', env_viriable, 'to: ', value
        os.environ[env_viriable] = value
    elif override:
        print 'overriding ', env_viriable, 'from: ' , os.environ[env_viriable] , 'to: ', value
        os.environ[env_viriable] = value
    else:
        print env_viriable, 'has been set to: ', os.environ[env_viriable], ' skipping setting to: ', value

def setenv_dev():
    setenv('MODE','LOGGING') # LOGGING | SURVEILANCE | DEFAULT
    setenv('ENV','DEV')
    setenv('LOG_LEVEL','DEBUG')
    setenv('FRAME_SHRINK_RATE','1')
    setenv('FRAME_SHRINK_RATE_PREPROC','1')
    setenv('FACE_PHOTO_LOC','facephotos/')
    setenv('FACE_LOG_LOC','facelog/')
    setenv('CAM_DEV_ID','0')
    setenv('OBJC_DISABLE_INITIALIZE_FORK_SAFETY','YES')
    setenv('SHOW_FRAMES','NO')
    setenv('SAVE_JSONLOG','YES', override=True)
    setenv('KEEP_LOCAL_PHOTO','YES')
    # setenv('AWS_DEFAULT_REGION','ap-southeast-2')
    # setenv('AWS_SES_REGION','us-west-2')
    # setenv('AWS_ACCESS_KEY_ID','xxx')
    # setenv('AWS_SECRET_ACCESS_KEY','xxxx')
    # setenv('S3_BUCKET','photolog-xxx')

    # please update SMTP server settings before running the programe
    setenv('SMTP_SERVER','smtp.live.com')
    setenv('SMTP_PORT','587')
    setenv('EMAIL_USER','xxxx.xxxx@outlook.com')
    setenv('EMAIL_PASS','xxxx')
    setenv('EMAIL_LIST','xxxx@hotmail.com')

def setenv_prod():
    setenv('ENV','PROD')
    setenv('LOG_LEVEL','INFO')
    setenv('MODE','LOGGING')    # LOGGING | SURVEILANCE | DEFAULT
    setenv('FRAME_SHRINK_RATE','1')
    setenv('FRAME_SHRINK_RATE_PREPROC','1')
    setenv('FACE_PHOTO_LOC','facephotos/')
    setenv('FACE_LOG_LOC','facelog/')
    setenv('CAM_DEV_ID','0')
    setenv('OBJC_DISABLE_INITIALIZE_FORK_SAFETY','YES')
    setenv('SHOW_FRAMES','NO')
    setenv('SAVE_JSONLOG','NO')
    setenv('KEEP_LOCAL_PHOTO','NO')
    # setenv('AWS_DEFAULT_REGION','ap-southeast-2')
    # setenv('AWS_SES_REGION','us-west-2')
    # setenv('AWS_ACCESS_KEY_ID','xxx')
    # setenv('AWS_SECRET_ACCESS_KEY','xxxx')
    # setenv('S3_BUCKET','photolog-xxx')

    # please update SMTP server settings before running the programe
    setenv('SMTP_SERVER','smtp.live.com')
    setenv('SMTP_PORT','587')
    setenv('EMAIL_USER','xxxx.xxxx@outlook.com')
    setenv('EMAIL_PASS','xxxx')
    setenv('EMAIL_LIST','xxxx@hotmail.com')

def init(env):
    envmap = {'DEV': setenv_dev,'PROD': setenv_prod}
    if env in envmap:
        print 'load environemnt: ', env
        envmap[env]()
    else:
        print env, ' not defined!'

if 'ENV' in os.environ:
    init(os.environ['ENV'])
else:
    init('DEV')

if ('AWS_DEFAULT_REGION' in os.environ and len(os.environ['AWS_DEFAULT_REGION']) > 5 and 'AWS_ACCESS_KEY_ID' in os.environ and 'AWS_SECRET_ACCESS_KEY' in os.environ and len(os.environ['AWS_ACCESS_KEY_ID']) > 5 and len(os.environ['AWS_SECRET_ACCESS_KEY']) > 5):
    os.environ['NO_AWS_CONF'] = 'NO'
else:
    os.environ['NO_AWS_CONF'] = 'YES'
