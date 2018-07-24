#!/usr/bin/env python
import face_recognition
import cv2
import numpy
import multiprocessing
import os
import collections
import time
import service as service
import Queue
import traceback
import logging

class Core:
    def __init__(self):
        logging.basicConfig(level=service.get_loglevel(os.environ['LOG_LEVEL']))
        # logging.basicConfig(level=logging.DEBUG)
        logging.info('creating Core object')

    def load_photos(self,facephoto_folder="facephotos/"):
        known_face_encodings = []
        known_face_names = []
        for namedir in os.listdir(facephoto_folder):
            if os.path.isdir(facephoto_folder + namedir):
                for f in os.listdir(facephoto_folder + namedir):
                    fext = f[-4:].upper()
                    fnoext = f #f[:-4]
                    if fext == '.JPG' or fext == '.PNG':
                        cache_fn = facephoto_folder + namedir + '/' + fnoext + '.pkl'
                        image_enc_temp0 = None
                        if os.path.isfile(cache_fn):
                            logging.info('loading from cache file: ' + str(cache_fn))
                            image_enc_temp0 = service.loaddata(cache_fn)
                        else:
                            fp = facephoto_folder + namedir + '/' + f
                            logging.info(' loading.. '+ str(namedir) + 'photo: ' +  str(fp))
                            image_temp = face_recognition.load_image_file(fp)
                            image_enc_temp = face_recognition.face_encodings(image_temp)
                            if len(image_enc_temp) > 0:
                                image_enc_temp0 = image_enc_temp[0]
                                service.savedata(image_enc_temp0,cache_fn)
                        if type(image_enc_temp0) == numpy.ndarray:
                            known_face_names.append(namedir)
                            known_face_encodings.append(image_enc_temp0)
                        else:
                            logging.info('No face found, skiping this one..' +  str(fp))
        return known_face_encodings, known_face_names

    def face_loader(self, ns):
        loopgap = 60
        logging.info('face_loader - process name'+ str(multiprocessing.current_process().name))
        while True:
            if ns.loadfaces:
                known_face_encodings, known_face_names = self.load_photos()
                ns.faces_loaded = {'known_face_names': known_face_names,'known_face_encodings': known_face_encodings}
                ns.loadfaces = False
                logging.info('face_loader: loaded...')
            time.sleep(loopgap)

    def frame_queue_input(self, ns, frame_queues):
        no_of_frame_queues = len(frame_queues)
        last_frame_id_in_queues = [0.0] * no_of_frame_queues
        avg_frame_gap_in_queues = [0.0] * no_of_frame_queues
        logging.info('frame_queue_input - process name: '+ str(multiprocessing.current_process().name) + str(no_of_frame_queues))
        video_capture = cv2.VideoCapture(ns.conf['CAM_DEV_ID'])
        logging.info("frame_queue_input - Frame default resolution: (" + str(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH)) + "; " + str(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) + ")")
        video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, ns.conf['CAM_WIDTH'])
        video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, ns.conf['CAM_HEIGHT'])
        frame_w = video_capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        frame_h = video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        logging.info("frame_queue_input - Frame resolution set to: (" + str(frame_w) + "; " + str(frame_h) + ")")
        frame_no = 0
        max_frame_no = no_of_frame_queues * 300
        frame_discarded = 0
        fps_count_start_time = time.time()
        show_frames = ns.conf['show_frames']
        show_detection_box = ns.conf['show_detection_box']

        avg = None
        delta_thresh = 5
        # min_area_start is the start point of threshold, it should auto adjust between min_area and ns.contourArea
        min_area_start = 100
        # frame_pre_afd_shrink to use a fixed width for detection to ensure the performance
        frame_pre_afd_shrink = frame_w / 180
        frame_no_motion_start = 0
        motion_trigger = 2
        min_area = min_area_start
        laplacian_frame_id = 0.0
        laplacian_switch_frame_gap_max = 0.4
        laplacian_values = []
        laplacian_value = 0.0

        logging.info("frame_queue_input - sleep for few seconds, wait for camera...")
        time.sleep(2)
        while True:
            ret = False
            contourArea = 9999999
            try:
                ret, frame = video_capture.read()
            except Exception as e:
                logging.error('frame_queue_input error....')
                pass

            if ret:

                frame_id = time.time()
                frame_no += 1

                q_idx = frame_no % no_of_frame_queues
                # if not frame_queues[q_idx].full():

                _start_detect = time.time()
                motion_locations = []
                motion_detected = False

                frame_pre_afd = cv2.resize(frame, (0, 0), fx=(1.0 / frame_pre_afd_shrink), fy=(1.0 / frame_pre_afd_shrink))
                gray = cv2.cvtColor(frame_pre_afd, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (21, 21), 0)
                laplacian_value = cv2.Laplacian(frame_pre_afd, cv2.CV_64F).var()

                if avg is None:
                    avg = gray.copy().astype("float")
                else:
                    cv2.accumulateWeighted(gray, avg, 0.5)
                    frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))
                    thresh = cv2.threshold(frameDelta, delta_thresh, 255, cv2.THRESH_BINARY)[1]
                    thresh = cv2.dilate(thresh, None, iterations=2)
                    cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    # cnts = cnts[0] if imutils.is_cv2() else cnts[1]
                    if len(cnts) > 1:
                        cnts = cnts[1]
                        if len(cnts) > 0:
                            for c in cnts:
                                ca = cv2.contourArea(c)
                                if ca > min_area:
                                    motion_detected = True
                                    contourArea = min(contourArea, ca)
                                    (x, y, w, h) = cv2.boundingRect(c)
                                    motion_locations.append((x, y, w, h))
                            if motion_detected:
                                frame_no_motion_start = frame_no
                            elif min_area > min_area_start:
                                min_area = min_area - 5

                frame_obj = {'id': frame_id, 'frame': frame,'contourArea': contourArea, 'laplacian_value': laplacian_value}

                push_frame_to_queue = False

                if frame_id - laplacian_frame_id >= laplacian_switch_frame_gap_max:
                    laplacian_frame_id = frame_id
                    laplacian_values = []
                    ns.laplacianSwitch = 0.0

                if motion_detected or (frame_no - frame_no_motion_start < motion_trigger):
                    push_frame_to_queue = True
                    if frame_id - laplacian_frame_id < laplacian_switch_frame_gap_max:
                        laplacian_values.append(laplacian_value)
                        laplacian_frame_id = frame_id
                        laplacian_values_len = len(laplacian_values)
                        if laplacian_values_len > 6:
                            laplacianSwitch = sorted(laplacian_values)[
                                int(laplacian_values_len * 2 / 3)]
                            ns.laplacianSwitch = laplacianSwitch
                            logging.debug("frame_queue_input - laplacianSwitch condition met " + str(laplacianSwitch))
                            if laplacian_values_len > 200:
                                laplacian_values = laplacian_values[-20:]
                        else:
                            ns.laplacianSwitch = 0.0
                    if ns.laplacianSwitch > 0 and laplacian_value < ns.laplacianSwitch:
                        push_frame_to_queue = False
                        logging.debug("frame_queue_input - laplacianSwitch stopped queuing this frame " + str(frame_id))

                if push_frame_to_queue:
                    logging.debug("frame_queue_input -  motion_detected or motion_triggered: " + str(motion_detected) + " " + str(frame_no - frame_no_motion_start < motion_trigger) + " "+ str(frame_id) + " put frame_obj to frame_queue: " + str(q_idx) + " id: " +  str(frame_id) +  "deplayed: " + str(time.time() - frame_id))
                    try:
                        frame_queues[q_idx].put(frame_obj, False)
                        last_frame_id_in_queues[q_idx] = frame_id
                    except Queue.Full:
                        frame_discarded += 1
                        gap_since_last_push = frame_id - \
                            last_frame_id_in_queues[q_idx]
                        avg_frame_gap_in_queues[q_idx] = (
                            gap_since_last_push + avg_frame_gap_in_queues[q_idx]) / 2.0
                        if (frame_no > max_frame_no):
                            frame_processed = frame_no - frame_discarded
                            frame_process_rate = frame_processed * 1.0 / frame_no
                            fps_count_duration = time.time() - fps_count_start_time
                            fps_raw = frame_no / fps_count_duration
                            fps_processed = frame_processed / fps_count_duration
                            frame_discarded = 0
                            frame_no = q_idx
                            frame_no_motion_start = frame_no
                            fps_count_start_time = time.time()
                            logging.info("frame_queue_input - avg_frame_gap_in_queues:"+ str(avg_frame_gap_in_queues)+ "fps_raw:"+ str(fps_raw)+ "fps_processed:" + str(fps_processed))
                        ns_contourArea = ns.contourArea
                        if min_area < ns_contourArea * 1.5:
                            adjust_rate = min(
                                max((ns_contourArea - min_area) / 3, 1), 100)
                            min_area = min(min_area + adjust_rate,
                                           ns_contourArea * 1.5)
                            if ns_contourArea > 999999:
                                min_area = min(min_area, min_area_start * 6)
                        logging.debug("frame_queue_input - frame_queues full, skipping:"+ str(q_idx) + "frame_id:" + str(frame_id) + "min_area: " + str(min_area) + " ns_contourArea: " + str(ns_contourArea))

                if show_frames and ret:
                    if show_detection_box:
                        fls = ns.face_matched['face_locations']
                        names = ns.face_matched['names']
                        frame_shape = frame.shape
                        for loc, name in zip(fls, names):
                            (top, right, bottom, left) = service.scale_location_rate(frame_shape, loc, frame_shrink_rate=ns.conf['frame_shrink_rate'], rate=1.2)
                            cv2.rectangle(frame, (left, top),(right, bottom), (0, 0, 255), 2)
                            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
                            font = cv2.FONT_HERSHEY_DUPLEX
                            cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)
                    cv2.imshow('smartcam', frame)

                if show_frames and cv2.waitKey(1) & 0xFF == ord('q'):
                    logging.info('Key Q pressed, there is a opencv bug to close the window on MAC')
                    show_frames = False
                    cv2.destroyAllWindows()

    def auto_face_detector(self, ns, max_process_time, max_shrink_rate, q_frame, q_enc):
        logging.info('auto_face_detector - process name: '+ str(multiprocessing.current_process().name) + ' max_process_time: '+ str(max_process_time) + ' max_shrink_rate: ' + str(max_shrink_rate))
        max_buffer = ns.conf['AFD_FRAME_BUF_SIZE']
        unused_frame_buffer = []
        frame_shrink_rate_auto = 1.0
        # unused_frame_reuse_tolerance = 1.2 * max_process_time
        unused_frame_reuse_tolerance = 0.16
        frame_shrink_rate_unchanged = 0
        frame_shrink_rate_adjusting_lock = 5
        contourArea = 9999999
        contourAreas = []

        face_locations_model = 'hog'
        number_of_times_to_upsample = 1

        while True:
            id = 0.0
            frame = None
            obj_to_encode = None
            face_locations = []
            laplacianSwitch = ns.laplacianSwitch
            laplacian_value = 0.0
            try:
                f = q_frame.get(True, 5)
                id = f['id']
                frame = f.get('frame')
                contourArea = f.get('contourArea')
                laplacian_value = f.get('laplacian_value')
            except Queue.Empty:
                # unlock frame_shrink_rate update to decrease back to 1
                frame_shrink_rate_unchanged = 0
                if frame_shrink_rate_auto > 1.0:
                    frame_shrink_rate_auto = frame_shrink_rate_auto - 0.05
                    frame_shrink_rate_auto = max(1, frame_shrink_rate_auto)
                pass

            laplacianSwitchPass = True
            if laplacianSwitch > 0 and laplacian_value < laplacianSwitch:
                logging.debug("auto_face_detector - " + str(max_process_time) +  " laplacianSwitch triggered: " + str(id) + " " + str(laplacianSwitch) + " "+  str(laplacian_value))
                laplacianSwitchPass = False

            if laplacianSwitchPass and id > 0 and type(frame) == numpy.ndarray:
                _start = time.time()
                small_frame = cv2.resize(frame, (0, 0), fx=(
                    1.0 / frame_shrink_rate_auto), fy=(1.0 / frame_shrink_rate_auto))
                frame_preprocess = cv2.cvtColor(
                    small_frame, cv2.COLOR_BGR2GRAY)
                face_locations = face_recognition.face_locations(
                    frame_preprocess, number_of_times_to_upsample=number_of_times_to_upsample, model=face_locations_model)
                process_time = time.time() - _start
                frame_deplayed = time.time() - id
                if process_time > max_process_time and frame_shrink_rate_auto < max_shrink_rate and frame_shrink_rate_unchanged < frame_shrink_rate_adjusting_lock:
                    rate_adjust = min(
                        (process_time - max_process_time) / process_time * frame_shrink_rate_auto, 0.5)
                    if rate_adjust > 0.09:
                        frame_shrink_rate_auto = frame_shrink_rate_auto + rate_adjust
                else:
                    if frame_shrink_rate_unchanged < frame_shrink_rate_adjusting_lock:
                        frame_shrink_rate_unchanged += 1
                    elif frame_shrink_rate_unchanged == frame_shrink_rate_adjusting_lock:
                        frame_shrink_rate_unchanged += 1
                        logging.debug("auto_face_detector - " + str(max_process_time) + " - frame_shrink_rate_auto locked: " + str(frame_shrink_rate_auto) + "process_time: " + str(process_time) + "frame_deplayed: " + str(frame_deplayed))

            if id > 0 and type(frame) == numpy.ndarray and len(face_locations) == 0:
                obj_to_buffer = {'id': id, 'frame': frame,
                                 'afd': max_process_time}
                unused_frame_buffer.append(obj_to_buffer)
                unused_frame_buffer = unused_frame_buffer[-max_buffer:]
                frame_have_face = ns.frame_have_face
                if frame_have_face > 0:
                    min_distance = unused_frame_reuse_tolerance
                    min_distance_id = -1
                    for i, fo in enumerate(unused_frame_buffer):
                        if abs(frame_have_face - fo['id']) < min_distance:
                            min_distance = abs(frame_have_face - fo['id'])
                            min_distance_id = i
                    if min_distance_id > -1:
                        obj_to_encode = unused_frame_buffer[min_distance_id]
                        del unused_frame_buffer[min_distance_id]
                        logging.info("auto_face_detector-" + str(max_process_time) + " -Found possible useful frame from the buffer.." + str(obj_to_encode['id']) + " "+ str(min_distance))

            if id > 0 and len(face_locations) > 0:
                obj_to_encode = {'id': id, 'frame': frame,
                                 'afd': max_process_time}
                ns.frame_have_face = id
                logging.info("auto_face_detector - "+ str(max_process_time) + "- Found faces in the frame: " + str(id) + " update ns.frame_have_face to recuit nearby frames from other afds")
                if contourArea < 999999:
                    contourAreas.append(contourArea)
                    contourAreas = sorted(contourAreas)[:10]
                if len(contourAreas) > 2:
                    contourAreas_min_avg = sum(
                        contourAreas[1:]) * 1.0 / len(contourAreas[1:])
                    if contourAreas_min_avg < ns.contourArea:
                        ns.contourArea = contourAreas_min_avg
                        logging.debug("auto_face_detector -"+ str(max_process_time) + "- set new smaller contourAreas_min_avg "+  str(contourAreas_min_avg) + " " + str(contourAreas))

            if obj_to_encode is not None:
                try:
                    # print "face_detector -  put obj_to_encode to q_enc"
                    q_enc.put(obj_to_encode, False)
                    frame_deplayed = time.time() - id
                    process_cost = time.time() - _start
                    logging.debug("auto_face_detector -  "+ str(max_process_time) + "put obj_to_encode to q_enc, id: "+ str(id) + "process_cost: " + str(process_cost) + "frame_deplayed: " + str(frame_deplayed) + "frame_shrink_rate_auto:" + str(frame_shrink_rate_auto))
                except Queue.Full:
                    logging.info("auto_face_detector -  "+ str(max_process_time) + "q_enc full - Discard face location " +  str(obj_to_encode['id']))
                    pass
            else:
                pass


    def face_encoder(self, ns, q_enc, q_encoded):
        logging.info('face_encoder - process name '+ str(multiprocessing.current_process().name))
        face_locations_model = 'hog'
        # face_locations_model = 'cnn'
        number_of_times_to_upsample = 1
        num_jitters = 1
        while True:
            loc_frame = None
            face_encodings = []
            try:
                loc_frame = q_enc.get(True, 2)
            except Queue.Empty:
                pass
            if loc_frame != None:
                id = loc_frame.get('id')
                frame = loc_frame.get('frame')
                afd = loc_frame.get('afd')
                _start = time.time()
                face_locations = loc_frame.get('face_locations')
                if face_locations == None or len(face_locations) == 0:
                    frame_rgb = frame[:, :, ::-1]
                    face_locations = face_recognition.face_locations(
                        frame_rgb, number_of_times_to_upsample=number_of_times_to_upsample, model=face_locations_model)
                else:
                    frame_rgb = frame
                if len(face_locations) > 0:
                    face_encodings = face_recognition.face_encodings(
                        frame_rgb, face_locations, num_jitters=num_jitters)
                logging.info("face_encoder - Completed encoding in: " + str(time.time() - _start) + " the frame encoded was late for: "+ str(time.time() - id)+ " id: " + str(id))
                if len(face_encodings) > 0:
                    res = {'id': id, 'face_locations': face_locations,
                           'face_encodings': face_encodings, 'frame_rgb': frame_rgb, 'afd': afd}
                    try:
                        logging.info("face_encoder - put encoded result to q_encoded: " +  str(id) + " face_locations " + str(face_locations))
                        q_encoded.put(res, True, 2)
                    except Queue.Full:
                        logging.info("face_encoder - q_encoded queue full, discard encoded result: " + str(res['id']))
                        pass
                else:
                    logging.info("face_encoder - no face to encode")
                    pass

    def face_matcher(self, ns, q_encoded, q_matched):
        logging.info('face_matcher - process name' + str(multiprocessing.current_process().name))
        frameids = []
        face_locations_buffer = []
        face_encodings_buffer = []
        face_matches_buffer = []
        max_buffer = ns.conf['MATCHER_BUF_SIZE']
        max_match_no = 4
        max_take_no = 2
        multi_frame_no = ns.conf['consecutive_frames_tocheck']
        # multi_frame_sec = ns.conf['frame_gap_sec_max'] * (multi_frame_no+2)
        multi_frame_sec = multi_frame_no * 0.3
        t_default = ns.conf['t_default']
        t_adjust_step = ns.conf['t_adjust_step']
        t_min = ns.conf['t_min']
        t_max = ns.conf['t_max']

        while True:
            loc_encoded = None
            frame_rgb = None
            afd = 0.0
            id = 0.0
            fes = []
            fls = []
            known_face_names = ns.faces_loaded['known_face_names']
            known_face_encodings = ns.faces_loaded['known_face_encodings']

            try:
                # print "face_matcher - Waiting for item from q_encoded for up to 5 seconds"
                loc_encoded = q_encoded.get(True, 2)
            except Queue.Empty:
                # print "face_matcher - Caught q_encoded empty exception, retry next time"
                pass

            if loc_encoded != None:
                id = loc_encoded['id']
                fls = loc_encoded['face_locations']
                fes = loc_encoded['face_encodings']
                frame_rgb = loc_encoded.get('frame_rgb')
                afd = loc_encoded.get('afd')

            if loc_encoded != None and id > 0 and (id not in frameids) and len(fes) > 0 and len(known_face_names) > 0:

                ns.face_matched = {'id': 0, 'face_locations': [], 'names': []}
                frameids.append(id)
                face_locations_buffer.append(fls)
                face_encodings_buffer.append(fes)
                face_matches_buffer.append([])

                frameids = frameids[-max_buffer:]
                face_locations_buffer = face_locations_buffer[-max_buffer:]
                face_encodings_buffer = face_encodings_buffer[-max_buffer:]
                face_matches_buffer = face_matches_buffer[-max_buffer:]
                face_locations = face_locations_buffer[-1]
                face_encodings = face_encodings_buffer[-1]
                face_names = []
                for face_encoding in face_encodings:
                    # See if the face is a match for the known face(s)
                    t = t_default
                    name = []
                    oneway_adjusting_flag = 0

                    # print "face_matcher - before match", " time: ", time.time()
                    while (len(name) == 0 and t >= t_min and t <= t_max):
                        # print 'process match with T: ', t
                        matches = face_recognition.compare_faces(
                            known_face_encodings, face_encoding, tolerance=t)
                        # print "face_matcher - afer compare_faces", " time: ", time.time()
                        matched_faces = map(lambda (a, b): b, filter(
                            lambda (x, y): x, zip(matches, known_face_names)))
                        names_counter = collections.Counter(matched_faces)
                        names_counter_sorted = names_counter.most_common()
                        if (len(names_counter_sorted) == 0 and oneway_adjusting_flag >= 0):
                            t = t + t_adjust_step
                            oneway_adjusting_flag = 1
                            logging.debug('face_matcher -no match found, increase tolerance to: ' + str(t))
                        elif (len(names_counter_sorted) <= max_match_no):
                            name = map(lambda(x, y): x, names_counter_sorted[:max_take_no])
                            logging.debug('face_matcher -matches found, get the popular names ' + str(name))
                        elif (len(names_counter_sorted) > max_match_no and oneway_adjusting_flag <= 0):
                            t = t - t_adjust_step
                            oneway_adjusting_flag = -1
                            logging.debug('face_matcher -too many matchs found, decrease tolerance to: ' +  str(t))
                        else:
                            name = ["Unknown"]
                    if (len(name) == 0):
                        name = ["Unknown"]
                    face_names.append(name)

                face_matches_buffer[-1] = face_names
                # find frames within the multi frame check tolerance
                bufindex_to_check = []
                last_frame_time = frameids[-1]
                for i in range(len(frameids))[::-1]:
                    if last_frame_time - frameids[i] < multi_frame_sec and len(face_matches_buffer[-1]) == len(face_matches_buffer[i]):
                        bufindex_to_check.append(i)
                # bufindex_to_check = bufindex_to_check[:multi_frame_no]

                names_checked = []
                checked_count = 0
                logging.info('face_matcher - multi frames checking '+ str(frameids) + " " + str(face_matches_buffer) + " " + str(bufindex_to_check))
                names_tocheck = face_matches_buffer[-1]
                for i in bufindex_to_check:
                    check_pass = True
                    for j, location_names in enumerate(face_matches_buffer[i]):
                        common_names = list(
                            set(names_tocheck[j]).intersection(location_names))
                        if len(common_names) != len(names_tocheck[j]):
                            check_pass = False
                            break
                    if check_pass:
                        checked_count += 1
                if checked_count >= multi_frame_no:
                    names_checked = face_matches_buffer[-1]
                    logging.info('face_matcher - multi frames checking passed ' + str(names_checked) + str(checked_count))
                else:
                    logging.info('face_matcher - not enough frames to verify the result ' + str(names_checked) + str(checked_count))

                names_final = []
                should_trigger_event = False
                for l, n in enumerate(names_checked):
                    if len(n) == 1:
                        names_final.append(n[0])
                        should_trigger_event = True
                    else:
                        logging.info('face_matcher - failed multiframe checked faces: '+ str(n))
                        names_final.append('Processing')

                ns.face_matched = {'id': id, 'face_locations': fls, 'names': names_final}

                if should_trigger_event:
                    to_matched_queue = {'id': id, 'face_locations': fls, 'names': names_final, 'frame_rgb': frame_rgb, 'afd': afd}
                    try:
                        q_matched.put(to_matched_queue, True, 2)
                    except Queue.Full:
                        logging.info("face_matcher - q_matched Full Discard matched result: " +  str(to_matched_queue['names']))
                        pass

                # ns.match_inprocess = []
            else:
                pass
                time.sleep(0.1)

    def event_trigger(self, ns, q_matched):
        logging.info('event_trigger - process name ' + str(multiprocessing.current_process().name))
        last_event_triggered_ts = 0
        last_event_triggered_names = []
        event_supress_ms = ns.conf['event_supress_ms']
        while True:
            frame_rgb = None
            frame = None
            matched_names_obj = None
            id = 0.0
            afd = 0.0
            names = []
            fls = []
            try:
                matched_names_obj = q_matched.get(True, 5)
            except Queue.Empty:
                pass

            if matched_names_obj != None:
                id = matched_names_obj['id']
                fls = matched_names_obj['face_locations']
                names = matched_names_obj['names']
                frame_rgb = matched_names_obj.get('frame_rgb')
                afd = matched_names_obj.get('afd')

            if id > 0 and type(frame_rgb) == numpy.ndarray:
                frame = frame_rgb[:, :, ::-1]

            if id > 0 and type(frame) == numpy.ndarray and len(names) > 0:

                # event_inprocess = ns.event_inprocess
                # event_inprocess.append(id)
                # ns.event_inprocess = event_inprocess

                logging.info(' --->>>> start trigger events for id: ' + str(id) + ' names: ' + str(names) + ' src afd: ' + str(afd))
                last_event_triggered_ts = service.face_detected(
                    names, fls, frame, last_event_triggered_names, last_event_triggered_ts, event_supress_ms=event_supress_ms)
                last_event_triggered_names = names

                # ns.event_inprocess = []

            else:
                # ns.event_inprocess = []
                time.sleep(0.5)
