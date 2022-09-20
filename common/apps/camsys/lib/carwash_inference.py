#!/usr/bin/env python3

################################################################################
# SPDX-FileCopyrightText: Copyright (c) 2021 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
################################################################################

import sys
sys.path.append('../')
import gi
import pyds
# import configparser
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import GObject, Gst, GstRtspServer
# from gi.repository import GLib
from ctypes import *
from datetime import datetime
import time
import sys
import math
import threading
import re
# import random
# import platform
from common.is_aarch_64 import is_aarch64
from common.FPS import GETFPS

import socket
from urllib.parse import urlparse

import traceback

from edge_services_camlib import edge_services

import re
import os
import collections
import helper
import carwash_logging

VERSION = "2.0"

#----------------------------------------------------------------------------
# DeepStreamInference
#----------------------------------------------------------------------------
class DeepStreamInference(threading.Thread):

    def __init__(self,fifo_queue,args,event_manager_thread):

        self.args = args
        self.logger = carwash_logging.setup_timed_rotating_logger('inference_engine', '../logs/inference_engine.log')
        self.fifo_queue = fifo_queue
        
        self.MUXER_OUTPUT_WIDTH = 1280
        self.MUXER_OUTPUT_HEIGHT = 720
        self.TILED_OUTPUT_WIDTH = 1280
        self.TILED_OUTPUT_HEIGHT = 720

        self.PGIE_CLASS_ID_BACKGROUND = 0
        self.PGIE_CLASS_ID_PERSON = 1
        self.PGIE_CLASS_ID_VEHICLE = 2
        self.PGIE_CLASS_ID_FRONTLIGHT = 3
        self.PGIE_CLASS_ID_BACKLIGHT = 4

        self.no_display = False
        self.use_inference = True
        self.client_demo_mode = True

        self.is_live = False
        self.is_file = False
        self.isEdgeService = True
        self.printDebug = 0 #-1: no-print, 0:minimum, 1:devloper, 2:system


        # this is setup when adding sources
        self.NO_OF_CAMERAS = -1 


        self.pipeline = None
        self.streammux = None

        self.DRY_RUN = False
        self.ROLLING_FRAME = True
        self.ABSOLUTE_DIST = True


        self.source_id_list = []
        self.eos_list = []
        self.source_enabled = []
        self.source_bin_list = []
        self.uri = []
        self.frame_count = []

        self.fps_streams={}
        self.cameras_dict = {}
               

        self.distance_array = {}
        self.distance_array_val = {}

        self.prev_status = {}
        self.current_status = {}
        self.no_detection_counter = {}
        
        #rtsp output parameters
        self.out_rtsp_codec = "VP9"
        self.out_rtsp_bitrate = 4000000
        self.out_rtsp_port_number = 5400
        self.out_rtsp_user = "user"
        self.out_rtsp_password = "pass"
        self.bStop = False
        self.event_manager_thread = event_manager_thread
        
        super().__init__()
        
    # signaled to stop deepstream engine, terminates with bStop
    def stop(self):
        self.logger.info("signal to stop inference engine")
        self.bStop = True

    # setup_ds_source()
    def setup_ds_source(self):

        if self.NO_OF_CAMERAS > 0:
            self.source_id_list = [0] * self.NO_OF_CAMERAS
            self.eos_list = [False] * self.NO_OF_CAMERAS
            self.source_enabled = [False] * self.NO_OF_CAMERAS
            self.source_bin_list = [None] * self.NO_OF_CAMERAS
            self.event_camera_disconnect_sent = [False] * self.NO_OF_CAMERAS
            self.uri = [0] * self.NO_OF_CAMERAS
            self.frame_count = [0] * self.NO_OF_CAMERAS

            return True
        return False

    def init_from_edge_config(self):

        try:
            camsys_dict = edge_services.get_camsys_configuration()
            self.cameras_dict = edge_services.get_cameras_configuration()

        except Exception:
            print("Exception in --init_from_edge_config--")
            traceback.print_exception(*sys.exc_info())
            return False

        return True
    
    def print_debug(self, print_str, level=0):
        '''
        level_dict = {0:'Info:', 1:'Developer:', 2:'System:'}
        if self.printDebug >= level:
            print(f'{level_dict[level]} {print_str}')
        '''
        pass

    def set_cameras_to_undefined(self):
        for i in range(self.NO_OF_CAMERAS):
            self.event_manager_thread.fifo_queue.put((i+1,"U","","event"))
            self.logger.info("sending event U for camera %s", str(i+1))

    def getIPnPort(self, url_string):

        hostname, port = '', -1
        try:
            ret = urlparse(url_string)
            hostname = ret.hostname
            port = ret.port
        except Exception as e:
            self.logger.info(f" Exception in getIPnPort | url_string:{url_string} message:{str(e)}")
            traceback.print_exception(*sys.exc_info())

        return (hostname, port )


    def isCamAlive(self, url_str):
        result_of_check = -1
        location = self.getIPnPort(url_str)
        try:
            a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result_of_check = a_socket.connect_ex(location)
            a_socket.close()
        except Exception as e:
            self.logger.info(f"isCamAlive | location:{location} message:{str(e)}")
            traceback.print_exception(*sys.exc_info())

        return True if result_of_check == 0 else False

    # tiler_sink_pad_buffer_probe  will extract metadata received on tiler 
    # src pad and update params for drawing rectangle, object information etc.
    def tiler_sink_pad_buffer_probe(self, pad, info, u_data):
        frame_number = 0
        num_rects = 0
        gst_buffer = info.get_buffer()
        if not gst_buffer:
            self.print_debug("Unable to get GstBuffer ")
            return
        inference_objects = list()
        for i in range(self.NO_OF_CAMERAS):
            inference_objects.append(list())
        # Retrieve batch metadata from the gst_buffer
        # Note that pyds.gst_buffer_get_nvds_batch_meta() expects the
        # C address of gst_buffer as input, which is obtained with hash(gst_buffer)
        batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))

        l_frame = batch_meta.frame_meta_list

        display_meta=pyds.nvds_acquire_display_meta_from_pool(batch_meta)
        objects_x2x1 = {}
        while l_frame is not None:
            try:
                # Note that l_frame.data needs a cast to pyds.NvDsFrameMeta
                # The casting is done by pyds.NvDsFrameMeta.cast()
                # The casting also keeps ownership of the underlying memory
                # in the C code, so the Python garbage collector will leave
                # it alone.
                frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
                
                stream_number = frame_meta.pad_index
                camera_id = stream_number + 1

                num_rects = frame_meta.num_obj_meta
                l_obj=frame_meta.obj_meta_list
                inference_objects[int(frame_meta.pad_index)].append({"left" : -1, "top" : -1,"width" : -1, "height" : -1, "class_id" : -1, "frame_number" : frame_meta.frame_num })
                while l_obj is not None:
                    try:
                        obj_meta=pyds.NvDsObjectMeta.cast(l_obj.data)
                        if obj_meta.rect_params.left < 0:
                            obj_meta.rect_params.left = 1
                        if obj_meta.rect_params.top < 0:
                            obj_meta.rect_params.top = 1
                        if obj_meta.rect_params.width < 0:
                            obj_meta.rect_params.width = 1
                        if obj_meta.rect_params.height < 0:
                            obj_meta.rect_params.height = 1
                        inference_objects[int(frame_meta.pad_index)].append({"left" : obj_meta.rect_params.left, "top" : obj_meta.rect_params.top,"width" : obj_meta.rect_params.width, "height" : obj_meta.rect_params.height, "class_id" : obj_meta.class_id })
                        l_obj=l_obj.next
                    except StopIteration:
                        break
                    except Exception:
                        traceback.print_exception(*sys.exc_info())
                
                l_frame=l_frame.next            
            except StopIteration:
                break
            except Exception:
                traceback.print_exception(*sys.exc_info())

            frame_number = frame_meta.frame_num

        self.fifo_queue.put(inference_objects)
        
        return Gst.PadProbeReturn.OK

    # decodebin_child_added
    def decodebin_child_added(self, child_proxy, Object, name, user_data):

        self.print_debug(f"Decodebin child added:{name}\n")
        if(name.find("decodebin") != -1):
            Object.connect("child-added", self.decodebin_child_added, user_data)   
        if(name.find("nvv4l2decoder") != -1):
            if (is_aarch64()):
                Object.set_property("enable-max-performance", True)
                Object.set_property("drop-frame-interval", 0)
                Object.set_property("num-extra-surfaces", 0)
            else:
                Object.set_property("gpu_id", 0)

    # cb_newpad
    def cb_newpad(self, decodebin, pad, data):

        self.print_debug("In cb_newpad\n")
        caps=pad.get_current_caps()
        gststruct=caps.get_structure(0)
        gstname=gststruct.get_name()

        # Need to check if the pad created by the decodebin is for video 
        self.print_debug(f"gstname={gstname}")
        if(gstname.find("video")!=-1):
            source_id = data
            pad_name = "sink_%u" % source_id
            self.print_debug(pad_name)
            
            # Get a sink pad from the streammux, link to decodebin
            sinkpad = self.streammux.get_request_pad(pad_name)
            if pad.link(sinkpad) == Gst.PadLinkReturn.OK:
                self.print_debug("Decodebin linked to pipeline")
            else:
                self.print_debug("Failed to link decodebin to pipeline\n")

    # create_uridecode_bin
    def create_uridecode_bin(self, index, filename):

        self.print_debug(f"Creating uridecodebin for {filename}")

        # Create a source GstBin to abstract this bin's content from the rest 
        # of the pipeline
        self.source_id_list[index] = index
        bin_name="source-bin-%02d" % index
        self.print_debug(bin_name)

        # Source element for reading from the uri.
        # We will use decodebin and let it figure out the container format of the
        # stream and the codec and plug the appropriate demux and decode plugins.
        bin=Gst.ElementFactory.make("uridecodebin", bin_name)
        if not bin:
            self.print_debug(" Unable to create uri decode bin \n")

        # We set the input uri to the source element
        bin.set_property("uri", filename)

        # Connect to the "pad-added" signal of the decodebin which generates a
        # callback once a new pad for raw data has been created by the decodebin
        bin.connect("pad-added", self.cb_newpad, self.source_id_list[index])
        bin.connect("child-added", self.decodebin_child_added, self.source_id_list[index])

        # Set status of the source to enabled
        self.source_enabled[index] = True

        return bin

    # stop_release_source     
    def stop_release_source(self, source_id):

        #self.print_debug(f"Stop and release the source:{source_id} \n")

        # Attempt to change status of source to be released 
        state_return = self.source_bin_list[source_id].set_state(Gst.State.NULL)

        if state_return == Gst.StateChangeReturn.SUCCESS:
            self.print_debug("STATE CHANGE SUCCESS\n")
            pad_name = "sink_%u" % source_id
            self.print_debug(pad_name)
            
            # Retrieve sink pad to be released
            sinkpad = self.streammux.get_static_pad(pad_name)

            # Send flush stop event to the sink pad, then release from the 
            # streammux
            sinkpad.send_event(Gst.Event.new_flush_stop(False))
            self.streammux.release_request_pad(sinkpad)
            self.print_debug("STATE CHANGE SUCCESS\n")

            # Remove the source bin from the pipeline
            self.pipeline.remove(self.source_bin_list[source_id])
            source_id -= 1
            self.num_sources -= 1

        elif state_return == Gst.StateChangeReturn.FAILURE:
            self.print_debug("STATE CHANGE FAILURE\n")
    
        elif state_return == Gst.StateChangeReturn.ASYNC:
            state_return = self.source_bin_list[source_id].get_state(Gst.CLOCK_TIME_NONE)
            pad_name = "sink_%u" % source_id
            self.print_debug(pad_name)
            sinkpad = self.streammux.get_static_pad(pad_name)
            sinkpad.send_event(Gst.Event.new_flush_stop(False))
            self.streammux.release_request_pad(sinkpad)
            self.print_debug("STATE CHANGE ASYNC\n")
            self.pipeline.remove(self.source_bin_list[source_id])
            source_id -= 1
            self.num_sources -= 1


    # add_sources one by one to the pipeline
    def add_sources(self, data):
        # If is the maximum number of sources
        try:
            if self.num_sources == self.NO_OF_CAMERAS:
                return True

            for i, each  in  enumerate(self.source_enabled):
                if each == True:
                    continue
                else:
                    source_id  = i

                    if self.uri[source_id].find("rtsp://") == 0 :
                        if helper.isCamAlive(self.uri[source_id]):
                            self.logger.info(f"cam{source_id+1} is now connected with camera {self.uri[source_id]}")
                            self.event_manager_thread.fifo_queue.put((source_id+1,"",f"cam{source_id+1} is now connected with camera {self.uri[source_id]}","report"))
                            self.event_camera_disconnect_sent[source_id] = False

                        else:
                            if self.event_camera_disconnect_sent[source_id] == False:
                                self.logger.info(f"cam{source_id+1} is not responding {self.uri[source_id]}")
                                self.event_manager_thread.fifo_queue.put((source_id+1,"U","","event"))
                                self.event_manager_thread.fifo_queue.put((source_id+1,"","cam"+str(source_id+1)+"is not responding "+str(self.uri[source_id]),"report"))
                                self.event_camera_disconnect_sent[source_id] = True
                            continue
                    else:
                        if helper.is_valid_file(self.uri[source_id]) == True:
                            self.logger.info(f"cam{source_id+1} is now connected with file {self.uri[source_id]}")
                            self.event_manager_thread.fifo_queue.put((source_id+1,"",f"cam{source_id+1} is now connected with camera {self.uri[source_id]}","report"))
                            self.event_camera_disconnect_sent[source_id] = False
                        else:
                            if self.event_camera_disconnect_sent[source_id] == False:
                                self.logger.info(f"cam{source_id+1} is not responding {self.uri[source_id]}")
                                self.event_manager_thread.fifo_queue.put((source_id+1,"U","","event"))
                                self.event_manager_thread.fifo_queue.put((source_id+1,"","cam"+str(source_id+1)+"is not responding "+str(self.uri[source_id]),"report"))
                                self.logger.info("sending event U")
                                self.event_camera_disconnect_sent[source_id] = True
                            continue
                    # Enable the source
                    self.source_enabled[source_id] = True

                    # Create a uridecode bin with the chosen source id
                    source_bin = self.create_uridecode_bin(source_id, self.uri[source_id])
                    if (not source_bin):
                        self.print_debug("Failed to create source bin. Exiting.")
                        return True

                    # Add source bin to our list and to pipeline
                    self.source_bin_list[source_id] = source_bin
                    self.pipeline.add(source_bin)

                    # Set state of source bin to playing
                    state_return = self.source_bin_list[source_id].set_state(Gst.State.PLAYING)
                    if state_return == Gst.StateChangeReturn.SUCCESS:
                        self.print_debug("STATE CHANGE SUCCESS")
                    elif state_return == Gst.StateChangeReturn.FAILURE:
                        self.print_debug("STATE CHANGE FAILURE")
                    elif state_return == Gst.StateChangeReturn.ASYNC:
                        state_return = self.source_bin_list[source_id].get_state(Gst.CLOCK_TIME_NONE)
                    elif state_return == Gst.StateChangeReturn.NO_PREROLL:
                        self.print_debug("STATE CHANGE NO PREROLL")

                    self.num_sources += 1
        except Exception as e:
            self.logger.info("error adding sources: %s",str(e))
        return True


    # bus_call
    def bus_call(self, bus, message, loop):

        t = message.type
        if t == Gst.MessageType.EOS:
            self.logger.info(f"End-of-stream")
            if not self.is_live:
                loop.quit()

        elif t==Gst.MessageType.WARNING:
            err, debug = message.parse_warning()
            self.print_debug(f"Warning!!{err}:{debug}\n")

        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            self.print_debug(f"Error!!{err}:{debug}\n")
            loop.quit()

        elif t == Gst.MessageType.ELEMENT:
            struct = message.get_structure()
            # Check for stream-eos message
            if struct is not None and struct.has_name("stream-eos"):
                parsed, stream_id = struct.get_uint("stream-id")
                if parsed:
                    # Set eos status of stream to True, to be deleted 
                    # in delete-sources
                    self.logger.info(f"Got EOS from stream {stream_id+1}")
                    self.eos_list[stream_id] = True

                    # Delete sources that have reached end of stream
                    if (self.source_enabled[stream_id]):
                        self.source_enabled[stream_id] = False
                    self.stop_release_source(stream_id)

        if self.num_sources == 0:
            loop.quit()

        return True
    
    def run(self):

        # Check input arguments
        vsource = []
        if len(self.args) >= 1:
            for i in range(0,len(self.args)):
                self.fps_streams["stream{0}".format(i)]=GETFPS(i)
            self.num_sources=len(self.args)
            self.NO_OF_CAMERAS=self.num_sources
            vsource = self.args
        self.setup_ds_source()
        
        # Standard GStreamer initialization
        GObject.threads_init()
        Gst.init(None)

        # Create gstreamer elements
        # Create Pipeline element that will form a connection of other elements
        self.print_debug("Creating Pipeline \n ")
        self.pipeline = Gst.Pipeline()

        if not self.pipeline:
            self.print_debug(" Unable to create Pipeline \n")
            return

        
        for i in range(self.num_sources):
            uri_name=vsource[i]
            if uri_name.find("rtsp://") == 0 :
                self.is_live = True
            else:
                if helper.is_valid_file(uri_name) == True:
                    self.is_file = True
                    self.is_live = False
                    break

        # Create nvstreammux instance to form batches from one or more sources.
        self.print_debug("Creating streammux \n ")
        self.streammux = Gst.ElementFactory.make("nvstreammux", "Stream-muxer")
        if not self.streammux:
            self.print_debug(" Unable to create NvStreamMux \n")
            return

        # Set streammux width and height
        self.streammux.set_property('width', self.MUXER_OUTPUT_WIDTH)
        self.streammux.set_property('height', self.MUXER_OUTPUT_HEIGHT)
        self.streammux.set_property("batched-push-timeout", 25000)
        self.streammux.set_property("batch-size", self.NO_OF_CAMERAS)
        self.streammux.set_property("gpu_id", 0)

        if self.client_demo_mode == False:
            if self.is_live:
                print("All sources are live")
                self.streammux.set_property('live-source', 1)
            if self.is_file:
                print("at least one source is static, limit framerate")
                self.streammux.set_property("sync-inputs", 1)
        elif self.client_demo_mode == True:
            self.streammux.set_property('live-source', 1)
             


        self.pipeline.add(self.streammux)

        number_sources = self.num_sources
        for i in range(number_sources):
                self.print_debug(f"Creating source_bin:{i}\n")
 
                uri_name=vsource[i]
                print("i: ",i)
                print("uri_name: ",uri_name)
                self.uri[i] = uri_name
                if uri_name.find("rtsp://") == 0 :
                    self.is_live = True
                    # Checks if the camera stream works, else skip creation 
                    if helper.isCamAlive(uri_name):
                        self.logger.info(f"cam{i+1} is now connected with camera {uri_name}")
                    else:
                        self.logger.info(f"cam{i+1} is not responding {uri_name}")
                        self.num_sources -= 1
                        if self.num_sources == 0:
                            self.print_debug("No Active Camera found. Restarting!!!")
                            return False
                        else:
                            self.source_enabled[i] = False
                            continue
                # is not live source, then check the file exists
                else:
                    if helper.is_valid_file(uri_name) == True:
                        self.logger.info(f"cam{i+1} is now connected with camera {uri_name}")
                    else:
                        self.logger.info(f"cam{i+1} is not responding {uri_name}")
                        self.num_sources -= 1
                        if self.num_sources == 0:
                            self.print_debug("No Active Camera found. Restarting!!!")
                            return False
                        else:
                            self.source_enabled[i] = False
                            continue
                
                # Create source bins and add to pipeline
                source_bin=self.create_uridecode_bin(i, uri_name)
                if not source_bin:
                    self.print_debug("Failed to create source bin. \n")
                    self.num_sources -= 1
                    self.source_enabled[i] = False
                    continue

                self.source_bin_list[i] = source_bin
                self.source_enabled[i] = True
                self.pipeline.add(source_bin)

        if self.num_sources == 0:
           return False        

        # pgie
        if self.use_inference:
            self.print_debug("Creating Pgie \n ")
            pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
            if not pgie:
                self.print_debug(" Unable to create pgie \n")
                return

            # Set pgie configuration file paths
            pgie.set_property('config-file-path', "config_inference_primary_ssd.txt")

            # Set necessary properties of the nvinfer element, 
            # the necessary ones are:
            pgie_batch_size = pgie.get_property("batch-size")
            if(pgie_batch_size < self.NO_OF_CAMERAS):
                self.print_debug(f"Overriding infer-config batch-size:{pgie_batch_size} with number of sources:{self.num_sources}\n")
            pgie.set_property("batch-size", self.NO_OF_CAMERAS)

            # Set gpu IDs of the inference engines
            pgie.set_property("gpu_id", 0)


        # Tiler
        self.print_debug("Creating tiler \n ")
        tiler=Gst.ElementFactory.make("nvmultistreamtiler", "nvtiler")
        if not tiler:
            self.print_debug(" Unable to create tiler \n")
            return

        # Set tiler properties
        tiler.set_property("rows", 2)
        tiler.set_property("columns", 3)
        tiler.set_property("width", self.TILED_OUTPUT_WIDTH)
        tiler.set_property("height", self.TILED_OUTPUT_HEIGHT)
        tiler.set_property("gpu_id", 0)


        # NVVidConv
        self.print_debug("Creating nvvidconv \n ")
        nvvideoconvert = Gst.ElementFactory.make("nvvideoconvert", "convertor")
        if not nvvideoconvert:
            self.print_debug(" Unable to create nvvidconv \n")
            return
        nvvideoconvert.set_property("gpu_id", 0)

        # NVOsd
        self.print_debug("Creating nvosd \n ")
        nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")
        if not nvosd:
            self.print_debug(" Unable to create nvosd \n")
            return
        nvosd.set_property("gpu_id", 0)

        # set up post NVOsd
        nvvidconv_postosd = Gst.ElementFactory.make("nvvideoconvert", "convertor_postosd")
        if not nvvidconv_postosd:
            self.print_debug("Unable to create nvvidconv_postosd")
            return False
            
        # set up caps filter
        caps = Gst.ElementFactory.make("capsfilter", "filter")
        caps.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM), format=I420"))
        
        # build stream
        if self.out_rtsp_codec == "VP9":
            encoder = Gst.ElementFactory.make("nvv4l2vp9enc", "encoder")
            self.print_debug("Creating VP9 Encoder")
        elif self.out_rtsp_codec == "H264":
            encoder = Gst.ElementFactory.make("nvv4l2h264enc", "encoder")
            self.print_debug("Creating H264 Encoder")
        elif self.out_rtsp_codec == "H265":
            encoder = Gst.ElementFactory.make("nvv4l2h265enc", "encoder")
            self.print_debug("Creating H265 Encoder")
        if not encoder:
            self.print_debug(" Unable to create encoder")
            return False
        encoder.set_property('bitrate', self.out_rtsp_bitrate)
        
        # jetson specific properties
        if is_aarch64():
            encoder.set_property('preset-level', 1)
            encoder.set_property('bufapi-version', 1)
        
        # RTP package builder
        if self.out_rtsp_codec == "VP9":
            rtppay = Gst.ElementFactory.make("rtpvp9pay", "rtppay")
            self.print_debug("Creating H264 rtppay")
        elif self.out_rtsp_codec == "H264":
            rtppay = Gst.ElementFactory.make("rtph264pay", "rtppay")
            self.print_debug("Creating H264 rtppay")
        elif self.out_rtsp_codec == "H265":
            rtppay = Gst.ElementFactory.make("rtph265pay", "rtppay")
            self.print_debug("Creating H265 rtppay")
        if not rtppay:
            self.print_debug("Unable to create rtppay")
        
        # UDP sink
        updsink_port_num = self.out_rtsp_port_number
        sink = Gst.ElementFactory.make("udpsink", "udpsink")
        if not sink:
            self.print_debug("Unable to create udpsink")

        sink.set_property('host', '224.224.255.255')
        sink.set_property('port', updsink_port_num)
        sink.set_property('async', False)
        sink.set_property('sync', 0)
        sink.set_property('qos', 0)

        if sink:
            if(not is_aarch64()):
                sink.set_property("gpu_id", 0)
        
        self.print_debug("Adding elements to Pipeline")
        if self.use_inference:
            self.pipeline.add(pgie)
        self.pipeline.add(tiler)
        self.pipeline.add(nvvideoconvert)
        self.pipeline.add(nvosd)
        self.pipeline.add(nvvidconv_postosd)
        self.pipeline.add(caps)
        self.pipeline.add(encoder)
        self.pipeline.add(rtppay)
        self.pipeline.add(sink)
        
        self.print_debug("Linking elements in the Pipeline")
        if self.use_inference:
            self.streammux.link(pgie)
            pgie.link(tiler)
        else:
            self.streammux.link(tiler)
        tiler.link(nvvideoconvert)
        nvvideoconvert.link(nvosd)
        
        nvosd.link(nvvidconv_postosd)
        nvvidconv_postosd.link(caps)
        caps.link(encoder)
        encoder.link(rtppay)
        rtppay.link(sink)

        # create an event loop and feed gstreamer bus mesages to it
        loop = GObject.MainLoop()
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.bus_call, loop)

        # Create stream with user and password and start streaming
        rtsp_port_num = 554
        self.out_rtsp_user = "user"
        self.out_rtsp_password = "pass"
        server = GstRtspServer.RTSPServer.new()
        server.props.service = "%d" % rtsp_port_num
        auth = GstRtspServer.RTSPAuth()
        token = GstRtspServer.RTSPToken()
        token.set_string('media.factory.role', self.out_rtsp_user)
        basic = GstRtspServer.RTSPAuth.make_basic(self.out_rtsp_user, self.out_rtsp_password)
        auth.add_basic(basic, token)
        server.set_auth(auth)
        server.attach(None)

        factory = GstRtspServer.RTSPMediaFactory.new()
        factory.set_launch( "( udpsrc name=pay0 port=%d buffer-size=524288 caps=\"application/x-rtp, media=video, clock-rate=90000, encoding-name=(string)%s, payload=96 \" )" % (updsink_port_num, self.out_rtsp_codec))
        factory.set_shared(True)
        permissions = GstRtspServer.RTSPPermissions()
        permissions.add_permission_for_role(self.out_rtsp_user, "media.factory.access", True)
        permissions.add_permission_for_role(self.out_rtsp_user, "media.factory.construct", True)
        factory.set_permissions(permissions)
        server.get_mount_points().add_factory("/ds-test", factory)

        print("*** DeepStream: Launched RTSP Streaming at rtsp://user:pass@localhost:%d/ds-test ***" % rtsp_port_num)
        
        self.pipeline.set_state(Gst.State.PAUSED)

        # Tiler sink pad
        tiler_sink_pad = tiler.get_static_pad("sink")
        if not tiler_sink_pad:
            self.print_debug("Unable to get src pad")
            return False
        else:
            tiler_sink_pad.add_probe(Gst.PadProbeType.BUFFER, self.tiler_sink_pad_buffer_probe, 0)

        # List the sources
        self.logger.info("Now playing...")
        for i, source in enumerate(self.args):
            if (i != 0):
                self.print_debug(f"{i}:{source}")

        self.logger.info("Starting pipeline")

        # start play back and listed to events      
        self.pipeline.set_state(Gst.State.PLAYING)
        # Check closed connections and try to reopen them
        GObject.timeout_add_seconds(20, self.add_sources, self.source_bin_list)
        
        if self.bStop == True:
            loop.quit()

        try:
            loop.run()
        except:
            pass

        # cleanup
        self.logger.info("Exiting app")
        self.pipeline.set_state(Gst.State.NULL)

        return True

