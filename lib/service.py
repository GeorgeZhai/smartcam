#!/usr/bin/env python
import cv2
import os
import time
import tzlocal
import datetime
import pickle
import traceback
import json
import boto3
import base64
import numpy
import logging
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEImage import MIMEImage


def get_loglevel(level = "INFO"):
    LOG_LEVEL_MAP = {"CRITICAL": logging.CRITICAL,
            "ERROR": logging.ERROR,
            "WARNING": logging.WARNING,
            "INFO": logging.INFO,
            "DEBUG": logging.DEBUG,
            "NOTSET": logging.NOTSET}
    return LOG_LEVEL_MAP[level]

logging.basicConfig(level=get_loglevel(os.environ['LOG_LEVEL']))

def del_old_img(face_log_folder="facelog/",minutes=1440):
    if os.environ['KEEP_LOCAL_PHOTO'] != 'YES':
        for dirpath, dirnames, filenames in os.walk(face_log_folder):
            for file in filenames:
                curpath = os.path.join(dirpath, file)
                file_modified = datetime.datetime.fromtimestamp(os.path.getmtime(curpath))
                if datetime.datetime.now() - file_modified > datetime.timedelta(minutes=minutes):
                    logging.info('removing old file: ' + curpath)
                    os.remove(curpath)


def save_img(frame, face_log_folder="facelog/", face_log_prefix="cam", ts_ms = 1000):
    current_ts = int(time.time() * 1000 / ts_ms)
    jpgfn = face_log_prefix + str(current_ts) + '.jpg'
    jpgfnfull = face_log_folder + jpgfn
    cv2.imwrite(jpgfnfull, frame)
    s3link = ""
    signed_url = ""
    if os.environ['NO_AWS_CONF'] == 'YES':
        logging.info('no AWS configuration found, here suppose to save photo' + str(jpgfnfull) + ' into S3: ' +  str(s3link))
        return jpgfnfull, s3link
    s3link = "https://s3-" + os.environ['AWS_DEFAULT_REGION'] + ".amazonaws.com/" + os.environ['S3_BUCKET'] + "/" + jpgfn
    signed_url = s3link
    try:
        s3_client = boto3.client('s3')
        logbucket = os.environ['S3_BUCKET']
        s3_client.upload_file(jpgfnfull, logbucket, jpgfn)
        signed_url = s3_client.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': logbucket,
                'Key': jpgfn
            },
            ExpiresIn=(3600*12)
        )
    except Exception as e:
        traceback.print_exc(e)
    else:
        logging.info('file uploaded to: '+ str(s3link))

    return jpgfnfull, signed_url


def send_email_smtp(to, message):
    result = False
    try:
        SMTP_SERVER=os.environ['SMTP_SERVER']
        SMTP_PORT=int(os.environ['SMTP_PORT'])
        EMAIL_USER=os.environ['EMAIL_USER']
        EMAIL_PASS=os.environ['EMAIL_PASS']
        logging.info(' send_email_smtp - ' + SMTP_SERVER + str(SMTP_PORT) + EMAIL_USER)
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(EMAIL_USER, EMAIL_PASS)
        res = server.sendmail(EMAIL_USER, to, message)
        server.close()
        logging.info(' send_email_smtp - end of sending email --------------------!')
        logging.info(res)
        result = True
    except Exception as e:
        logging.info(' send_email_smtp - found exception in sending email')
        logging.error(e)
        pass

    return result


def email_notify_first_show_smtp(names_obj):
    names_list = names_obj.keys()

    if 'EMAIL_LIST' not in os.environ or os.environ['EMAIL_LIST']=='':
        logging.info('EMAIL_LIST not set - function disabled')
        return

    email_to = os.environ['EMAIL_LIST'].split(',')
    email_from = os.environ['EMAIL_USER']

    if len(names_list) == 0 or len(email_to) == 0 or len(email_from) == 0:
        return
    else:
        names_str = ', '.join(names_list)
        photofn = names_obj[names_list[0]]['photo']
        email_subject = 'smartcam event - ' + names_str + ' has showed up'
        email_body_text = names_str + ' showed up! '
        msgRoot = MIMEMultipart('related')
        msgRoot['Subject'] = email_subject
        msgRoot['From'] = email_from
        msgRoot['To'] = ';'.join(email_to)
        msgRoot.preamble = 'This is a multi-part message in MIME format.'
        msgAlternative = MIMEMultipart('alternative')
        msgRoot.attach(msgAlternative)
        msgText = MIMEText('<b>' + names_str + ' <i>  showed up! </i> </b> <br><img src="cid:image1"><br>', 'html')
        msgAlternative.attach(msgText)
        msgImage = None
        try:
            fp = open(photofn, 'rb')
            msgImage = MIMEImage(fp.read())
            fp.close()
        except Exception as e:
            logging.error(e)
            return
            pass
        msgImage.add_header('Content-ID', '<image1>')
        msgRoot.attach(msgImage)
        send_email_smtp(msgRoot['To'], msgRoot.as_string())
        return

def email_notify_unknown_smtp(names_obj,unknown_img_fns=[]):
    names_list = names_obj.keys()

    if 'EMAIL_LIST' not in os.environ or os.environ['EMAIL_LIST']=='':
        logging.info('EMAIL_LIST not set - function disabled')
        return

    email_to = os.environ['EMAIL_LIST'].split(',')
    email_from = os.environ['EMAIL_USER']

    if len(names_list) == 0 or len(email_to) == 0 or len(email_from) == 0:
        return
    else:
        names_str = ', '.join(names_list)
        photofn = names_obj[names_list[0]]['photo']
        email_subject = 'smartcam event - ' + names_str + ' has been detected'
        email_body_text = names_str + ' detected! '
        msgRoot = MIMEMultipart('related')
        msgRoot['Subject'] = email_subject
        msgRoot['From'] = email_from
        msgRoot['To'] = ';'.join(email_to)
        msgRoot.preamble = 'This is a multi-part message in MIME format.'
        msgAlternative = MIMEMultipart('alternative')
        msgRoot.attach(msgAlternative)

        msgText_org = '<b>' + names_str + ' <i>  detected! </i> </b> <br><img src="cid:image1"><br>'
        msgText = MIMEText(msgText_org, 'html')
        msgImage = None
        try:
            fp = open(photofn, 'rb')
            msgImage = MIMEImage(fp.read())
            fp.close()
        except Exception as e:
            logging.error(e)
            return
            pass
        msgImage.add_header('Content-ID', '<image1>')
        msgRoot.attach(msgImage)
        send_email_smtp(msgRoot['To'], msgRoot.as_string())
        return


def loaddata(filename):
    data = {}
    try:
        fh = open(filename, 'r')
    except Exception as e:
        # traceback.print_exc(e)
        del_old_img()
        logging.info('cannot open: ' + str(filename) + ' will start a new one')
    else:
        try:
            data = pickle.load(fh)
        except Exception as e:
            traceback.print_exc(e)
        else:
            logging.info('data loaded from: ' + str(filename))
        fh.close()
    return data


def savedata(data, filename):
    try:
        fh = open(filename, 'w+')
    except Exception as e:
        traceback.print_exc(e)
    else:
        try:
            pickle.dump(data, fh, protocol=2)
        except Exception as e:
            traceback.print_exc(e)
        else:
            logging.info('data saved to : ' +  str(filename))
        fh.close()


def savejsondata(data, filename):
    try:
        fh = open(filename, 'w+')
    except Exception as e:
        traceback.print_exc(e)
    else:
        try:
            json.dump(data, fh)
        except Exception as e:
            traceback.print_exc(e)
        else:
            logging.info('data saved to json file: ' + str(filename))
        fh.close()


def check_and_update_log(face_names, frame, current_ts, logdata_folder="facelog/"):
    local_timezone = tzlocal.get_localzone()
    local_time = datetime.datetime.fromtimestamp(current_ts / 1000.0, local_timezone)
    local_time_str = local_time.strftime("%Y-%m-%d %H:%M:%S.%f%z (%Z)")
    local_time_day_str = local_time.strftime("%Y-%m-%d")
    logfn = logdata_folder + 'log-' + local_time_day_str + '.pkl'
    jsonlogfn = logdata_folder + 'log-' + local_time_day_str + '.json'

    logdata = loaddata(logfn)
    # check if image should be saved
    imgfn = ''
    s3link = ''
    should_save_img = False
    for n in face_names:
        if (n not in logdata) or n in ['Unknown']:
            should_save_img = True
            break

    if should_save_img:
        imgfn, s3link = save_img(frame, face_log_folder=os.environ['FACE_LOG_LOC'])
        logging.info('image saved: ' + str(imgfn) + str(s3link))

    names_firsttime_showup = {}
    Unknown_face_showup = {}
    for n in face_names:
        record = {"ts": current_ts, "datetime": local_time_str, "photo": imgfn, "s3link": s3link}
        if n not in logdata:
            logdata[n] = []
            if n not in ['Unknown']:
                names_firsttime_showup[n] = record
        if n in ['Unknown']:
            Unknown_face_showup[n] = record
        logdata[n].append(record)

    savedata(logdata, logfn)
    if os.environ['SAVE_JSONLOG'] == 'YES':
        savejsondata(logdata, jsonlogfn)
    return names_firsttime_showup, Unknown_face_showup

def scale_back_location(location):
    frame_shrink_rate = int(os.environ['FRAME_SHRINK_RATE'])
    ht,wr,hb,wl=location
    ht *= frame_shrink_rate
    wr *= frame_shrink_rate
    hb *= frame_shrink_rate
    wl *= frame_shrink_rate
    return (ht,wr,hb,wl)

def scale_location_rate(frame_shape,location,frame_shrink_rate=1,rate=1.5):
    h=frame_shape[0]
    w=frame_shape[1]
    ht,wr,hb,wl=location
    ht *= frame_shrink_rate
    wr *= frame_shrink_rate
    hb *= frame_shrink_rate
    wl *= frame_shrink_rate
    nh = ((hb-ht)*1.0/h)*h*rate
    nw = ((wr-wl)*1.0/w)*w*rate
    hc = (hb-ht)/2 + ht
    wc = (wr-wl)/2 + wl
    nht = long(numpy.clip((hc - nh/2),0,h))
    nhb = long(numpy.clip((hc + nh/2),0,h))
    nwl = long(numpy.clip((wc - nw/2),0,w))
    nwr = long(numpy.clip((wc + nw/2),0,w))
    return (nht,nwr,nhb,nwl)

def crop_frame(frame,location,rate=1.5):
    h=frame.shape[0]
    w=frame.shape[1]
    ht,wr,hb,wl=location
    nh = ((hb-ht)*1.0/h)*h*rate
    nw = ((wr-wl)*1.0/w)*w*rate
    hc = (hb-ht)/2 + ht
    wc = (wr-wl)/2 + wl
    nht = long(numpy.clip((hc - nh/2),0,h))
    nhb = long(numpy.clip((hc + nh/2),0,h))
    nwl = long(numpy.clip((wc - nw/2),0,w))
    nwr = long(numpy.clip((wc + nw/2),0,w))
    return frame[nht:nhb,nwl:nwr]

def event_trigger(face_names, face_locations, frame, current_ts):
    names_firsttime, Unknown_face = check_and_update_log(face_names, frame, current_ts, logdata_folder=os.environ['FACE_LOG_LOC'])
    blurry_tolerance = 150
    if len(names_firsttime.keys()) > 0:
        logging.info('Found names first show up today  ' + str(names_firsttime))
        if os.environ['MODE'] != 'SURVEILANCE':
            email_notify_first_show_smtp(names_firsttime)
    if len(Unknown_face.keys()) > 0:
        logging.info('Found unknown faces: ' + str(Unknown_face))
        unknown_img_fns = []
        for i,n in enumerate(face_names):
            if n == 'Unknown':
                unknown_face_croped = crop_frame(frame,scale_back_location(face_locations[i]))
                blurry_value = cv2.Laplacian(unknown_face_croped, cv2.CV_64F).var()
                if blurry_value > blurry_tolerance:
                    imgfn_unkwn, s3link_unkwn = save_img(unknown_face_croped, face_log_folder=os.environ['FACE_LOG_LOC'], face_log_prefix="Unknown")
                    unknown_img_fns.append(imgfn_unkwn)
                else:
                    logging.info('skipping saving this photo, too bur:' + str(blurry_value))
        if os.environ['MODE'] != 'LOGGING':
            email_notify_unknown_smtp(Unknown_face,unknown_img_fns)


def face_detected(face_names, face_locations, frame, last_event_triggered_face_names, last_event_triggered_ts, event_supress_ms=20000):
    if (set(last_event_triggered_face_names) != set(face_names) or (int(time.time() * 1000) - last_event_triggered_ts) > event_supress_ms):
        logging.info('time to trigger event for : ' +   ', '.join(face_names))
        current_ts = int(time.time() * 1000)
        event_trigger(face_names, face_locations, frame, current_ts)
        return current_ts
    else:
        # print 'suprresing event trigger, time to last event: ',  int(time.time() * 1000) - last_event_triggered_ts
        return last_event_triggered_ts
