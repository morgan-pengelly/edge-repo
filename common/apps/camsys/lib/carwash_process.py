# py libs
import signal, os, time, datetime, json, traceback, random, uuid, shutil, getpass, threading, collections, math, copy
# carwash libs
import carwash_logging
from deepstream_worker import DeepstreamWorker
from message_distributor_worker import MessageDistributorWorker
from capture_worker import CaptureWorker
from event_manager import EventManager

# Class handler of the process
# The carwash process launches the deepstream inference engine thread, the message distributor thread and the camera handler threads
# Sends a alive heartbeat every X seconds to the corresponding log reporting the status of the threads managed
class CarwashProcess(object):
    
    bStop = False
    def __init__(self, carwash_num: int, carwash_count: int, vsource):
        self.vsource = vsource
        self.carwash_num = carwash_num
        self.carwash_count = carwash_count
        self.lock = threading.Lock()
        self.number_of_cameras = len(self.vsource)
        self.report_timing = 1800.0
        signal.signal(signal.SIGTERM, self._sigterm_handler)
        signal.signal(signal.SIGINT, self._sigint_handler)
        self.logger = carwash_logging.setup_timed_rotating_logger('carwash_process_'+str(carwash_num), '../logs/carwash_process.log')
        self.logger.info("Starting carwash process: %d, total processes is: %d",carwash_num, carwash_count)
        self.thread_deepstream = None
        self.thread_distributor = None
        self.thread_event_manager = None
        self.thread_cameras = []
        pass
    
    # stop signal received enabling the stop flag so all processes can be stopped
    def stop(self):
        self.bStop = True
    
    # handler for SIGINT
    def _sigint_handler(self, signum, taskfrm):
        self.stop()

    # handler for SIGTERM
    def _sigterm_handler(self, signum, taskfrm):
        self.stop()

    # launches the message distributor 
    # message distributor connects with the deepstream system and pulls the objects data for all cameras
    def launch_message_distributor(self):
        self.thread_distributor = MessageDistributorWorker(self.thread_cameras,self.carwash_num,self.vsource,self.thread_event_manager)
        self.thread_distributor.start()
    
    # launches the camera handlers
    # camera handlers run the distance calculations for each camera using the information provided by the message distributor
    def launch_camera_handlers(self):
        # check which camera will print logs
        try:
            file1 = open('logs_config.txt', 'r')
            Lines = file1.readlines()
            camera_id_logs =""
            # Strips the newline character
            for line in Lines:
                try:
                    camera_id_logs = int(line.strip())
                except Exception as e:
                    pass    
            if camera_id_logs == "":
                camera_id_logs = -1
        except Exception as e:
            camera_id_logs = -1
        for i in range(1, self.number_of_cameras+1):
            self.logger.info("start recognition of camera: [%d] address: %s", i, self.vsource[i-1])            
            t = CaptureWorker(self, self.carwash_num, i, self.number_of_cameras, self.vsource[i-1],self.thread_event_manager,camera_id_logs)
            self.thread_cameras.append(t)
            t.start()
            
    def launch_event_manager(self):
        self.thread_event_manager = EventManager()
        self.thread_event_manager.start()
    
    # stops all cameras running and all yolo engines running
    def kill_all(self):
        self.logger.info("stopping and joining event manager thread")
        self.thread_event_manager.stop()
        self.thread_event_manager.join()
        self.logger.info("stopping and joining capture worker threads")
        for t in self.thread_cameras:
            t.stop()
        for t in self.thread_cameras:
            t.join()
        self.logger.info("stopping and joining message distributor thread")
        self.thread_distributor.stop()
        self.thread_distributor.join()
        
            
        
    # handles the entire logic for the ROG architecture 
    def run(self):
		#execution loop
        # launch event manager
        self.launch_event_manager()
        # launch camera handlers
        self.launch_camera_handlers()
        # launch the message distributor
        self.launch_message_distributor()
        
        start_time = time.time()
        # mantain process alive and report heartbeat
        while not self.bStop:
            if time.time() - start_time > self.report_timing:
                start_time = time.time()
                self.logger.info("Carwash process reports: distributor thread alive: %s, camera threads: %s", str(self.thread_distributor.isAlive()), str(len(self.thread_cameras)))
            pass
        self.kill_all()
        self.logger.info("terminating...")
        
        
