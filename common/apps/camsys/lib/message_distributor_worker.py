# py libs
import time,  threading, numpy as np, os, queue

# carwash libs
import carwash_logging

#from dummy_deepstream4 import DeepStreamInference
from carwash_inference import DeepStreamInference

# message distributor handler class
# This thread takes care of pulling the jsons obtained by the deepstream worker, validate the format and send the to all camera threads
# reports alive heartbeat every X seconds to the corresponding log
class MessageDistributorWorker(threading.Thread):
    
    def __init__(self, camera_threads, vsource, event_manager_thread):
        self.vsource = vsource
        self.camera_threads = camera_threads
        self.last_message = None
        self.deepstream_json_reception_rolling_average = 1800.0
        self.check_for_alive_engine = 10.0
        self.logger = carwash_logging.setup_timed_rotating_logger('message_distributor_worker', '../logs/message_distributor.log')
        self.rolling_average_fps = np.zeros(10)
        self.bStop = False
        self.fifo_queue = queue.Queue()
        self.thread_inference = None
        self.event_manager_thread = event_manager_thread
        super().__init__()

    # signaled to stop terminates with bStop
    def stop(self):
        self.logger.info("signal to stop message distributor worker")
        self.bStop = True
    
    # updates camera handler thread
    def update_cam_threads(self, camera_threads):
        self.lock.acquire()
        try:
            self.camera_threads = camera_threads
        finally:
            self.lock.release()
            
    def launch_deepstream_engine(self):
        self.thread_inference = DeepStreamInference(self.fifo_queue,self.vsource,self.event_manager_thread)
        self.thread_inference.start()
        self.logger.info('launching inference engine')
        
    def terminate_deepstream_engine(self):
        self.thread_inference.set_cameras_to_undefined()
        self.thread_inference.stop()
        self.thread_inference.join()
        self.logger.info("stopping and joining inference engine thread")
        
    # calculates the rolling average of json reception from yolo engine
    def calculate_rolling_average(self,actual_fps):
        self.rolling_average_fps = np.append(self.rolling_average_fps,actual_fps)
        if len(self.rolling_average_fps) > self.deepstream_json_reception_rolling_average:
            self.rolling_average_fps = np.delete(self.rolling_average_fps, 0)
        accum = 0
        num_elements = 0
        for i in range(len(self.rolling_average_fps)):
            accum = accum + self.rolling_average_fps[i]
            num_elements = num_elements + 1
        average = accum / num_elements
        return average / self.deepstream_json_reception_rolling_average
        
    def run_deepstream_engine(self):
        # tries to read line
        # no lineas available checks for deepstream engine flags like EOF or OOM
        # reports rolling average
        inference_time = time.time()
        check_alive_time = time.time()
        inference_json_counter = 0
        distributor_json_counter = 0
        while 1 and not self.bStop:
            
            if time.time() - inference_time > self.deepstream_json_reception_rolling_average:
                self.logger.info('message ditributor worker reports: inference jsons/sec: %4.2f, distributor jsons/sec: %4.2f', inference_json_counter/self.deepstream_json_reception_rolling_average, distributor_json_counter/self.deepstream_json_reception_rolling_average)
                inference_json_counter = 0
                distributor_json_counter = 0
                inference_time = time.time()
            dict_out = None
            try:
                dict_out = self.fifo_queue.get(timeout=1)
                inference_json_counter += 1
            except Exception as e:
                pass
            if time.time() - check_alive_time > self.check_for_alive_engine:
                check_alive_time = time.time()
                try:
                    if self.thread_inference.is_alive() == False and self.bStop == False:
                        self.logger.info("inference engine is dead, start a new one")
                        self.terminate_deepstream_engine()
                        time.sleep(10)
                        os.kill(os.getppid(), 9)
                        self.launch_deepstream_engine()
                except Exception as e:
                    self.logger.info("error in checking thread alive flag: %s", str(e))
                    pass

            if dict_out != None:
                for t in self.camera_threads:
                    try:
                        t.queue.put(dict_out)
                        distributor_json_counter += 1
                    except Exception as e:
                        pass
            
        self.logger.info("stopping deepstream engine")
        
    # controls the pulling of messages from the deepstream thread and sending them to all alive camera threads
    def run(self):
        # checks if the deepstream engine is alive, running and generating messages
        # if it is enables the camera handlers to process messages by setting the engine flag to True
        # pulls messages available in the deepstream worker and validates the structure
        # if the message is a valid json then sends it to all camera threads

        self.launch_deepstream_engine()
        self.run_deepstream_engine()
        self.terminate_deepstream_engine()
        self.logger.info("terminating message distributor worker")
