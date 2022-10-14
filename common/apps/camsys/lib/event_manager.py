# py libs
import time, threading, numpy as np, queue
from datetime import datetime
# carwash libs
import carwash_logging
from event_sender import EventSender


class EventManager(threading.Thread):
    
    def __init__(self):
        self.deepstream_json_reception_rolling_average = 1800.0
        self.logger = carwash_logging.setup_timed_rotating_logger('event_manager', '../logs/event_managers.log')
        self.rolling_average_fps = np.zeros(10)
        self.bStop = False
        self.fifo_queue = queue.Queue()
        super().__init__()

    # signaled to stop deepstream engine, terminates with bStop
    def stop(self):
        self.logger.info("signal to stop edge manager")
        self.bStop = True
        
    def run_edge_manager(self):
        # tries to read line
        # if no lines available, checks for deepstream engine flags like EOF or OOM
        # reports rolling average
        inference_time = time.time()
        num_events = 0
        distributor_json_counter = 0
        while 1 and not self.bStop:
            
            if time.time() - inference_time > self.deepstream_json_reception_rolling_average:
                self.logger.info('event manager reports: events generated: %4.2f', num_events)
                num_events = 0
                inference_time = time.time()
            
            str_out = list()
            try:
                str_out = self.fifo_queue.get(timeout=1)
                num_events += 1
            except Exception as e:
                pass

            if len(str_out) > 0:
                camera_id = str_out[0]
                msg1 = str_out[1]
                msg2 = str_out[2]
                msg_type = str_out[3]
                try:
                    t = EventSender(self.logger,camera_id,msg1,msg2,msg_type)
                    t.start()
                except Exception as e:
                    self.logger.info("Exception launching thread for: camera_id: %s, msg1: %s, msg2: %s, msg_type: %s, error: %s",str(camera_id),str(msg1),str(msg2),str(msg_type),str(e))
                    pass
            
        self.logger.info("stopping event manager")
        
    # controls the pulling of messages from the deepstream thread and sending them to all alive camera threads
    def run(self):
        # checks if the deepstream engine is alive, running and generating messages
        # if it is enables the camera handlers to process messages by setting the engine flag to True
        # pulls messages available in the deepstream worker and validates the structure
        # if the message is a valid json then sends it to all camera threads

        self.run_edge_manager()
        
        self.logger.info("terminating event manager")
