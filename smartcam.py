#!/usr/bin/env python
import numpy
import multiprocessing
import os,time
import conf.default as conf
import lib.core as core
import lib.service as service
import Queue
import logging

def main():

    logging.basicConfig(level=service.get_loglevel(os.environ['LOG_LEVEL']))

    coreobj = core.Core()
    mgr = multiprocessing.Manager()
    namespace = mgr.Namespace()
    configuration = {}

    configuration['frame_gap_sec_max'] = 3.0
    configuration['ENC_QUEUE_SIZE'] = 10
    configuration['MAX_QUEUE_SIZE'] = 5

    configuration['AFD_FRAME_BUF_SIZE'] = 8
    configuration['MATCHER_BUF_SIZE'] = 20
    configuration['CAM_WIDTH'] = 1280
    configuration['CAM_HEIGHT'] = 720

    configuration['frame_shrink_rate'] = int(os.environ['FRAME_SHRINK_RATE']) # 1,2,4,8,  larger number -> faster detection and face need to be closer to the camera
    configuration['frame_shrink_rate_preprocess'] = int(os.environ['FRAME_SHRINK_RATE_PREPROC']) # 1,2,4,8,  larger number -> faster detection and face need to be closer to the camera
    configuration['consecutive_frames_tocheck'] = 2 # face recognition need to be checked in no of consecutive frames before trigger the event
    configuration['event_supress_ms'] = 60000 # same face will not trigger the event again in this time frame

    configuration['show_frames'] = (os.environ['SHOW_FRAMES'] == 'YES') #True
    configuration['show_detection_box'] = (os.environ['SHOW_FRAMES'] == 'YES') #True
    configuration['CAM_DEV_ID'] = int(os.environ['CAM_DEV_ID']) #True

    if os.environ['MODE'] == 'LOGGING':
        logging.info(('SYSTEM is in mode: ',os.environ['MODE']))
        configuration['t_min'] = 0.25
        configuration['t_max'] = 0.52
        configuration['t_default'] = 0.35
        configuration['t_adjust_step'] = 0.03
    elif os.environ['MODE'] == 'SURVEILANCE':
        logging.info(('SYSTEM is in mode: ',os.environ['MODE']))
        configuration['t_min'] = 0.3
        configuration['t_max'] = 0.57
        configuration['t_default'] = 0.5
        configuration['t_adjust_step'] = 0.03
    else:
        logging.info(('SYSTEM is in mode: ',os.environ['MODE']))
        configuration['t_min'] = 0.3     # face will be Unknown when tolerance decreases to this min value, i.e. same face matches multiple name can be an error
        configuration['t_max'] = 0.54    # face will be Unknown when tolerance increases to this max value
        configuration['t_default'] = 0.4 # tolerance to start with
        configuration['t_adjust_step'] = 0.04 # tolerance adjustment step


    namespace.conf = configuration

    q_enc = multiprocessing.Queue(configuration['ENC_QUEUE_SIZE'])
    q_encoded = multiprocessing.Queue(configuration['MAX_QUEUE_SIZE'])
    q_matched = multiprocessing.Queue(configuration['MAX_QUEUE_SIZE'])

    namespace.loadfaces = True
    namespace.faces_loaded =  {'known_face_names':[],'known_face_encodings':[]}
    namespace.frames_buffer = []
    namespace.face_matched = {'id':0,'frame':numpy.ndarray((configuration['CAM_WIDTH'], configuration['CAM_HEIGHT'], 3)),'face_locations':[],'names':[]}

    # namespace.faces_detected = {'id':0,'frame':numpy.ndarray((configuration['CAM_WIDTH'], configuration['CAM_HEIGHT'], 3)),'face_locations':[],'face_encodings':[]}
    # namespace.match_inprocess = []
    # namespace.event_inprocess = []

    namespace.frame_have_face = 0.0
    namespace.contourArea = 9999999
    namespace.laplacianSwitch = 0.0

    fe = multiprocessing.Process(target=coreobj.face_encoder, args=(namespace,q_enc,q_encoded))
    fm = multiprocessing.Process(target=coreobj.face_matcher, args=(namespace,q_encoded,q_matched))
    et = multiprocessing.Process(target=coreobj.event_trigger, args=(namespace,q_matched))
    fl = multiprocessing.Process(target=coreobj.face_loader, args=(namespace,))


    # slas is a list of SLA for afd process to achieve
    slas = [0.5,5.5,0.6,6.5,0.7,7.5]

    worst_sla = max(slas)
    afd_queue_length_seconds = min((worst_sla * 2), 5)

    frame_queues = []
    afds = [None] * len(slas)
    for qi,sla in enumerate(slas):
        q_len = min(max(2,int(afd_queue_length_seconds/sla)),10)
        logging.debug(('preparing adf process: ', qi, sla, q_len))
        queue_fr = multiprocessing.Queue(q_len)
        frame_queues.append(queue_fr)
        afds[qi] = multiprocessing.Process(target=coreobj.auto_face_detector, args=(namespace,sla, 8.8, frame_queues[qi], q_enc))

    fqi = multiprocessing.Process(target=coreobj.frame_queue_input, args=(namespace,frame_queues))


    try:

        for afd in afds:
            afd.start()
        fqi.start()
        fl.start()
        fe.start()
        fm.start()
        et.start()

        for afd in afds:
            afd.join()
        fqi.join()
        fl.join()
        fe.join()
        fm.join()
        et.join()

    except KeyboardInterrupt:
        logging.info("Caught KeyboardInterrupt, terminating processes")

        for afd in afds:
            afd.terminate()
        fqi.terminate()
        fl.terminate()
        fe.terminate()
        fm.terminate()
        et.terminate()

        for afd in afds:
            afd.join()
        fqi.join()
        fl.join()
        fe.join()
        fm.join()
        et.join()
        logging.info("All processes stopped.....")


if __name__ == "__main__":
    main()
