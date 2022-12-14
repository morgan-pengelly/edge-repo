from fastapi import BackgroundTasks, FastAPI
from enum import Enum
from typing import Optional
from pymodbus.client.sync import ModbusTcpClient
from datetime import datetime
import logging
import inspect
import copy
import yaml
import pytz
import time
import redis
import json
import threading

'''
-----------------
API DOCUMENTATION
-----------------
'''
api_version = '0.5c-eqp'
api_title = "Sonny's Tunnel Anti-Collision System"
api_description = """

<h4>This API service provides data access and control functions for the Sonny's Tunnel Anti-Collision System</h4>

"""

api_tags = [
    { "name": "General Usage", },
    { "name": "System Control"},
    { "name": "Logs & Notificatios"},    
    { "name": "Carwash Interface"},
    { "name": "Cameras Events"},
    { "name": "Cameras Information"},    
    { "name": "Configuration"}
]


'''
--------
API DEFS
--------
'''
app = FastAPI(
    title = api_title, 
    description = api_description,
    version = api_version,
    openapi_tags=api_tags
    )

@app.on_event("startup")
async def startup_event():
    app.tz = pytz.timezone('utc')
    app.edge_services = EdgeServices()
    app.logger = LogAndNotify()
    app.config = Configuration()
    app.config.load_config()
    app.logger.system_id = app.config.carwash().get('system_id', 'Unknown')
    app.state_tracker = CameraSystemStateTracker(app.config.camsys())
    app.carwash_interface = CarwashInterface(app.config.carwash())
    app.edge_services.debug = app.config.system('debug_start_mode')
    app.edge_services.dry_run = app.config.system('dry_run_start_mode')
    app.logger.notify(f"Edge API Services (version: {api_version}) started")


@app.on_event("shutdown")
async def startup_event():
    app.logger.notify("Edge API Services shutdown")


@app.get("/", tags=["General Usage"])
def welcome_test_message():
    return ApiResponse("Welcome to Edge Services")


@app.get("/dry-run", tags=["System Control"])
def dry_run_status():
    return ApiResponse({ "dry-run": app.edge_services.dry_run})


@app.post("/dry-run", tags=["System Control"])
def start_dry_run():
    app.edge_services.dry_run = True
    return ApiResponse({ "dry-run": app.edge_services.dry_run})


@app.delete("/dry-run", tags=["System Control"])
def end_dry_run():
    app.edge_services.dry_run = False
    return ApiResponse({ "dry-run": app.edge_services.dry_run})

@app.get("/debug", tags=["System Control"])
def debug_status():
    return ApiResponse({ "debug": app.edge_services.debug})


@app.post("/debug", tags=["System Control"])
def start_debug():
    app.edge_services.debug = True
    return ApiResponse({ "debug": app.edge_services.debug})


@app.delete("/debug", tags=["System Control"])
def end_debug():
    app.edge_services.debug = False
    return ApiResponse({ "debug": app.edge_services.debug})


@app.post("/reboot", tags=["System Control"])
def jetson_reboot():
    return ApiResponse({ "warning": "Not implemented yet"})

class LogTypes(str, Enum):
    report = "report"
    notify = "notify"
    alert = "alert"
    debug = "debug"

@app.post("/logger/{log_type}", tags=["Logs & Notificatios"])
def system_logger(log_type: LogTypes, message: str):
    eval(f'app.logger.{log_type}("{message}")')
    return ApiResponse({ "log_type": log_type, 'message': message, 'debug': app.edge_services.debug })


@app.get("/logger/inference/last_errors", tags=["Logs & Notificatios"])
def inference_last_errors():
    try:
        with open('/app/data/errorlog.js', 'r') as json_file:
            data = json.load(json_file)
            json_file.close()
        error = False
    except:
        data = []
        error = True
    return ApiResponse(data, error=error)


@app.get("/logger/inference/last_events", tags=["Logs & Notificatios"])
def inference_last_events():
    try:
        with open('/app/data/eventlog.js', 'r') as json_file:
            data = json.load(json_file)
            json_file.close()
        error = False
    except:
        data = []
        error = True
    return ApiResponse(data, error=error)


@app.get("/cameras/status", tags=["Cameras Information"])
def cameras_status():
    camera_status, error = app.state_tracker.get_tracking_state()
    return ApiResponse( {"cameras_status": camera_status}, error=error )


@app.get("/camera/status/{camera_id}", tags=["Cameras Information"])
def camera_status(camera_id: str):
    camera_status, error = app.state_tracker.get_tracking_state(camera_id)
    return ApiResponse( {"camera_id":camera_id, "camera_status":camera_status}, error=error)


@app.get("/camera/state/{camera_id}", tags=["Cameras Information"])
def camera_state(camera_id: str):
    camera_state, error = app.state_tracker.get_camera_state(camera_id)
    return ApiResponse( {"camera_id":camera_id, "camera_state": camera_state}, error=error)


@app.post("/camera/{camera_id}/event/{state}", tags=["Cameras Events"])
async def camera_event(camera_id: str, state: str, background_tasks: BackgroundTasks):
    camera_state, error = app.state_tracker.set_camera_state(camera_id, state)
    if error:
        return ApiResponse( {"camera_id": camera_id}, error=error )
    if not app.edge_services.dry_run:
        bt = background_tasks
        if app.state_tracker.in_stop_states(state):
            app.carwash_interface.background_task(bt, app.carwash_interface.conveyor_stop)
        if app.state_tracker.in_alarm_states(state):
            app.carwash_interface.background_task(bt, app.carwash_interface.alarm_start)
        if not app.state_tracker.in_alarm_states(app.state_tracker.camsys_states()):
            app.carwash_interface.background_task(bt, app.carwash_interface.alarm_stop)
        if app.state_tracker.all_reset_states(app.state_tracker.camsys_states()):
            last_camera_id, last_request, last_update = app.state_tracker.get_last_event()
            full_start = app.config.camera_field(last_camera_id, 'full_start')
            if full_start == True and \
                    app.state_tracker.all_normal_states(app.state_tracker.camsys_states()):
                app.carwash_interface.background_task(bt, app.carwash_interface.conveyor_full_start)
            else:
                app.carwash_interface.background_task(bt, app.carwash_interface.conveyor_start)
    else:
        app.logger.notify("device in dry-run mode. Modbus commands were not executed.")
    return ApiResponse( {"camera_id": camera_id, "camera_state": camera_state} )


@app.post("/camera/{camera_id}/keepalive/{state}", tags=["Cameras Events"])
def camera_keepalive(camera_id: str, state: str = None):
    camera_state, error = app.state_tracker.set_camera_state(camera_id, state)
    if error:
        return ApiResponse( {"camera_id": camera_id}, error=error )
    return ApiResponse( {"camera_id":camera_id, "camera_state":camera_state} )


@app.get("/config", tags=["Configuration"])
def get_configuration():
    return ApiResponse(app.config.data)


@app.get("/config/reload", tags=["Configuration"])
def reload_configuration():
    app.config.load_config()
    return ApiResponse(app.config.data) 


@app.get("/config/camsys", tags=["Configuration"])
def get_camsys_configuration():
    return ApiResponse(app.config.camsys()) 


@app.get("/config/cameras", tags=["Configuration"])
def get_cameras_configuration(as_dict: Optional[bool] = True):
    return ApiResponse(app.config.cameras(as_dict=as_dict)) 


@app.get("/config/carwash", tags=["Configuration"])
def get_carwash_configuration():
    return ApiResponse(app.config.carwash()) 


@app.get("/carwash/status", tags=["Carwash Interface"])
def carwash_status():
    return ApiResponse(app.carwash_interface.carwash_status()) 


@app.get("/conveyor/state", tags=["Carwash Interface"])
def conveyor_state():
    return ApiResponse(app.carwash_interface.conveyor_state()) 


@app.post("/conveyor/start", tags=["Carwash Interface"])
def conveyor_start():
    return ApiResponse(app.carwash_interface.conveyor_start()) 


@app.post("/conveyor/full_start", tags=["Carwash Interface"])
def conveyor_full_start():
    return ApiResponse(app.carwash_interface.conveyor_full_start()) 


@app.post("/conveyor/reset", tags=["Carwash Interface"])
def conveyor_reset():
    return ApiResponse(app.carwash_interface.conveyor_reset()) 


@app.post("/conveyor/stop", tags=["Carwash Interface"])
def conveyor_stop():
    return ApiResponse(app.carwash_interface.conveyor_stop()) 


@app.get("/alarm/state", tags=["Carwash Interface"])
def alarm_state():
    return ApiResponse(app.carwash_interface.alarm_state()) 


@app.post("/alarm/start", tags=["Carwash Interface"])
def alarm_start():
    return ApiResponse(app.carwash_interface.alarm_start()) 


@app.post("/alarm/stop", tags=["Carwash Interface"])
def alarm_stop():
    return ApiResponse(app.carwash_interface.alarm_stop()) 


'''
-------
CLASSES
-------
'''

#---------------------------------------------------------------------------------------------------
class EdgeServices:
    def __init__(self):
        self._dry_run = False
        self._debug = False
        self.__log_queue_len = 100
        self.__log_queue_name = 'edge_services_log'

        # FIXME - Controlar errores.
        self.redis = redis.Redis(host='edge-redis', db=0)


    def _redis_get_str(self, key):
        value = self.redis.get(key)
        return value.decode("utf-8") if value else None


    def _redis_get_bool(self, key):
        value = self.redis.get(key)
        try:
            value = eval(value.decode("utf-8"))
        except:
            value = False
        return value


    @property
    def dry_run(self):
        return self._dry_run


    @dry_run.setter
    def dry_run(self, value):
        if not isinstance(value, bool):
            if   value == 'yes': value = True
            elif value == 'no': value = False
            elif value == 'last': value = self._redis_get_bool('edge_services_dry_run')
        if not isinstance(value, bool): value = False
        self._dry_run = value
        self.redis.set('edge_services_dry_run', repr(value))
        app.logger.report(f'dry_run mode set to {value}')


    @property
    def debug(self):
        return self._debug


    @debug.setter
    def debug(self, value):
        if not isinstance(value, bool):
            if   value == 'yes': value = True
            elif value == 'no': value = False
            elif value == 'last': value = self._redis_get_bool('edge_services_debug')
        if not isinstance(value, bool): value = False
        self._debug = value
        self.redis.set('edge_services_debug', repr(value))
        app.logger.report(f'debug mode set to {value}')


    def log_push(self, log_type: str, log_message: str):

        with self.redis.pipeline() as pipe:
            pipe.lpush(
                self.__log_queue_name,
                json.dumps(
                    {
                        'date': format(datetime.now(app.tz)), 
                        'type': log_type,
                        'system': app.logger.system_id,
                        'message': log_message
                    }
                )
            )
            pipe.ltrim(self.__log_queue_name,0,self.__log_queue_len-1)
            pipe.execute()




#---------------------------------------------------------------------------------------------------
class Configuration:

    def __init__(self):
        self.data = {}
        self.data['cameras'] = []
        self.data['camsys'] = {}
        self.data['carwash'] = {}
        self.data['system'] = {}


    def _load_yaml(self, yaml_file: str):
        try:
            with open(yaml_file, 'r') as stream:
                parsed_yaml = yaml.safe_load(stream)
                for module in parsed_yaml:
                    self.data[module] = copy.deepcopy(parsed_yaml[module])
        except:
            app.logger.notify(f"load_cameras: error reading {yaml_file}")


    def load_config(self):
        self.load_camsys()
        self.load_cameras()
        self.load_carwash()
        self.load_system()


    def load_camsys(self):
        yaml_file = '/app/app/camsys.yml'
        self._load_yaml(yaml_file)
        camsys = self.data['camsys']

        if 'conveyor_stop_states' not in camsys:
            camsys['conveyor_stop_states'] = ['C','P','S']
        if 'carwash_alarm_states' not in camsys:
            camsys['carwash_alarm_states'] = ['A','C','P','S']
        if 'reset_camera_values' not in camsys:
            camsys['reset_camera_values'] = ['N','U']
        if 'valid_camera_states' not in camsys:
            camsys['valid_camera_states'] = {
                'U': 'Unknown State',
                'N': 'No problem detected',
                'A': 'Distance Alert',
                'C': 'Collision Risk',
                'P': 'Person Outside the Car',
                'S': 'Car stopped at the end of tunnel'
                }


    def load_cameras(self):
        yaml_file = '/app/app/cameras.yml'
        self._load_yaml(yaml_file)


    def load_carwash(self):
        yaml_file = '/app/app/carwash.yml'
        self._load_yaml(yaml_file)
        carwash = self.data['carwash']
        if 'system_id' not in carwash:
            carwash['system_id'] = 'Unknown System ID'
        if 'system_timezone' in carwash:
            try:
                systz = carwash['system_timezone']
                app.tz = pytz.timezone(systz)
            except:
                app.tz = pytz.timezone('utc')


    def load_system(self):
        yaml_file = '/app/app/system.yml'
        self._load_yaml(yaml_file)
        system = self.data['system']
 

    def camsys(self, value: str = None):
        camsys = copy.deepcopy(self.data.get('camsys', {}))
        return camsys.get(value,None) if value else camsys


    def cameras(self, value: str = None, as_dict: bool = True):
        cameras = copy.deepcopy(self.data.get('cameras', {}))
        if as_dict:
            camdict = {}
            for d in cameras:
                cid = d['id']
                del d['id']
                camdict[cid] = d
            return camdict
        else:
            return cameras.get(value,None) if value else cameras


    def camera_field(self, camera_id: str = None, field: str = None):
        value = 'unset'
        try:
            cameras = self.data.get('cameras', {})
            value = next(camera[field] for camera in cameras if camera['id'] == camera_id)
        except:
            pass
        return value


    def carwash(self, value: str = None):
        carwash = copy.deepcopy(self.data.get('carwash', {}))
        return carwash.get(value,None) if value else carwash


    def system(self, value: str = None):
        system = copy.deepcopy(self.data.get('system', {}))
        return system.get(value,None) if value else system


#---------------------------------------------------------------------------------------------------
class LogAndNotify:

    def __init__(self):
        self.logger = logging.getLogger("uvicorn.info")
        self.system_id = 'System_Id unset'


    def report(self, message: str = ''):
        app.edge_services.log_push('LOG', message)
        if app.edge_services.debug:
            self.logger.warning(f'{datetime.now(app.tz)} - <LOG> - [{self.system_id}]: {message}')


    def notify(self, message: str = ''):
        self.report(message)
        app.edge_services.log_push('NOTIFY', message)
        if app.edge_services.debug:
            self.logger.warning(f'{datetime.now(app.tz)} - <NOTIFY> - [{self.system_id}]: {message}')


    def alert(self, message: str = ''):
        #-- Provisional definition
        self.notify(message)
        app.edge_services.log_push('ALERT', message)
        if app.edge_services.debug:
            self.logger.warning(f'{datetime.now(app.tz)} - <ALERT> - [{self.system_id}]: {message}')


    def debug(self, message: str = ''):
        if app.edge_services.debug:
            self.logger.warning(f'{datetime.now(app.tz)} - <DEBUG> - [{self.system_id}]: {message}')



#---------------------------------------------------------------------------------------------------
class CameraSystemStateTracker:

    def __init__(self, params : dict = None):
        default_camera_states = {
                'U': 'Unknown State',
                'N': 'No problem detected',
                'A': 'Distance Alert',
                'C': 'Collision Risk',
                'P': 'Person Outside the Car',
                'S': 'Car stopped at the end of tunnel'
                }
        self._cameras_state = {}
        self.reset_camera_values = params.get('reset_camera_values', ['N','U'])
        self.valid_camera_states = params.get('valid_camera_states', default_camera_states)
        self.conveyor_stop_states = params.get('conveyor_stop_states', ['C','P','S'])
        self.carwash_alarm_states = params.get('carwash_alarm_states', ['C','A','P','S'])
        try:
            for camera_id in app.config.cameras():
                self.set_camera_state(camera_id, 'U')
        except:
            app.logger.alert("Cannot initialize cameras with state 'U'")


    def validate_states(self, states: str = None):
        bad_states = ''
        response = None
        for state in states:
            if state not in self.valid_camera_states.keys():
                bad_states += state + ','
        if bad_states:
            response = f"argument contains invalid states: {bad_states}".rstrip(',')
        return response


    def validate_camera(self, camera_id: str):
        response = None
        if not camera_id in app.config.cameras():
            response = f'camera {camera_id} is not defined in configuration'
        return response


    def set_camera_state(self, camera_id: str, states: str):
        bad_camera = self.validate_camera(camera_id)
        if bad_camera:
            return None, bad_camera

        bad_states = self.validate_states(states)
        if bad_states:
            return None,bad_states

        prev_data = copy.deepcopy(self._cameras_state.get(camera_id, {}))
        prev_state = prev_data.get('state', '?')
        prev_request = prev_data.get('last_request', '')
        prev_update = prev_data.get('last_update', '')


        new_state = set()
        for state in states:
            new_state.add(state)

        camera_description = app.config.camera_field(camera_id, 'description')
        self._cameras_state[camera_id] = {
            "state": new_state,
            "description": camera_description,
            "last_request": states,
            "last_update": datetime.now(app.tz),
            "prev_state": prev_state,
            "prev_request": prev_request,
            "prev_update": prev_update
            }

        if new_state != prev_state:
            app.logger.notify(f'<{camera_id}> ({camera_description}) changed state from {prev_state} to {new_state}')

        return new_state,None


    def get_camera_state(self, camera_id: str):
        bad_camera = self.validate_camera(camera_id)
        if bad_camera: return None, bad_camera
        try:
            camera_state = self._cameras_state[camera_id]['state']
        except:
            camera_state = '?'        
        return copy.copy(camera_state), None


    def get_tracking_state(self, camera_id: str = None):
        if camera_id:
            bad_camera = self.validate_camera(camera_id)
            if bad_camera: return None, bad_camera
            return copy.deepcopy(self._cameras_state).get(camera_id,{}), None
        else:
            return copy.deepcopy(self._cameras_state), None


    def in_stop_states(self, states):
        retval = False
        for state in states:
            if state in self.conveyor_stop_states: retval = True
        return retval


    def in_alarm_states(self, states):
        retval = False
        for state in states:
            if state in self.carwash_alarm_states: retval = True
        return retval


    def all_reset_states(self, states = None):
        retval = True if states else False
        for state in states:
            if state not in self.reset_camera_values: return False
        return retval


    def all_normal_states(self, states = None):
        retval = True if states else False
        for state in states:
            if state != 'N': return False
        return retval


    def camsys_states(self):
        states = set()
        for cam in self._cameras_state:
            for state in self._cameras_state[cam]['state']:
                states.add(state)
        return states


    def get_last_event(self, event_type = None):
        last_event = (None, None, None)
        for cam in self._cameras_state:
            last_request = self._cameras_state[cam].get('last_request', None)
            last_update = self._cameras_state[cam].get('last_update', None)
            if event_type and last_request != event_type:
                continue
            if last_event[0]:
                if last_update and last_update > last_event[2]:
                    last_event = (cam, last_request, last_update)
            else:
                last_event = (cam, last_request, last_update)
        return last_event


#---------------------------------------------------------------------------------------------------
class CarwashInterface:

    def __init__(self, params: dict):
        # General Init
        self.modbus_ip = params.get('modbus_ip', None)
        self.modbus_targets = {}
        self.modbus_pulse_list = set()
        self.background_counter = 0
        self._conveyor_state = 'On'
        self._alarm_state = "Off"
        self.sem_busy = threading.Semaphore()
        self.sem_background_counter = threading.Semaphore()

        # Modbus Common Config
        self.mb_signal_pulse_seconds = params.get('modbus_signal_pulse_seconds', 2)
        
        #
        # Hint: Modbus config tuple = (signal_on, signal_off, pulse)
        # 
    
        # Modbus Alarm Signal Config
        self.mb_alarm_trigger = params.get('modbus_alarm_trigger_terminal', 3)
        inverted = params.get('modbus_alarm_trigger_inverted', False)
        pulse = params.get('modbus_alarm_trigger_pulse', False)
        on_signal, off_signal = self._modbus_target_signal_values(inverted)
        self.modbus_targets[self.mb_alarm_trigger] = (on_signal, off_signal, pulse)

        # Modbus Conveyor Stop Signal Config    
        self.mb_conveyor_stop_term = params.get('modbus_conveyor_stop_terminal', 2)
        inverted = params.get('modbus_conveyor_stop_inverted', False)
        pulse = params.get('modbus_conveyor_stop_pulse', False)
        on_signal, off_signal = self._modbus_target_signal_values(inverted)
        self.modbus_targets[self.mb_conveyor_stop_term] = (on_signal, off_signal, pulse)

        # Modbus Conveyor Start Signal Config
        self.mb_conveyor_plc_delay = params.get('modbus_conveyor_plc_delay', 0.01)
        self.mb_conveyor_start_term = params.get('modbus_conveyor_start_terminal', 0)
        inverted = params.get('modbus_conveyor_start_inverted', False)
        pulse = params.get('modbus_conveyor_start_pulse', True)
        on_signal, off_signal = self._modbus_target_signal_values(inverted)
        self.modbus_targets[self.mb_conveyor_start_term] = (on_signal, off_signal, pulse)


    def _modbus_target_signal_values(self, inverted: bool = False):
        return (0,1) if inverted else (1,0)


    def _modbus_target_use_pulse(self, target = -1):
        return self.modbus_targets.get(target, (None,None,False))[2]


    def _modbus_set_on(self, mbclient = None, target = None):
        if mbclient == None: return
        if target == None: return
        #app.logger.debug(f'calling ON with {target} and {self.modbus_targets[target][0]}')
        mbclient.write_coil(target, self.modbus_targets[target][0])
        time.sleep(0.06)
        if self._modbus_target_use_pulse(target):
            self.modbus_pulse_list.add(target)


    def _modbus_set_off(self, mbclient = None, target = None, force = False):
        if mbclient == None: return
        if target == None: return
        if not self._modbus_target_use_pulse(target) or force:
            mbclient.write_coil(target, self.modbus_targets[target][1])
            time.sleep(0.06)


    def _background_counter(self, action = None):
        self.sem_background_counter.acquire(timeout=10)
        if action == '+':
           self.background_counter += 1
        if action == '-':
            self.background_counter -= 1
            if self.background_counter < 0: self.background_counter = 0
        self.sem_background_counter.release()


    def _modbus_command(self, command: str = None, **extra_args):
        message = f"command {command} was sent to modbus {self.modbus_ip}"
        full_start_end_pulse = False
        if self.sem_busy.acquire(timeout=10):
            try:
                mbclient = ModbusTcpClient(self.modbus_ip)
                mbclient.connect()
                time.sleep(0.1)

                if command == 'conveyor_start':
                    full_start = extra_args.get('full_start', False)
                    self._modbus_set_off(mbclient, self.mb_conveyor_stop_term)
                    self._conveyor_state = 'On'
                    if full_start:
                        time.sleep(self.mb_conveyor_plc_delay)
                        self._modbus_set_on(mbclient, self.mb_conveyor_start_term)
                
                if command == 'conveyor_stop':
                    self._modbus_set_on(mbclient, self.mb_conveyor_stop_term)
                    self._modbus_set_off(mbclient, self.mb_conveyor_start_term)
                    self._conveyor_state = 'Off'
                
                if command == 'conveyor_reset':
                    self._modbus_set_off(mbclient, self.mb_conveyor_start_term, force=True)
                    self._modbus_set_off(mbclient, self.mb_conveyor_stop_term, force=True)
                    self._modbus_set_off(mbclient, self.mb_alarm_trigger, force=True)
                    self._conveyor_state = 'On'
                            
                if command == 'alarm_start':
                    self._modbus_set_on(mbclient, self.mb_alarm_trigger)
                    self._alarm_state = 'On'
                
                if command == 'alarm_stop':
                    self._modbus_set_off(mbclient, self.mb_alarm_trigger)
                    self._alarm_state = 'Off'

                if command == 'process_end_of_pulse':
                    for target in self.modbus_pulse_list.copy():
                        self.modbus_pulse_list.discard(target)
                        self._modbus_set_off(mbclient, target, force=True)
                
                mbclient.close()
            except:
                message = f"an error ocurred sending {command} command to modbus {self.modbus_ip}"
            app.logger.alert(message)
            self.sem_busy.release()
            self._background_counter('-')
            if self.background_counter == 0 and len(self.modbus_pulse_list):
                time.sleep(self.mb_signal_pulse_seconds)
                self._modbus_command('process_end_of_pulse')
        else:
            self._background_counter('-')
            message = f"could not acquire semaphore sending {command} command to modbus {self.modbus_ip}"
            app.logger.alert(message)

        return message


    def background_task(self, background_tasks, task):
        self._background_counter('+')
        return background_tasks.add_task(task)


    def conveyor_start(self):
        return self._modbus_command('conveyor_start', full_start = False)


    def conveyor_full_start(self):
        return self._modbus_command('conveyor_start', full_start = True)


    def conveyor_stop(self):
        return self._modbus_command('conveyor_stop')


    def conveyor_reset(self):
        return self._modbus_command('conveyor_reset')


    def conveyor_state(self):
        return { 'conveyor_state': self._conveyor_state }


    def alarm_start(self):
        return self._modbus_command('alarm_start')


    def alarm_stop(self):
        return self._modbus_command('alarm_stop')


    def alarm_state(self):
        return { 'alarm_state': self._alarm_state }


    def carwash_status(self):
        retval = {}        
        for a in [a for a in dir(self) if not a.startswith('__') and not callable(getattr(self, a))]:
            if a.startswith('_'):
                retval[a[1:]] = getattr(self, a)
            else:
                retval[a] = getattr(self, a)
        return retval



'''
----
MISC
----
'''

def ApiResponse(data = '', error = '', code = 200):
    success = True if not error else False
    response = {}
    response['success'] = success
    response['timestamp'] = datetime.now(app.tz)
    response['function'] = inspect.stack()[1][3]
    if success:    
        response['data'] = data
    else:
        data['reason'] = error
        response['error'] = data
    return response
