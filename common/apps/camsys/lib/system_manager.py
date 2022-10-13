#py libraries
import threading
from jtop import jtop #https://github.com/rbonghi/jetson_stats/wiki/library

# carwash libs
import carwash_logging

class SystemManager(threading.Thread):
   
    def __init__(self):
        self.logger = carwash_logging.setup_timed_rotating_logger('system_manager', '../logs/system_manager.log')
        self.bStop = False
        super().__init__()

    # signaled to stop, terminates with bStop
    def stop(self):
        self.logger.info("signal to stop system manager")
        self.bStop = True

    def run(self):
        with jtop() as jetson:
            # Enable Jetson Clocks for maximum performance
            jetson.jetson_clocks = True
            print(f"Jeston Clocks status:{jetson.jetson_clocks}")
            # jetson.ok() will provide stats are pre-determined update frequency
            while jetson.ok():
                # Read tegra stats
                self.logger.info(jetson.stats)