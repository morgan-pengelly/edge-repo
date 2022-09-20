import requests
from threading import Semaphore
import time
import random


class MessageRepetitionControl:

    class MRC:
        def __init__(self, message = None, repeat_after = 0):
            self.message = message
            self.repeat_after = repeat_after
            self.counter = 0


    def __init__(self):
        self.messages_dict = {}
        self.semaphore = Semaphore(1)


    def message_filter(self, message = None, message_id = None, repeat_after=10):
        if not message or not message_id: return message
        if not self.semaphore.acquire(5): return message
        ret_message = message
        mrc = self.messages_dict.get(message_id, None)
        if mrc:
            if mrc.message == message:
                mrc.counter += 1
                mrc.repeat_after = repeat_after
                if mrc.counter > repeat_after:
                    mrc.counter = 1
                else:
                    ret_message = None
            else:
                mrc.message = message
                mrc.counter = 1
                mrc.repeat_after = repeat_after
        else:
            mrc = self.MRC(message, repeat_after)
            self.messages_dict[message_id] = mrc
        self.semaphore.release()
        return ret_message


class EdgeServicesClient:

    def __init__(self, api_address):
        self.disabled = False
        self.api_address = api_address
        self.api_url = "http://"+api_address+":8000"
        self.repeat_filter = MessageRepetitionControl().message_filter


    def __get_request(self, url_path='/'):
        retval = {}
        if self.disabled: return retval
        max_tries = 6
        retry = 0
        timeout = 0.8
        while retry < max_tries:
            try:
                r = requests.get(self.api_url + url_path, timeout=(0.1,timeout))
                if r.status_code == 200:
                    retval = r.json().get('data', r.json().get('error', {}))
                    break
            except Exception:
                pass
            timeout += 0.1
            retry+=1
            time.sleep(random.uniform(0.08, 0.15))
        return retval


    def __post_request(self, url_path='/', message=None):
        retval = {}
        if self.disabled: return retval
        max_tries = 6
        retry = 0
        timeout = 0.8
        while retry < max_tries:
            try:
                r = requests.post(self.api_url+url_path, data=message, timeout=(0.01,timeout))
                if r.status_code == 200:
                    retval = r.json().get('data', r.json().get('error', {}))
                    break
            except Exception:
                pass
            timeout += 0.1
            retry+=1
            time.sleep(random.uniform(0.08, 0.15))
        retval["retries"] = retry
        return retval


    def get_cameras_configuration(self):
        return self.__get_request("/config/cameras")


    def get_camsys_configuration(self):
        return self.__get_request("/config/camsys")


    def get_carwash_configuration(self):
        return self.__get_request("/config/carwash")


    def send_event(self, camera_id, state):
        return self.__post_request("/camera/{}/event/{}".format(camera_id, state))


    def send_keepalive(self, camera_id, state):
        return self.__post_request("/camera/{}/keepalive/{}".format(camera_id, state))


    def send_log(self, message='Empty message', log_type='report', log_id = None, repeat_after=0):
        f_message = self.repeat_filter(message=message, message_id=log_id, repeat_after=repeat_after)
        if not f_message: return {}
        return self.__post_request("/logger/{}?message={}".format(log_type, f_message))


edge_services = EdgeServicesClient('172.17.0.1')

