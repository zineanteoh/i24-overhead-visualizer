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
import json
import cv2
import numpy as np

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
        self.frame = np.ones(shape=(self.window_h, self.window_w, 3),
                              dtype=np.float64)
        # add line 
        

    def animate(self):
        self.refresh_frame()
        
        x1 = 0
        y1 = int(self.window_h / 2)
        direction = 'r'
        w = 75
        h = 25
        c = (255, 0, 0)
        
        end = False
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
            
            
            self.refresh_frame()
            cv2.rectangle(self.frame, (x1, y1), (x1 + w, y1 + h), c, cv2.FILLED)
            cv2.imshow("i24 overhead compare v2", self.frame)
            
            k = cv2.waitKey(int(1/self.framerate * 1000)) & 0xFF
            # end with escape
            if k == 27:
                end = True
                break
        print("fr: ", int(1/self.framerate * 1000))
        cv2.destroyAllWindows()
        return


def main(rec, gt = "groundtruth_scene_2_57", framerate = 25, x_min=-100, x_max=2200, offset=0, duration=500, 
         save=False, upload=False, extra=""):
    
    # change path to config
    with open("/home/zitest/Desktop/i24-overhead-visualizer/config.json") as f:
        db_param = json.load(f)
    
    print(db_param)
    
    raw = rec.split("__")[0]
    print("Generating a video for {}...".format(rec))
    p = OverheadCompareV2(db_param, 
                collections = [gt, raw, rec],
                framerate = framerate, x_min = x_min, x_max=x_max, offset = offset, duration=duration)
    # p.animate(save=save, upload=upload, extra=extra)
    p.animate()
    
if __name__=="__main__":

    main(rec = "zonked_cnidarian--RAW_GT2__articulates", save=False, upload = False)
    
        


