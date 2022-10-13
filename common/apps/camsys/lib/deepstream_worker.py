# py libs
import threading, time, subprocess, shlex, os, select, subprocess, subprocess
from collections import deque

# carwash libs
import carwash_logging

# class handler of the deepstream inferencing
# the deepstream inference engine takes care of processing the cameras and generating 2 things:
# outgoing stream over rtsp that can be displayed on the same device and mainly to be displayed outside of the box
# raw inference object data to be streamed out over stdout and pipelined from the wrapper system

class DeepstreamWorker(threading.Thread):
    connection = None
    thread_count = 0
    bStop = False   # True, if thread gone to exit
    bExit = False   # True, if thread exited
    worker = None
    
    def get_data(self):
        return self.str_out
    
    def __init__(self, reco_num, vsource):
        self.vsource = vsource
        self.reco_num = reco_num
        self.deepstream_proc = -1
        self.slot_index = -1
        self.deepstream_json_reception_rolling_average = 10
        self.rolling_average_fps = deque(maxlen=self.deepstream_json_reception_rolling_average)
        self.logger = carwash_logging.setup_timed_rotating_logger('deepstream_engine_'+str(reco_num), '../logs/deepstream_engine.log')
        self.last_valid_json = ''
        DeepstreamWorker.thread_count += 1
        self.timeout = -1
        self.message_buffer = deque(maxlen=10)
        self.lock = threading.Lock()
        self.engine_ready = 0
        super().__init__()
    
    # signaled to stop deepstream engine, terminates with bStop
    def stop(self):
        self.logger.info("signal to stop deepstream engine")
        self.bStop = True
    
    # removes element from queue to be processed for distance calculation
    def pop_element(self):
        val = "empty"
        self.lock.acquire()
        try:
            if len(self.message_buffer) > 0:
                val = self.message_buffer.popleft()
        finally:
            self.lock.release()
        return val
        
    # returns if the engine is ready to produce raw object data
    def get_engine_ready(self):
        return self.engine_ready
		
    # launches the deepstream engine using the plugin executable, pipelines as subprocess
    def launch_deepstream_engine(self):
        cmd = 'python3 carwash_inference3.py '
        for i in range(len(self.vsource)):
            cmd = cmd + self.vsource[i] + ' '
        args = shlex.split(cmd)
        self.deepstream_proc = subprocess.Popen(args,stdout=subprocess.PIPE,universal_newlines=True)
        self.logger.info('[%d] pid created for deepstream_engine %d, execution command %s', os.getpid(),self.deepstream_proc.pid,cmd)
        
    # terminates the deepstream engine, kills the plugin executable subprocess
    def terminate_deepstream_engine(self):
        self.logger.info('[%d] terminating deepstream process ', os.getpid())
        self.deepstream_proc.kill()
        outs, errs = self.deepstream_proc.communicate()
        self.logger.info('[%d] deepstream processes comunicates errors: [%s] %d ', 
                   os.getpid(), errs, self.deepstream_proc.pid)
        self.bExit = True

    # this loops controlls the reading of the json output from deepstream engine
    def read_line(self):
        # checks if the deepstream engine exists
        # creates a poll for the stdout from deepstream engine
        # loops and reads stdout line by line
        # sets the connection ready when the line contains "metadata"
        # continues to read and waits for incoming data from the plugin executable
        line = ''
        if self.deepstream_proc is not None:
            poll_obj = select.poll()
            poll_obj.register(self.deepstream_proc.stdout, select.POLLIN)
            start = time.time()
            while not self.bStop:
                poll_result = poll_obj.poll(0)
                if poll_result:
                    line = self.deepstream_proc.stdout.readline()
                    if line.find("metadata") != -1 and self.engine_ready == 0:
                        
                        self.lock.acquire()
                        try:
                            self.engine_ready = 1
                        finally:
                            self.lock.release()
                            
                        self.logger.info("deepstream engine reports: engine is ready")
                    return line
                else:
                    time.sleep(0.001)
            self.logger.info('polling timer exceded and no new string from deepstream')
            return "EOF"
        else:
            return "EOF" 

    # calculates the rolling average of json reception from deepstream engine
    def calculate_rolling_average(self,actual_fps):
        self.rolling_average_fps.append(actual_fps)
        average = sum(self.rolling_average_fps) / self.deepstream_json_reception_rolling_average
        
        return average / self.deepstream_json_reception_rolling_average

    # controlls the deepstream engine interactions
    def run_deepstream_engine(self):
        # tries to read line
        # no lines available checks for deepstream engine flags like EOF or OOM
        # reports rolling average
        start = time.time()
        counter = 0
        ret_code = 0
        str_out_prev = ''
        inference_time = time.time()
        inference_count = 0
        while 1 and not self.bStop:
            start_performance = time.time()
            str_out = self.read_line()
            stop_performance = time.time()
            if str_out == "EOF": #end of file signal, meaning the camera did not started correctly
                self.logger.info('[%d] EOF in deepstream engine, terminating',os.getpid())
                break

            # sets the inference count on each second 
            if time.time() - inference_time > self.deepstream_json_reception_rolling_average:
                average = self.calculate_rolling_average(inference_count)
                self.logger.info('[%d] deepstream_worker reports: avg jsons/sec: %4.2f, msg_buffer: %d', os.getpid(),average, len(self.message_buffer) )
                inference_count = 0
                inference_time = time.time()
            # if it finds the metadata tag sends signal that the engine is ready
            if str_out.find('metadata') != -1:
                inference_count = inference_count + 1
                if str_out_prev != str_out:
                    self.lock.acquire()
                    try:
                        self.message_buffer.append(str_out)
                    finally:
                        self.lock.release()
                    self.last_valid_json = str_out
                    str_out_prev = str_out
                    
        self.logger.info('[%d] deepstream engine loop end', os.getpid())
        
    # main entry point
    def run(self):
        # launches deepstream engine
        # runs the engine
        # terminates after the engine has closed or no valid outputs are found
        
        # launch deepstream plugin executable
        self.launch_deepstream_engine()
        # launch deepstream pipeline controller
        self.run_deepstream_engine()
        # terminates deepstream plugin subprocess
        self.terminate_deepstream_engine()
        self.logger.info("deepstream worker shutting down...")
