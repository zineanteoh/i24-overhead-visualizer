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
from multiprocessing import Process, Queue
import time # temporary

class Visualizer():
    """
    Visualizer utilizes i24_database_api to query trajectories
    information and plot a visualization of the vehicles using opencv
    """
    
    def __init__(self, config):
        """
        Initializes an Overhead Traffic VIsualizer object
        """
        self.dbr = DBReader(host=config["host"], 
                       port=config["port"], 
                       username=config["username"], 
                       password=config["password"], 
                       database_name=config["database_name"], 
                       collection_name=config["collection_name"])
        
        # window width and height
        self.w = 600
        self.h = 1000
        
    def quit(self):
        cv2.destroyAllWindows()
        
    def rotate_img(self, img, angle = 0, bound = False):
        """
        Return a rotated img for cv2 
        """
        if bound:
            return imutils.rotate_bound(img, angle)
        else:
            return imutils.rotate(img, angle)
    
    def setup_window(self):
        cv2.namedWindow('window')
        # blank white window
        self.img = 255 * np.ones((self.w, self.h, 3))
        cv2.imshow('window', self.img)
        
    def collect_data(self, conn):
        """
        A child process to parallelize data collection
        """
        buffer_size = 30
        count = 0
        while True:
            # maintain buffer size
            if conn.qsize() >= buffer_size:
                print("sleeping...")
                time.sleep(1)
                continue
            
            # get data
            xval = np.random.randint(400)
            yval =  np.random.randint(400)
            rand_color = (np.random.randint(255), 
                          np.random.randint(255),
                          np.random.randint(255))
            
            # send data to multiprocessing Queue
            conn.put([xval, yval, rand_color])
            # print("collecting data...", [xval, yval, rand_color])
            # time.sleep(1)
            
            # testing purpose
            count += 1
            if count > 100:
                break
        cv2.destroyAllWindows()
    
    def plot_data(self, conn):
        """
        A child process to parallelize data plotting
        """
        self.setup_window()
        while True:
            print("waiting data...")
            
            # get data
            data = conn.get()
            x = data[0]
            y = data[1]
            color = (0, 0, 255)
            # print("data received: ({}, {}, {})".format(x, y, color))
            
            # clear frame
            self.img = 255 * np.ones((self.w, self.h, 3))
            
            # plot
            cv2.rectangle(self.img, (x, y), (500, 500), color, -1)
            # cv2.rectangle(self.img, (200, 200), (500, 500), color, -1)
            
            # show
            cv2.imshow('window', self.img)
            
            # wait for key press for next frame
            print("waiting key...")
            cv2.waitKey(0)
        print("plotting complete")
    
    def visualize_road_segment(self): 
        """
        Visualizes road segment by initializing multiprocessing with Queue
        """
        conn = Queue()
        print("Starting data collection process...")
        duta = Process(target=self.collect_data, args=(conn,))
        duta.start()
        
        print("Starting plotting process...")
        plut = Process(target=self.plot_data, args=(conn,))
        plut.start()
        
        duta.join()
        plut.join()
        
        print("complete")

if True and __name__=="__main__":
    
    os.chdir("/isis/home/teohz/Desktop/videowall")
    with open('config.json') as f:
        config = json.load(f)
    
    viz = Visualizer(config)
    viz.visualize_road_segment()