# py libs
import threading, traceback, time, datetime, numpy as np, sys, collections, queue, datetime
from collections import deque
# carwash libs
import carwash_logging
from edge_services_camlib import edge_services
from event_sender import EventSender


# class handler for the handling of each camera detections
# each camera is handled by a capture worker thread and recevies the object information from the message distributor
# the message is decomposed and only the objects corresponding to the camera processed are used for calculations
# the connection is made to edge services to communicate the results
class CaptureWorker(threading.Thread):
   
    def __init__(self, camera_id, camera_name, event_manager_thread):
        
        self.queue = queue.Queue()

        # Inference Classes
        self.PGIE_CLASS_ID_BACKGROUND = 0
        self.PGIE_CLASS_ID_PERSON = 1
        self.PGIE_CLASS_ID_VEHICLE = 2
        self.PGIE_CLASS_ID_FRONTLIGHT = 3
        self.PGIE_CLASS_ID_BACKLIGHT = 4
        
        #Camera configuration variables
        self.NO_OF_CAMERAS = 6
        self.CAMERAS_DISABLED = {'cam1': False, 'cam2': False, 'cam3': False, 'cam4': False, 'cam5': False, 'cam6': False, }
        self.camera_disabled = False
        self.REFERENCE_POINT_MATRIX = {'cam1': {'DEFAULT': 57, 'LEFT_THRESHOLD': [0, 200], 'LEFT_PIXEL': 12, 'CENTER_THRESHOLD': [200, 1080], 'CENTER_PIXEL': 57, 'RIGHT_THRESHOLD': [1080, 1280], 'RIGHT_PIXEL': 12}, 'cam2': {'DEFAULT': 62, 'LEFT_THRESHOLD': [0, 200], 'LEFT_PIXEL': 12, 'CENTER_THRESHOLD': [200, 1080], 'CENTER_PIXEL': 62, 'RIGHT_THRESHOLD': [1080, 1280], 'RIGHT_PIXEL': 12}, 'cam3': {'DEFAULT': 54, 'LEFT_THRESHOLD': [0, 200], 'LEFT_PIXEL': 12, 'CENTER_THRESHOLD': [200, 1080], 'CENTER_PIXEL': 54, 'RIGHT_THRESHOLD': [1080, 1280], 'RIGHT_PIXEL': 12}, 'cam4': {'DEFAULT': 62, 'LEFT_THRESHOLD': [0, 200], 'LEFT_PIXEL': 12, 'CENTER_THRESHOLD': [200, 1080], 'CENTER_PIXEL': 62, 'RIGHT_THRESHOLD': [1080, 1280], 'RIGHT_PIXEL': 12}, 'cam5': {'DEFAULT': 30, 'LEFT_THRESHOLD': [0, 100], 'LEFT_PIXEL': 6, 'CENTER_THRESHOLD': [100, 540], 'CENTER_PIXEL': 30, 'RIGHT_THRESHOLD': [540, 640], 'RIGHT_PIXEL': 6}, 'cam6': {'DEFAULT': 60, 'LEFT_THRESHOLD': [0, 200], 'LEFT_PIXEL': 12, 'CENTER_THRESHOLD': [200, 1080], 'CENTER_PIXEL': 60, 'RIGHT_THRESHOLD': [1080, 1280], 'RIGHT_PIXEL': 12}}
        self.NO_OF_DETECTION_FRAMES = 20
        self.SUPRESSION_ZONE = {}
        self.supression_pixel_from = list()
        self.supression_pixel_to = list()

        #System configuration
        self.VEHICLE_DETECTION_IGNORE = {}
        self.NO_DETECTION_FRAMES_COUNT = 80
        self.SIGNAL_CODES = ['N', 'A', 'C', 'P', 'S']
        self.RED_THRESHOLD_INCHES = 12
        self.YELLOW_THRESHOLD_INCHES = 24
        self.MIN_WEIGHT_SCORE = 10
        self.DRY_RUN = False
        self.ROLLING_FRAME = True
        self.ABSOLUTE_DIST = True
        self.printDebug = 0

        
        self.distance_array = {}
        self.distance_array_val = {}

        self.prev_status = {}
        self.current_status = {}
        self.no_detection_counter = {}

        # capture worker parameters
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.json_full = collections.deque(maxlen=10)
        self.valid_json = collections.deque(maxlen=10)
        self.dict_setting_mps = 0
        self.capture_worker_lps = 0
        self.valid_dict_vmps = 0
        self.valid_dict_vmps2 = 0
        self.avg_fps = None
        self.capture_max_time_no_new_json = 10
        self.rolling_average_fps = np.zeros(10)
        self.reception_rolling_average = 1800.0
        self.alert_threads = []
        self.event_manager_thread = event_manager_thread
        self.max_queue_size = 10
        
        # variables for yolo engine performance measurement
        self.json_full_start = time.time()
        self.bStop = False
        self.bExit = False
        
        self.logger = carwash_logging.setup_timed_rotating_logger('capture_worker_'+str(self.camera_id), '../logs/capture_worker_'+str(self.camera_id)+'.log')
        
        self.distance_array = {}
        self.distance_array_val = {}

        self.prev_status = {}
        self.current_status = {}
        self.no_detection_counter = {}
        self.current_status[self.camera_id] = "D"
        
        # new business logic
        self.projection_queue_max_len = 5
        self.obj_pos_queue = deque(maxlen=self.projection_queue_max_len)
        
        for i in range(self.projection_queue_max_len):
            self.obj_pos_queue.append([])
        
        self.logger.info("capture worker initializing")
        self.deepstream_engine_ready = 1
        self.lock = threading.Lock()
        self.last_frame = 0
        self.current_dict = None
        self.last_dict = None
        super().__init__()
    
    def set_parameters1(self):
        try:
            
            #Read in configuration from camsys.yaml and cameras.yaml
            camsys_dict = edge_services.get_camsys_configuration()
            self.cameras_dict = edge_services.get_cameras_configuration()

            #Parse configs
            self.NO_OF_CAMERAS = len(self.cameras_dict)
            self.CAMERAS_DISABLED = camsys_dict["CAMERAS_DISABLED"]
            self.REFERENCE_POINT_MATRIX = camsys_dict["REFERENCE_POINT_MATRIX"]
            self.SUPRESSION_ZONE = camsys_dict["SUPRESSION_ZONE"]
            self.VEHICLE_DETECTION_IGNORE = camsys_dict["VEHICLE_DETECTION_IGNORE"]
            self.NO_OF_DETECTION_FRAMES = int(camsys_dict["NO_OF_DETECTION_FRAMES"])
            self.NO_DETECTION_FRAMES_COUNT = int(camsys_dict["NO_DETECTION_FRAMES_COUNT"])
            self.SIGNAL_CODES = list(camsys_dict['valid_camera_states'].keys()) #['N', 'A', 'C', 'P', 'S']
            self.RED_THRESHOLD_INCHES = int(camsys_dict['C_min_distance'])
            self.YELLOW_THRESHOLD_INCHES = int(camsys_dict['D_min_distance'])
            self.MIN_WEIGHT_SCORE = int(camsys_dict['MIN_WEIGHT_SCORE'])
            
            #Check to see if camera has been disabled in config
            try:
                for key, value in self.CAMERAS_DISABLED.items():
                    if key == "cam"+str(self.camera_id):
                        self.camera_disabled = value
            except Exception as e:
                self.CAMERAS_DISABLED = {}

            #Define all suppresion zones from config    
            try:
                self.SUPRESSION_ZONE = self.SUPRESSION_ZONE["cam"+str(self.camera_id)]
                for key, value in self.SUPRESSION_ZONE.items():
                    if key.find('pixel_from') != -1:
                        self.supression_pixel_from.append(value)
                    if key.find('pixel_to') != -1:
                        self.supression_pixel_to.append(value)
            except Exception as e:
                self.SUPRESSION_ZONE = {}
                
            try:
                len_vehicles = len(self.VEHICLE_DETECTION_IGNORE)
            except Exception as e:
                self.VEHICLE_DETECTION_IGNORE = {}

            
        except Exception as e:
            self.logger.info("Exception in --init_from_edge_config--: "+str(e))
            traceback.print_exception(*sys.exc_info())
            return False

        return True
    
    # sets parameters for calculations of distance, generating events
    def set_parameters2(self):
        if self.NO_OF_CAMERAS > 0:
            self.yellow_bucket = self.init_dict(self.NO_OF_CAMERAS, isList=1)
            self.red_bucket = self.init_dict(self.NO_OF_CAMERAS, isList=1)
            self.green_bucket = self.init_dict(self.NO_OF_CAMERAS, isList=1)

            self.distance_array = self.init_dict(self.NO_OF_CAMERAS, isList=1)
            self.distance_array_val = self.init_dict(self.NO_OF_CAMERAS, isList=1)

            self.prev_status = self.init_dict(self.NO_OF_CAMERAS, init_value="D")
            self.current_status = self.init_dict(self.NO_OF_CAMERAS, init_value="D")
            self.no_detection_counter = self.init_dict(self.NO_OF_CAMERAS, init_value=0)
            return True
        return True
    
    # Initialize dictionary
    def init_dict(self, no_of_camera, isList=0, init_value=''):
        data_dict = {}
        for i in range(1, no_of_camera+1):
            if isList:
                data_dict[i] = []
            else:
                data_dict[i] = init_value
        return data_dict
        
    # reset_dict function from original code
    def reset_dict(self, data_dict, isList=0, reset_value=''):
        for key in data_dict.keys():
            if isList:
               data_dict[key] = [] 
            else:
                data_dict[key] = init_value
        return data_dict
        
    # sets if depstream engine is ready or not
    def set_deepstream_engine(self, val):
        self.lock.acquire()
        try:
            self.deepstream_engine_ready = val
            if val == 1:
                self.logger.info("deepstream engine reports: ready ")
            else:
                self.logger.info("deepstream engine reports: not ready ")
        finally:
            self.lock.release()

    # kills entire interactions
    def stop(self):
        self.logger.info("signal to stop capture camera ")
        self.bStop = True

    
    # sets the json file and periodically inform about execution
    def set_json(self,json_full):
        self.json_full.append(json_full)
        self.dict_setting_mps = self.dict_setting_mps + 1
        
    # gets a new json and appends the information   
    def process_full_dict(self):
        try:
            dict_message = self.queue.get(timeout=1)
            self.dict_setting_mps += 1
        except Exception as e:
            return None
        try:
            valid_dict = dict_message[self.camera_id-1]
        except Exception as e:
            print("EXCEPTION IN PROCESS FULL DICT:",str(e))
            return None
        
        return valid_dict
                
    def print_debug(self, print_str, level=0):
        level_dict = {0:'Info:', 1:'Developer:', 2:'System:'}
        if self.printDebug >= level:
            print(f'{level_dict[level]} {print_str}')
    
    def flush_queue(self):
        while True:
            self.queue.get(timeout=1)
            if self.queue.qsize() < self.max_queue_size:
                break
                
    
    def pointInRect(self,point,P1,P2):
        x1, y1 = P1
        x2, y2 = P2
        x, y = point
        if (x1 < x and x < x2):
            if (y1 < y and y < y2):
                return True
        return False
        
    # pick 3 points from the right side of the left car and check if any of those points are in the left side car
    # pick 3 points from the left side of the right side car and check if any of those points are in the right side car
    # the 3 points will be top middle and bottom
    # if not then return same dist, if true then return 0            
    def is_overlapping(self,dist):
        # get car order left and right
        try:
            if self.obj_pos_queue[self.projection_queue_max_len-1][0]["left"]+self.obj_pos_queue[self.projection_queue_max_len-1][0]["width"] < self.obj_pos_queue[self.projection_queue_max_len-1][1]["left"]+self.obj_pos_queue[self.projection_queue_max_len-1][1]["width"]:
                car_left = self.obj_pos_queue[self.projection_queue_max_len-1][0]
                car_right = self.obj_pos_queue[self.projection_queue_max_len-1][1]
            else:
                car_left = self.obj_pos_queue[self.projection_queue_max_len-1][1]
                car_right = self.obj_pos_queue[self.projection_queue_max_len-1][0]
            car_left["left"] = float(car_left["left"])
            car_left["width"] = float(car_left["width"])
            car_left["top"] = float(car_left["top"])
            car_left["height"] = float(car_left["height"])
            
            car_right["left"] = float(car_right["left"])
            car_right["width"] = float(car_right["width"])
            car_right["top"] = float(car_right["top"])
            car_right["height"] = float(car_right["height"])
            
            # get 3 points from each car
            P1_left = (car_left["left"]+car_left["width"],car_left["top"])
            P2_left = (car_left["left"]+car_left["width"],car_left["top"]+(car_left["height"]/2))
            P3_left = (car_left["left"]+car_left["width"],car_left["top"]+car_left["height"])
            #top left and bottom right coordinates
            car_left_cord1 = (car_left["left"],car_left["top"])
            car_left_cord2 = (car_left["left"]+car_left["width"],car_left["top"]+car_left["height"])

            P1_right = (car_right["left"],car_right["top"])
            P2_right = (car_right["left"],car_right["top"]+(car_right["height"])/2)
            P3_right = (car_right["left"],car_right["top"]+car_right["height"])
            #top left and bottom right coordinates
            car_right_cord1 = (car_right["left"],car_right["top"])
            car_right_cord2 = (car_right["left"]+car_right["width"],car_right["top"]+car_right["height"])

            if self.pointInRect(P1_left,car_right_cord1,car_right_cord2) == True or self.pointInRect(P2_left,car_right_cord1,car_right_cord2) == True or self.pointInRect(P3_left,car_right_cord1,car_right_cord2) == True:
                return 0,True
            
            if self.pointInRect(P1_right,car_left_cord1,car_left_cord2) == True or self.pointInRect(P2_right,car_left_cord1,car_left_cord2) == True or self.pointInRect(P3_right,car_left_cord1,car_left_cord2) == True:
                return 0,True
                
            return dist,False
        except Exception as e:
            return dist,False
    
    # removes frames that have one or more objects inside the supression areas
    # if the left side of any of the vehicles in the screen is inside the supression area, return true to filter frame
    def filter_supression_zones(self,dict_out):
        
        # badly configured vectors (check camsys.yml) or no supression areas for the camera
        if (len(self.supression_pixel_from) != len(self.supression_pixel_to)) or (len(self.supression_pixel_from) == 0) or (len(dict_out) != 2):
            return False
        else:
            if float(dict_out[0]["left"])+float(dict_out[0]["width"]) < float(dict_out[1]["left"])+float(dict_out[1]["width"]):
                car_left = dict_out[0]
                car_right = dict_out[1]
            else:
                car_left = dict_out[1]
                car_right = dict_out[0]
            for j in range(len(self.supression_pixel_from)):
                if float(car_left["left"]) + float(car_left["width"]) > float(self.supression_pixel_from[j]) and float(car_right["left"]) < float(self.supression_pixel_to[j]):
                    return True
        return False
        
    # check if the frame contains an object bigger than the specified size and the intersection between boxes is higher than the set value
    def filter_special(self,overlaps,distPix,dict_out):
        if len(self.VEHICLE_DETECTION_IGNORE) == 0:
            return False
        for key, value in self.VEHICLE_DETECTION_IGNORE.items():
            for j in range(len(dict_out)):
                if overlaps == True and distPix >= float(value["overlapping_box_size_x"]) and float(dict_out[j]["width"]) >= float(value["original_box_size"]):
                    return True
        return False
        
    # check if the coming frame contains object in line with the calculated dequeue of poistions for all cars in the image
    # if it does let the values pass
    def filter_outlier(self,dict_out):
        # check the array and filter based on position and search area
        obj_exists = 0
        # check if all slots contain 2 cars
        for i in range(self.projection_queue_max_len):
            if len(self.obj_pos_queue[i]) == 2:
                obj_exists += 1
            # skip frame whenever there is more than 2 cars in the frame
            if len(self.obj_pos_queue[i]) > 2:
                return True
        
        # return false if we have slots with no objects (empty list)
        if obj_exists != self.projection_queue_max_len:
            return False
        
        else:
            cars_left = list()
            cars_right = list()
            last_car_left = None
            last_car_right = None
            # calculate if the frame will be dropped or not and return True to drop False to not drop
            for i in range(self.projection_queue_max_len):
                #calculate expected position based on previous location and velocity of object
                #find which is left and right car
                
                if float(self.obj_pos_queue[i][0]["left"])+float(self.obj_pos_queue[i][0]["width"]) < float(self.obj_pos_queue[i][1]["left"])+float(self.obj_pos_queue[i][1]["width"]):
                    cars_left.append(self.obj_pos_queue[i][0])
                    cars_right.append(self.obj_pos_queue[i][1])
                    last_car_left = self.obj_pos_queue[i][0]
                    last_car_right = self.obj_pos_queue[i][1]
                else:
                    cars_left.append(self.obj_pos_queue[i][1])
                    cars_right.append(self.obj_pos_queue[i][0])
                    last_car_left = self.obj_pos_queue[i][1]
                    last_car_right = self.obj_pos_queue[i][0]
                    
            
            dist_array_cars_left = list()
            dist_array_cars_right = list()
            for i in range(len(cars_left)-1):
                dist_array_cars_left.append(abs((float(cars_left[i+1]["left"]) + float(cars_left[i+1]["width"]))-(float(cars_left[i]["left"]) + float(cars_left[i]["width"]))))
                dist_array_cars_right.append(abs(float(cars_right[i+1]["left"])-float(cars_right[i]["left"])))
            
            avg_displacement_cars_left = float(sum(dist_array_cars_left) / len(dist_array_cars_left))
            avg_displacement_cars_right = float(sum(dist_array_cars_right) / len(dist_array_cars_right))

            # calculate search areas for future position
            search_area_left_min = float(last_car_left["left"])+float(last_car_left["width"])-(avg_displacement_cars_left*2)
            search_area_left_max = float(last_car_left["left"])+float(last_car_left["width"])+(avg_displacement_cars_left*2)
            search_area_right_min = float(last_car_right["left"])-(avg_displacement_cars_right*2)
            search_area_right_max = float(last_car_right["left"])+(avg_displacement_cars_right*2)
            
            # check if the objects found match the expected locations
            correctly_matched = 0
            if len(dict_out) == 2:
                if float(dict_out[0]["left"])+float(dict_out[0]["width"]) < float(dict_out[1]["left"])+float(dict_out[1]["width"]):
                    current_car_left = dict_out[0]
                    current_car_right = dict_out[1]
                else:
                    current_car_left = dict_out[1]
                    current_car_right = dict_out[0]
                    
                if float(current_car_left["left"])+float(current_car_left["width"]) > search_area_left_min and float(current_car_left["left"])+float(current_car_left["width"]) < search_area_left_max:
                    correctly_matched+=1
                if float(current_car_right["left"]) > search_area_right_min and float(current_car_right["left"]) < search_area_right_max:
                    correctly_matched+=1
                if correctly_matched == 2:
                    return False
                else:
                    return True
            else:
                return True
    
    # gets biggest X position of first object and smallest X position of second object, for all objects in frame
    # only uses vehicle objects
    def get_objects_x2x1(self, frame_meta):

        final_x2x1 = []
        return_data = {}
        obj_counter = {
            self.PGIE_CLASS_ID_PERSON:0,
            self.PGIE_CLASS_ID_VEHICLE:0,
            self.PGIE_CLASS_ID_FRONTLIGHT:0,
            self.PGIE_CLASS_ID_BACKLIGHT:0
        }   
        num_rects = len(frame_meta)
        pred_dict = {}
        temp_objs = list()
        if num_rects > 1:
            for i in range(len(frame_meta)):
                try:
                    if int(frame_meta[i]["class_id"]) == 2:
                        temp_objs.append(frame_meta[i])
                    obj_counter[int(frame_meta[i]["class_id"])] += 1
                    x1 = float(frame_meta[i]["left"])
                    x2 = x1 + float(frame_meta[i]["width"])
                    if obj_counter[int(frame_meta[i]["class_id"])] == 1:
                        pred_dict[int(frame_meta[i]["class_id"])] = [[x1, x2]]
                    elif obj_counter[int(frame_meta[i]["class_id"])] > 1:
                        temp_list = pred_dict[int(frame_meta[i]["class_id"])]
                        temp_list.append([x1, x2])
                        pred_dict[int(frame_meta[i]["class_id"])] = temp_list
                except StopIteration:
                    break
                except Exception as e:
                    self.logger.info("Exception in --get_objects_x2x1--: "+ str(e))

            self.obj_pos_queue.append(temp_objs)
            if len(pred_dict) > 0:
                for key in pred_dict:
                    # get distance ONLY between "cars"
                    if key !=2:
                        continue
                    objs = pred_dict[key]

                    sorted_objs = sorted(objs, key=lambda x:x[0])
                    for i in range(len(sorted_objs) - 1):
                        mdist = abs(sorted_objs[i][1] - sorted_objs[i+1][0])
                        final_x2x1.append(round(sorted_objs[i][1], 2))
                        final_x2x1.append(round(sorted_objs[i+1][0], 2))


            if len(final_x2x1) > 0:

                stream_number = self.camera_id-1
                return_data[stream_number] = final_x2x1
                
        else:
            self.obj_pos_queue.append(temp_objs)

        return return_data

    # gets final status for detection a collision
    def get_final_status(self, codes_timer_array, cam_id=-1):
        #scores = {self.SIGNAL_CODES[0]:2}
        #default C=3, A=2, N=1 in the same order
        #Same score logic | [C A]->C,  [C N]->C, [A N]->A
        scores = {self.SIGNAL_CODES[2]:0.003, self.SIGNAL_CODES[1]:0.002, self.SIGNAL_CODES[0]:0.001} 
        time_limit = time.monotonic()-1
        codes_array = [ x[0] for x in filter(lambda x: x[1] > time_limit, codes_timer_array) ]
        
        i = 0
        end = len(codes_array)-1
        weight = 0
        while( i < end) :
            if codes_array[i] == codes_array[i+1] :
                weight += 0.5
                scores[codes_array[i]] = round(scores.get(codes_array[i], 0) + 1 + weight, 3)
            else :
                scores[codes_array[i]] = round(scores.get(codes_array[i], 0) + 0.25, 3)
                weight = 0
            i += 1

        winner = max(scores, key=scores.get)
        
        return (time_limit, scores, winner) if scores[winner] >= self.MIN_WEIGHT_SCORE else (time_limit, scores, None)

    # gets resolution based on a resolution matrix, used for distance calculations
    def get_pixel_resolution(self, camera_id, car1_x):
        cam_id = f'cam{camera_id}'
        cam_resolution_dict = self.REFERENCE_POINT_MATRIX[cam_id]

        if car1_x  >= cam_resolution_dict['LEFT_THRESHOLD'][0] and  car1_x < cam_resolution_dict['LEFT_THRESHOLD'][1]:
            return cam_resolution_dict['LEFT_PIXEL']
        elif car1_x  >= cam_resolution_dict['CENTER_THRESHOLD'][0] and  car1_x < cam_resolution_dict['CENTER_THRESHOLD'][1]:
            return cam_resolution_dict['CENTER_PIXEL']
        elif car1_x >= cam_resolution_dict['RIGHT_THRESHOLD'][0] and car1_x < cam_resolution_dict['RIGHT_THRESHOLD'][1]:
            return cam_resolution_dict['RIGHT_PIXEL']

        return cam_resolution_dict['DEFAULT']
        
    def generate_event(self,msg1,msg2,msg_type):
        try:
            self.event_manager_thread.fifo_queue.put((self.camera_id,msg1,msg2,msg_type))
        except Exception as e:
            pass

    # business logic
    def business_logic(self,objects_x2x1,current_frame,dict_out):

        #If no cars are detected
        if len(objects_x2x1) == 0:
            self.no_detection_counter[self.camera_id]+=1

            if self.no_detection_counter[self.camera_id] >= self.NO_DETECTION_FRAMES_COUNT: 
                self.distance_array[self.camera_id].clear()
                self.distance_array_val[self.camera_id].clear()
                if self.current_status[self.camera_id] != self.SIGNAL_CODES[0]:
                    self.prev_status[self.camera_id] = self.current_status[self.camera_id]
                    #only for start up or camera reconnection
                    if self.current_status[self.camera_id] == "D":
                        self.prev_status[self.camera_id] = self.SIGNAL_CODES[0]
                        self.current_status[self.camera_id] = self.SIGNAL_CODES[0]
                    else:
                        self.current_status[self.camera_id] = self.SIGNAL_CODES[0]

                    if not self.DRY_RUN:
                        self.generate_event(self.current_status[self.camera_id],"","event")
                self.no_detection_counter[self.camera_id] = 0
        else:
            self.no_detection_counter[self.camera_id] = 0   
            for key in objects_x2x1:
                #each_x2x1=rear car x1; each_x2x1=front car x2
                each_x2x1 = objects_x2x1[key] 
                camera_id = key+1
                if len(each_x2x1) > 0:

                    try:
                        distPix = round((abs(each_x2x1[0]-each_x2x1[1])), 2) #in pixels
                        PIXEL_PER_FOOT = self.get_pixel_resolution(self.camera_id, each_x2x1[0])
                        dist = round((distPix/PIXEL_PER_FOOT)*12, 2) #in inches
                        current_ts = datetime.now().strftime('%Y-%m-%d:%H-%M-%S-%f')
                        dist,overlaps = self.is_overlapping(dist)
                        if self.filter_special(overlaps,distPix,dict_out) == True:
                            continue

                        if dist <= self.RED_THRESHOLD_INCHES:
                            self.distance_array[self.camera_id].append((self.SIGNAL_CODES[2], np.round(time.monotonic(), decimals = 1)))
                        elif dist > self.RED_THRESHOLD_INCHES and dist <= self.YELLOW_THRESHOLD_INCHES:
                            self.distance_array[self.camera_id].append((self.SIGNAL_CODES[1], np.round(time.monotonic(), decimals = 1)))
                        else:
                            self.distance_array[self.camera_id].append((self.SIGNAL_CODES[0], np.round(time.monotonic(), decimals = 1)))
    
                        self.distance_array_val[self.camera_id].append(dist)

                        if len(self.distance_array[self.camera_id]) >= self.NO_OF_DETECTION_FRAMES:
                            time_limit, final_score, final_status = self.get_final_status(self.distance_array[self.camera_id], cam_id=self.camera_id)
                            if final_status != None:
                                score_log = f"Left Car X2:{each_x2x1[0]} | time_limit:{time_limit} | Frame Number {current_frame} | Final Status Scores:{final_score} ||"
                                dist_log = f"{score_log}\n Distances(inches)- cam{self.camera_id}:{self.distance_array_val[self.camera_id]} | TimeStamp:{current_ts} ||"
                                final_log = f"{dist_log}\n Dist_log Status Codes- cam{self.camera_id}:{self.distance_array[self.camera_id]} | TimeStamp:{current_ts}"

                                self.current_status[self.camera_id] = final_status
                                if self.prev_status[self.camera_id] != self.current_status[self.camera_id]:

                                    self.generate_event("",final_log,"report")
                                    self.print_debug(final_log, 0)
                                    now = datetime.now()
                                    time_now = now.strftime('%Y-%m-%d %H:%M:%S,%f').strip()[:-3]
                                    self.print_debug(f"\n{time_now} Status change for cam{self.camera_id}: {self.prev_status[self.camera_id]}->{self.current_status[self.camera_id]} | {final_status}--------------\n", 0)
                                   
                                    ## Send event to edge_service if dry run is not enabled and camera is not disabled in config
                                    if not self.camera_disabled and not self.DRY_RUN:
                                        self.print_debug(f"Sending Event for Cam{self.camera_id}")
                                        self.generate_event(self.current_status[self.camera_id],"","event")
                                    self.prev_status[self.camera_id] = self.current_status[self.camera_id]
                            
                            if self.ROLLING_FRAME:
                                self.distance_array[self.camera_id].pop(0)
                                self.distance_array_val[self.camera_id].pop(0)
                            else:
                                self.distance_array[self.camera_id].clear()
                                self.distance_array_val[self.camera_id].clear()
                                
                                
                    except Exception as e:
                        self.logger.info("Exception 1 in --tiler_sink_pad_buffer_probe--: "+str(e))
                        traceback.print_exception(*sys.exc_info())

    # loops while there are frames in the camera and deepstream information coming in
    def run(self):
        # initiate parameters
        self.set_parameters1()
        self.set_parameters2()
        entered_first = 0
        start_time = time.time()
        start_time_no_frames = time.time()
        # loops while there are frames being written
        skipped_frames = 0
        queue_max = 0
        while True and not self.bStop:
            dict_out = self.process_full_dict()
            self.capture_worker_lps = self.capture_worker_lps + 1
            # check if no frames generated in 10 seconds change to state D
            if time.time() - start_time_no_frames > 10:
                start_time_no_frames = time.time()
                processed_dict_vmps_counter = self.valid_dict_vmps2 / 10
                if processed_dict_vmps_counter == 0.0 and self.current_status[self.camera_id] != "D":
                    #iniciate all parameters
                    self.set_parameters2()
                if queue_max > 10:
                    self.generate_event("","queue max size reached","report")
                self.valid_dict_vmps2 = 0
            
            if time.time() - start_time > self.reception_rolling_average:
                
                start_time = time.time()
                processed_dict_vmps_counter = self.valid_dict_vmps / self.reception_rolling_average
                self.logger.info("capture worker for camera : %s, processed msg/sec: %s, skipped frames: %s, queue max size: %s", str(self.camera_name), str(processed_dict_vmps_counter), str(skipped_frames), str(queue_max))
                heart_beat_log = "capture worker for camera : "+str(self.camera_name)+", processed msg/sec: "+str(processed_dict_vmps_counter)+", skipped frames: "+str(skipped_frames)+", queue max size: "+str(queue_max)
                self.generate_event("",heart_beat_log,"report")
                self.dict_setting_mps = 0
                self.valid_dict_vmps = 0
                skipped_frames = 0
                queue_max = 0
                
            # if the json from deepstream engine is valid
            objects_x2x1 = {}
            
            if dict_out is not None and len(dict_out)>0:
                # calculate repeated and skiped frames

                current_frame = int(dict_out[0]["frame_number"])
                dict_out.pop(0)
                queue_size = self.queue.qsize() - 1
                # flush queue
                if queue_size >= self.max_queue_size:
                    self.flush_queue()
                    
                if queue_size > queue_max:
                    queue_max = queue_size
                
                elif current_frame - self.last_frame > 1:
                    skipped_frames = current_frame - self.last_frame
                self.last_frame = current_frame
                try:
                    # business logic here
                    self.current_dict = dict_out
                    objects_x2x1 = self.get_objects_x2x1(self.current_dict)
                    if self.filter_outlier(self.current_dict) == False and self.filter_supression_zones(self.current_dict) == False:
                        self.business_logic(objects_x2x1, current_frame,self.current_dict)
                    self.valid_dict_vmps += 1
                    self.valid_dict_vmps2 += 1
                    self.last_dict = self.current_dict
                except Exception as e:
                    print("error: ",str(e))
                    pass
            
        # terminates and return
        self.logger.info('capture loop end of camera: %s', str(self.camera_id))
        self.logger.info("capture worker shutting down...")
