#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Sep 18 12:27:36 2022

@author: zitest

TODOs: 
    1. Attempt to speed up overhead_compare.py by utilizing openCV's plotting API
    2. Attempt to publish visualization to a web server by utilizing Flask(?) Bokeh(?)

"""

from i24_database_api import DBClient
from datetime import datetime
from flask import Response
from flask import Flask
from flask import render_template
import numpy as np
import threading
import time
import json
import cv2

outputFrame = None
lock = threading.Lock()

class OverheadCompareV2():
    """
    compare the overhead views of two collecctions
    """
    
    def __init__(self, config, collections = None,
                 framerate = 25, x_min = 0, x_max = 1500, offset = None ,duration = 60):
        
        list_dbr = [] # time indexed
        list_veh = [] # vehicle indexed
        list_db = ["trajectories", "trajectories", "reconciled"] # gt, raw, rec
        trans = DBClient(**config, database_name = "transformed")
        transformed_collections = trans.list_collection_names()
        
        # first collection is GT
        for i,collection in enumerate(collections):
            dbr = DBClient(**config, database_name = "transformed", collection_name=collection)
            veh = DBClient(**config, database_name = list_db[i], collection_name=collection)
            dbr.create_index("timestamp")
            list_dbr.append(dbr)
            list_veh.append(veh)
            
            if collection not in transformed_collections:
                # print("Transform ", collection)
                veh.transform()
            
        
        if len(list_dbr) == 0:
            raise Exception("at least one collection must be specified.")
        
        # get plotting ranges
        t_min = max([dbr.get_min("timestamp") for dbr in list_dbr])
        t_max = min([dbr.get_max("timestamp") for dbr in list_dbr])
        if offset:
            t_min += offset  
        if duration: 
            t_max = min(t_max, t_min + duration)
        
        self.x_start = x_min
        self.x_end = x_max
        self.t_min = t_min
        self.t_max = t_max
        
        # Initialize animation
        self.anim = None
        self.framerate = framerate if framerate else 25
        
        self.lanes = [i*12 for i in range(-1,12)]   
        self.lane_name = [ "EBRS", "EB4", "EB3", "EB2", "EB1", "EBLS", "WBLS", "WB1", "WB2", "WB3", "WB4", "WBRS"]
        self.lane_idx = [i for i in range(12)]
        self.lane_ax = [[1,5],[1,4],[1,3],[1,2],[1,1],[1,0],[0,0],[0,1],[0,2],[0,3],[0,4],[0,5]]
        
        # self.annot_queue = queue.Queue()
        # self.cursor = None
        
        # self.list_dbr =  list_dbr
        # self.list_veh = list_veh
        
        self.window_w = 1200
        self.window_h = 600
        
    def refresh_frame(self):
        """
        Set up frame to plot
        """
        # frame to plot
        self.frame = np.full(shape=(self.window_h, self.window_w, 3), 
                             fill_value=255,
                             dtype=np.float64)
        # add line 
        

    def animate(self, save, upload, stream, extra): 
        
        # initiate frame 
        self.refresh_frame()
        
        x1 = 0
        y1 = int(self.window_h / 2)
        direction = 'r'
        w = 75
        h = 25
        c = (255, 0, 0)
        
        if save:
            now = datetime.utcfromtimestamp(int(time.time())).strftime('%Y-%m-%d_%H-%M-%S')
            file_name = now+"_" + "random-trajectory" +extra+".mp4"
            path_name = "/home/zitest/Desktop/i24-overhead-visualizer/videos/" + file_name
            # write to file
            fourcc = cv2.VideoWriter_fourcc(*'MPEG')
            out = cv2.VideoWriter(path_name, fourcc, self.framerate, (self.window_w, self.window_h))

        end = False
        frame = 0
        if stream:
            global outputFrame, lock
        while True:
            if end:
                break
            
            # temporary move mechanism
            if x1 + w > self.window_w:
                direction = 'l'
            elif x1 < 0:
                direction = 'r'
            if direction == 'l':
                x1 -= 5
            else:
                x1 += 5
            
            # clear frame
            self.refresh_frame()
            # plot vehicles
            cv2.rectangle(self.frame, (x1, y1), (x1 + w, y1 + h), c, cv2.FILLED)
            # add frame number
            cv2.putText(self.frame, 'Frame # {f}'.format(f=frame), 
                        org=(10, self.window_h - 20), fontFace=cv2.FONT_HERSHEY_DUPLEX,
                        fontScale=1, color=(0, 0, 0), thickness=1, lineType=1)
            if not stream:
                cv2.imshow("i24 overhead compare v2", self.frame)
            
            # save
            if save:
                out.write(self.frame.astype(np.uint8))
            
            # end with escape
            k = cv2.waitKey(int(1000/self.framerate)) & 0xFF
            if k == 27:
                end = True
                break
            
            frame += 1
            
            # acquire lock, set output frame, and release lock
            if stream:
                print('Current lock: ', lock)
                with lock:
                    outputFrame = self.frame.copy()
        
        if save:
            out.release()
        cv2.destroyAllWindows()
        return
    
    def generate_stream(self):
        # grab global references to the output frame and lock variables
    	global outputFrame, lock
    	# loop over frames from the output stream
    	while True:
    		# wait until the lock is acquired
    		with lock:
    			# check if the output frame is available, otherwise skip
    			# the iteration of the loop
    			if outputFrame is None:
    				continue
    			# encode the frame in JPEG format
    			(flag, encodedImage) = cv2.imencode(".jpg", outputFrame)
    			# ensure the frame was successfully encoded
    			if not flag:
    				continue
    		# yield the output frame in the byte format
    		yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
    			bytearray(encodedImage) + b'\r\n')
    
    def setup_stream(self):
        self.app = Flask(__name__)
        
        @self.app.route("/")
        def index():
        	# return the rendered template
        	return render_template("index.html")
        
        @self.app.route("/video_feed")
        def video_feed():
        	# return the response generated along with the specific media
        	# type (mime type)
        	return Response(self.generate_stream(),
        		mimetype = "multipart/x-mixed-replace; boundary=frame")

    def start_stream(self):
        self.app.run(host="0.0.0.0",
                     port=8000,
                     debug=True,
                     threaded=True,
                     use_reloader=False)


def main(rec, gt = "groundtruth_scene_2_57", framerate = 25, x_min=-100, x_max=2200, offset=0, duration=500, 
         save=False, upload=False, extra="", stream=False):
    
    # change path to config
    with open("/home/zitest/Desktop/i24-overhead-visualizer/config.json") as f:
        db_param = json.load(f)
    
    raw = rec.split("__")[0]
    print("Generating a video for {}...".format(rec))
    p = OverheadCompareV2(db_param, 
                collections = [gt, raw, rec],
                framerate = framerate, x_min = x_min, x_max=x_max, offset = offset, duration=duration)
    if stream:
        p.setup_stream()
        
        t = threading.Thread(target=p.animate, args=(
            False, False, True, "",))
        t.daemon = True
        t.start()
        
        print("starting animate process: ", t.native_id)
        
        p.start_stream()
    else:
        p.animate(save=save, upload=upload, stream=stream, extra=extra)
    
if __name__=="__main__":

    main(rec = "zonked_cnidarian--RAW_GT2__articulates", save=False, upload=False, stream=True)
    
        


