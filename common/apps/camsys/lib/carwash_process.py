# py libs
import signal, time, threading
# carwash libs
import carwash_logging
from message_distributor_worker import MessageDistributorWorker
from capture_worker import CaptureWorker
from event_manager import EventManager
from system_manager import SystemManager

# Class handler of the process
# The carwash process launches the deepstream inference engine thread, the message distributor thread and the camera handler threads
# Sends a alive heartbeat every X seconds to the corresponding log reporting the status of the threads managed
class CarwashProcess(object):
    
    bStop = False
    def __init__(self, vsource):
        self.vsource = vsource
        self.lock = threading.Lock()
        self.number_of_cameras = len(self.vsource)
        self.report_timing = 1800.0
        signal.signal(signal.SIGTERM, self._sigterm_handler)
        signal.signal(signal.SIGINT, self._sigint_handler)
        self.logger = carwash_logging.setup_timed_rotating_logger('carwash_process', '../logs/carwash_process.log')
        self.logger.info("Starting carwash process")
        self.thread_deepstream = None
        self.thread_distributor = None
        self.thread_event_manager = None
        self.thread_system_manager = None
        self.thread_cameras = [] #List of capture_worker threads
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

    #Launches the event manager
    #pulls the jsons obtained by the deepstream worker, validates the format and sends the to all camera threads               
    def launch_event_manager(self):
        self.thread_event_manager = EventManager()
        self.thread_event_manager.start()

    # launches the camera handlers
    # camera handlers run the distance calculations for each camera using the information provided by the message distributor
    def launch_camera_handlers(self):
        for i in range(1, self.number_of_cameras+1):
            self.logger.info("start recognition of camera: [%d] address: %s", i, self.vsource[i-1])            
            t = CaptureWorker( i, self.vsource[i-1],self.thread_event_manager)
            self.thread_cameras.append(t)
            t.start()

    # launches the message distributor 
    # message distributor connects with the deepstream system and pulls the objects data for all cameras
    def launch_message_distributor(self):
        self.thread_distributor = MessageDistributorWorker(self.thread_cameras,self.vsource,self.thread_event_manager)
        self.thread_distributor.start()
    
    #launches system manager thread for monitoring of GPU/CPU load of edge device
    def launch_system_manager(self):
        self.thread_system_manager = SystemManager()
        self.thread_system_manager.start()

    # stops all cameras running and all yolo engines running
    def kill_all(self):
        self.logger.info("stopping and joining event manager thread")
        self.thread_event_manager.stop()
        self.thread_event_manager.join()
        self.logger.info("stopping and joining system manager thread")
        self.thread_system_manager.stop()
        self.thread_system_manager.join()
        self.logger.info("stopping and joining capture worker threads")
        for t in self.thread_cameras:
            t.stop()
        for t in self.thread_cameras:
            t.join()
        self.logger.info("stopping and joining message distributor thread")
        self.thread_distributor.stop()
        self.thread_distributor.join()
        
    # Launch event manager, camera threads, message distributor and system manager 
    def run(self):
		#execution loop
        self.launch_event_manager()
        self.launch_camera_handlers()
        self.launch_message_distributor()
        self.launch_system_manager()
        
        start_time = time.time()
        # mantain process alive and report heartbeat
        while not self.bStop:
            if time.time() - start_time > self.report_timing:
                start_time = time.time()
                self.logger.info("Carwash process reports: distributor thread alive: %s, camera threads: %s", str(self.thread_distributor.isAlive()), str(len(self.thread_cameras)))
            pass
        self.kill_all()
        self.logger.info("terminating...")
        
        
