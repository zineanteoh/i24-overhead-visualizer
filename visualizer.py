#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun  8 16:03:20 2022

@author: teohz
"""
from i24_database_api.db_reader import DBReader
import json
import os
import cv2
import numpy as np
import imutils
import pandas as pd
from multiprocessing import Process, Queue
import dill as pickle
import time # temporary
import math

class Visualizer():
    """
    Visualizer utilizes i24_database_api to query trajectories
    information and plot a visualization of the vehicles using opencv
    """
    
    def __init__(self, config):
        """
        Initializes an Overhead Traffic VIsualizer object
        """
        self.dbr = None
        # window width and height
        self.w = 1000
        self.h = 200
        self.timestamps = []
        
    def init_dbr_reader(self):
        self.dbr = DBReader(host=config["host"], 
                       port=config["port"], 
                       username=config["username"], 
                       password=config["password"], 
                       database_name=config["database_name"], 
                       collection_name=config["collection_name"])
        
    def quit(self):
        cv2.destroyAllWindows()
    
    def resample(self, car, has_position=False):
        # resample timestamps to 30hz, leave nans for missing data
        '''
        Original Author: Yanbing Wang
        Repository: I24-trajectory-generation/utils/reconciliation_module.py
        Modified by Zi Teoh to resample when car object has no positions
        
        resample the original time-series to uniformly sampled time series in 30Hz
        car: document
        '''
    
        # Select time series only
        try:
            if has_position:
                time_series_field = ["timestamp", "x_position", "y_position"]
            else:
                time_series_field = ["timestamp"]
            data = {key: car[key] for key in time_series_field}
            
            # Read to dataframe and resample
            df = pd.DataFrame(data, columns=data.keys()) 
            index = pd.to_timedelta(df["timestamp"], unit='s')
            df = df.set_index(index)
            df = df.drop(columns = "timestamp")
            df = df.resample('0.033333333S').mean() # close to 30Hz
            df.index = df.index.values.astype('datetime64[ns]').astype('int64')*1e-9
        
            if has_position:
                car['x_position'] = df['x_position'].values
                car['y_position'] = df['y_position'].values
            car['timestamp'] = df.index.values
        except Exception as e:
            print("Exception caught", e)
        return car

    def normalize_window(self):
        """
        Computes the optimal window dimension (self.w, self.h) and trajectory
        offset (self.x_offset, self.y_offset -- relative to center of window)
        by querying all vehicles of a random timestamp and averaging their
        positions
        """
        random_time = self.timestamps[np.random.randint(len(self.timestamps))]
        random_traj = self.dbr.collection.aggregate([
            {"$match": 
             {"timestamp": random_time}},
            {"$group":
             {"_id": "null",
              "avg_x": {"$avg": "$x_position"}, 
              "avg_y": {"$avg": "$y_position"}}}
        ])
        print(random_traj)
        return random_traj
    
    def setup_window(self):
        cv2.namedWindow('window')
        # blank white window
        self.img = 255 * np.ones((self.h, self.w, 3))
        cv2.imshow('window', self.img)
        
    def get_collection_timestamps(self):
        """
        Query the sorted list of distinct timestamps within the collection of
        trajectories. 
        
        (?) Does collection.distinct() return a sorted timestamp? 
        If not, then current approach is not suitable for large collection of 
        trajectories as it queries for distinct 'timestamp' and then sort it 
        in ascending order. 
        """
        self.timestamps = self.resample(self.dbr.collection.distinct("timestamp"))
        
    def collect_data(self, conn, start, end):
        """
        A child process to parallelize data collection
        """
        self.init_dbr_reader()
        buffer_size = 100000
        
        # get all distinct tiomestamps
        # self.get_collection_timestamps()
        min_timestamp = self.dbr.get_min("first_timestamp")
        max_timestamp = self.dbr.get_max("last_timestamp")
        fps = 30
        
        # normalize window using self.timestamps
        # self.normalize_window()
        
        print("[DATA] set up complete. begin querying frames")
        curr_timestamp = math.floor(min_timestamp)
        while curr_timestamp < math.ceil(max_timestamp):
            # maintain buffer size
            print("Frames queried: {}".format(conn.qsize()))
            #if conn.qsize() >= buffer_size:
            #    print("[DATA] sleeping...")
            #    time.sleep(1)
            #    continue
            
            traj_cursor = self.dbr.collection.find({
                {}, {"timestamp": {"$slice": curr_timestamp } }
            })
            
            trajectories = []
            for car_data in traj_cursor:
                car_data = self.resample(car_data, True)
                x = car_data["x_position"][index_to_plot]
                y = car_data["y_position"][index_to_plot]
                width = car_data["width"][0]
                length = car_data["length"][0]
                car_id = car_data["_id"]
                class_id = car_data["coarse_vehicle_class"]
                
                car_obj = {
                    "x": x,
                    "y": y,
                    "width": width,
                    "length": length,
                    "car_id": car_id,
                    "class_id": class_id
                }
                trajectories.append(car_obj)
            p = pickle.dumps(trajectories)
            
            # send data to multiprocessing Queue
            conn.put(p)
            index_to_plot += 1
        self.quit()
    
    def plot_data(self, conn, start, end):
        """
        A child process to parallelize data plotting
        """
        self.setup_window()
        frame = 0
        while True:
            # get data
            p = conn.get()
            traj_data = pickle.loads(p)
            
            color = (0, 0, 255)
            
            # clear frame
            self.img = 255 * np.ones((self.h, self.w, 3))
            
            # plot
            for car_data in traj_data:
                x = car_data["x"]
                y = car_data["y"]
                width = car_data["width"]
                length = car_data["length"]
                x = round(x)
                y = round(y)
                width = round(width)
                length = round(length)
                #if x + length >= 0 and x + length <= self.w:
                print("plotting vehicle from ({},{}) to ({}, {}) with color {}".format(x, y, x + length, y + width, color))
                cv2.rectangle(self.img, (x, y), (x + length, y + width), color, -1)
            
            # put frame number
            cv2.putText(self.img, "Frame #{}".format(frame), (50, 50), cv2.FONT_HERSHEY_PLAIN, 1, (255, 0, 0))
            frame += 1
            
            # show
            cv2.imshow('window', self.img)
            
            # wait for key press for next frame
            # print("[PLOT] waiting key...")
            cv2.waitKey(0)
        print("[PLOT] plotting complete")
    
    def visualize_road_segment(self, start=1000, end=2000): 
        """
        Visualizes road segment by initializing multiprocessing with Queue
        """
        conn = Queue()
        print("Starting data collection process...")
        duta = Process(target=self.collect_data, args=(conn, start, end,))
        duta.start()
        
        print("Starting plotting process...")
        plut = Process(target=self.plot_data, args=(conn, start, end,))
        plut.start()
        
        duta.join()
        plut.join()
        
        print("complete")

if True and __name__=="__main__":
    
    os.chdir("/isis/home/teohz/Desktop/videowall")
    with open('config.json') as f:
        config = json.load(f)
    
    test_run = True
    viz = Visualizer(config)
    # viz.init_dbr_reader()
    
    if test_run:
        viz.visualize_road_segment()