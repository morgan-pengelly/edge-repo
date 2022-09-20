from urllib.parse import urlparse
import socket,traceback,os
LOG_IDENTIFIER = "[deepstream_app] "

# initializes dict 
def init_dict(no_of_camera, isList=0, init_value=''):
    data_dict = {}
    for i in range(1, no_of_camera+1):
        if isList:
            data_dict[i] = []
        else:
            data_dict[i] = init_value
    return data_dict

# gets the ip of the port in the rtsp url
def getIPnPort(url_string):
    hostname, port = '', -1
    try:
        ret = urlparse(url_string)
        hostname = ret.hostname
        port = ret.port
    except Exception:
        pass
    return (hostname, port )
        
# checks if rtsp camera is alive and accessible
def isCamAlive(url_str):
    result_of_check = -1
    location = getIPnPort(url_str)
    try:
        a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result_of_check = a_socket.connect_ex(location)
        a_socket.close()
    except Exception:
        pass
    return True if result_of_check == 0 else False

# resets dictionary
def reset_dict(data_dict, isList=0, reset_value=''):
    for key in data_dict.keys():
        if isList:
           data_dict[key] = [] 
        else:
            data_dict[key] = init_value
    return data_dict

# file exists
def is_valid_file(url_str):
    if url_str.find("file://") ==0:
        new_url_str = url_str.replace("file://", "")
        return os.path.isfile(new_url_str)
    else:
        return os.path.isfile(url_str)
