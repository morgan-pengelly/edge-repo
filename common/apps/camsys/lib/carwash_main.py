# py libs
import  sys, os, signal, multiprocessing, traceback, time

# carwash libs
from carwash_process import CarwashProcess
from edge_services_camlib import edge_services
import carwash_logging
__version__ = "1.0.0"

vsource = []
# takes configuration for cameras from edge
def init_from_edge_config():

    try:
        cameras_dict = edge_services.get_cameras_configuration()
    except Exception:
        print("Exception in --init_from_edge_config--")
        traceback.print_exception(*sys.exc_info())
        return {}

    return cameras_dict

# defines the entry point for each process
def carwash_launcher(carwash_num, carwash_count):
    logger.info('launching process: %d', carwash_num)
    app = CarwashProcess(vsource)
    try:
        app.run()
    except:
        logger.error(traceback.format_exc())
    logger.info('carwash process: %d terminated...', carwash_num)
    exit(1)

# check if the deepstream inference engine exists
def check_deepstream_engine_bin():
    exists = os.path.isfile('carwash_inference.py')
    if exists:
        logger.info('Inference engine found, continue...')
    else:
        logger.info('Inference engine not found, check the file carwash_inference.py exists. Terminating...')
        sys.exit(1)
    
# handles the running of the system, launches processes in a process pool
class carwash_pool(object):

    def __init__(self, carwash_count):
        self.carwash_count = carwash_count
        self.pool = multiprocessing.Pool(carwash_count)
        
        #signals that the system will recognize and pass through all the functions
        signal.signal(signal.SIGINT, self._sigint_handler)
        signal.signal(signal.SIGTERM, self._sigterm_handler)

        logger.info('finished initialization')

    # launches processes
    def run(self):
        args = zip(range(0,self.carwash_count), [self.carwash_count]*self.carwash_count)
        logger.info('starting the launch of the carwash processes')
        try:
            res = self.pool.starmap_async(carwash_launcher, args)
            res = res.get()
        except KeyboardInterrupt:
            logger.info('keyboard interrupt, stopping system')
            self.pool.terminate()
        except Exception as e:
            logger.info('excpetion ocurred %s', str(e))
            self.pool.terminate()
        else:
            pass
        finally:
            self.pool.close()
            self.pool.join()

        logger.info('exit')

    # handler for interruption signal
    def _sigint_handler(self, signum, taskfrm):
        logger.info('sigint captured: terminating processes and threads')
        self.pool.terminate()
        self.pool.close()
        try:
            self.pool.join()
        except Exception as e:
            pass
        sys.exit(1)
    
    # handler for termination signal
    def _sigterm_handler(self, signum, taskfrm):
        logger.info('sigterm captured: terminating processes and threads')
        self.pool.terminate()
        self.pool.close()
        try:
            self.pool.join()
        except Exception as e:
            pass
        logger.info('shutdown')
        sys.exit(1)

if __name__ == '__main__':

    # Configure Logger
    logger = carwash_logging.setup_timed_rotating_logger('carwash_main', '../logs/carwash_main.log')
    logger.info("VERSION: %s",__version__)
    
    #Get sources from configuration file
    num_sources = 0
    while num_sources == 0:
        num_sources = len(vsource)
        cameras_dict = init_from_edge_config()
        num_sources=len(cameras_dict)
        vsource = [each['url'] for key, each in cameras_dict.items()]
        if num_sources < 1:
            logger.info("waiting for API to pull cameras")
            time.sleep(10)
    print("vsource: ",vsource)
    carwash_count = 1
	
    # checks if the deepstream inference file is available
    check_deepstream_engine_bin()

	# call CarwashPool to launch the processes
    pool = carwash_pool(carwash_count)
    pool.run()
