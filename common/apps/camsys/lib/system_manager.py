#py libraries
from datetime import datetime
import threading
import numpy as np
from jtop import jtop #https://github.com/rbonghi/jetson_stats/wiki/library

# carwash libs
import carwash_logging

class SystemManager(threading.Thread):

    def __init__(self):
        self.logger = carwash_logging.setup_timed_rotating_logger('system_manager', '../logs/system_manager.log')
        self.bStop = False
        self.stats_dict = {}
        self.gpu = []
        self.gpu_temp = []
        self.cpu_temp = []
        self.uptime = datetime.now()
        super().__init__()

    # signaled to stop, terminates with bStop
    def stop(self):
        self.logger.info("signal to stop system manager")
        self.bStop = True

    def running_mean(self, in_array, sample_length):
        cumsum = np.cumsum(np.insert(in_array,0,0))
        return (cumsum[sample_length:] - cumsum[:-sample_length])/ float(sample_length)

    def run(self):
        with jtop() as jetson:
            # Enable Jetson Clocks for maximum performance
            jetson.jetson_clocks = True
            print(f"Jeston Clocks status:{jetson.jetson_clocks}")
            # jetson.ok() will provide stats are pre-determined update frequency
            while jetson.ok():
                self.stats_dict = jetson.stats
                for key, value in self.stats_dict.items():
                    if key == 'GPU':
                        self.gpu.append(value)
                    if key == 'Temp GPU':
                        self.gpu_temp.append(value)
                    if key == 'Temp CPU':
                        self.cpu_temp.append(value) 
                    if key == 'uptime':
                        self.uptime = value
                gpu_avg = np.convolve(self.gpu, np.ones(1000)/1000, mode = 'valid')
                gpu_avg2 = self.running_mean(self.gpu, 1000)
                print(gpu_avg)
                print(gpu_avg2)
                #self.logger.info(jetson.stats)