#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun  1 15:42:19 2022

@author: teohz
"""
from i24_database_api.db_reader import DBReader
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.animation as animation
import mplcursors
import numpy as np
import cmd
import json
import os
import pymongo

class OverheadVisualizer():
    """
    Overhead Visualizer utilizes i24_database_api to query trajectories
    information and plot a visualization of the vehicles.
    """
    
    def __init__(self, config, MODE, 
                 vehicle_database, vehicle_collection, 
                 timestamp_database, timestamp_collection,
                 x_start=2000, x_end=1000,
                 framerate=25):
        """
        Initializes an Overhead Traffic VIsualizer object
        
        Parameters
        ----------
        config : object
        """
        self.timestamp_dbr = DBReader(host=config["host"], 
                                      port=config["port"], 
                                      username=config["username"], 
                                      password=config["password"], 
                                      database_name=timestamp_database, 
                                      collection_name=timestamp_collection)
        self.vehicle_dbr = DBReader(host=config["host"],
                                 port=config["port"],
                                 username=config["username"], 
                                 password=config["password"], 
                                 database_name=vehicle_database, 
                                 collection_name=vehicle_collection)
        self.anim = None
        self.MODE = MODE
        if self.MODE != "RAW" and self.MODE != "RECONCILED":
            raise ValueError("MODE must be either 'RAW' or 'RECONCILED'")
        # TODO dynamically set the most appropriate start and end
        self.x_start = x_start
        self.x_end = x_end
        self.framerate = framerate
        self.y_start = -12
        self.y_end = 11*12
        self.paused = False
        self.cursor = None
        self.vehicle_collection = vehicle_collection
        
    def visualize(self, frames=20000, save=False, verbose=False):
        """
        params:
            frames (int): 
                number of frames to plot. if exceeds max number 
                of frames in database, then animation will stop
            save (boolean): 
                whether to save animation as a .mp4 file
            verbose (boolean):
                whether to print messages related to visualization
                i.e. vehicle off the road plotted
        """
        
        fig = plt.figure()
        ax1 = fig.add_subplot(111)
        ax1.set_aspect('equal', 'box')
        ax1.set(ylim=[self.y_start, self.y_end])
        ax1.set_title("Bird-eye view")
        ax1.set(xlim=[self.x_start, self.x_end])
        
        # connect key press event to toggle pause
        fig.canvas.mpl_connect('key_press_event', self.toggle_pause)
        
        def on_xlims_change(event_ax):
            # print("updated xlims: ", event_ax.get_xlim())
            new_xlim = event_ax.get_xlim()
            # ax1.set(xlim=new_xlim)
            self.x_start = new_xlim[0]
            self.x_end = new_xlim[1]
        
        ax1.callbacks.connect('xlim_changed', on_xlims_change)
        
        def init():
            # plot lanes
            for i in range(-1, 12):
                if i in (-1, 5, 11):
                    plt.axhline(y=i*12, linewidth=0.5, color='k')
                else:
                    plt.axhline(y=i*12, linewidth=0.1, color='k')
            return ax1,
        
        def animate_reconciled(i, cursor, cache_vehicle, cache_colors):
            if (i % self.framerate > self.framerate):
                return ax1,
            
            ax1.set_title("{} | Frame {}".format(self.vehicle_collection, i))
            
            doc = cursor.next()
            
            # remove all car_boxes
            for box in list(ax1.patches):
                box.set_visible(False)
                box.remove()
            
            # query for vehicle dimensions
            traj_cursor = self.vehicle_dbr.collection.find({"_id": {"$in": doc["id"]} }, 
                                                           {"width":1, "length":1, "coarse_vehicle_class": 1})
        
            # add vehicle dimension to cache
            for index, traj in enumerate(traj_cursor):
                # print("index: {} is {}".format(index, traj))
                # { ObjectId('...') : [length, width, coarse_vehicle_class] }
                
                cache_vehicle[traj["_id"]] = [traj["length"], traj["width"], traj["coarse_vehicle_class"]]
            
                if traj["_id"] not in cache_colors:
                    cache_colors[traj["_id"]] = np.random.rand(3,)
            
            # plot vehicles
            for index in range(len(doc["position"])):
                car_x_pos = doc["position"][index][0]
                car_y_pos = doc["position"][index][1]
                
                car_length = cache_vehicle[doc["id"][index]][0]
                car_width = cache_vehicle[doc["id"][index]][1]
                
                if isinstance(car_width, list):
                    # vehicle width and length are lists
                    # TODO: currently just take the first item from the array
                    car_length = car_length[0]
                    car_width = car_width[0]
                
                # print("index {} at ({},{})".format(index, car_x_pos, car_y_pos))
                if car_x_pos <= self.x_start and car_x_pos >= self.x_end:
                    box = patches.Rectangle((car_x_pos, car_y_pos),
                                            car_length, car_width, 
                                            color=cache_colors[doc["id"][index]],
                                            label=doc["id"][index])
                    ax1.add_patch(box)
                    if verbose:
                        if car_y_pos > self.y_end or car_y_pos < self.y_start:
                            print("Vehicle off the road at coordinate ({}, {}) at frame={}".format(car_x_pos, car_y_pos, i))
            
            return ax1,
    
        def animate_raw(i, cursor, cache_colors):
            if (i % self.framerate > self.framerate):
                return ax1,
            
            ax1.set_title("{} | Frame {}".format(self.vehicle_collection, i))
            
            doc = cursor.next()
            
            # remove all car_boxes
            for box in list(ax1.patches):
                box.set_visible(False)
                box.remove()
            
            # plot vehicles
            for index in range(len(doc["id"])):
                car_id = doc["id"][index]
                if car_id not in cache_colors:
                    cache_colors[car_id] = np.random.rand(3,)
                car_x_pos = doc["position"][index][0]
                car_y_pos = doc["position"][index][1]
                
                car_length = doc["dimensions"][index][0]
                car_width = doc["dimensions"][index][1]
                
                # print("index {} at ({},{})".format(index, car_x_pos, car_y_pos))
                if car_x_pos <= self.x_start and car_x_pos >= self.x_end:
                    box = patches.Rectangle((car_x_pos, car_y_pos),
                                            car_length, car_width, 
                                            color=cache_colors[car_id],
                                            label=car_id)
                    ax1.add_patch(box)
                    if verbose:
                        if car_y_pos > self.y_end or car_y_pos < self.y_start:
                            print("Vehicle off the road at coordinate ({}, {}) at frame={}".format(car_x_pos, car_y_pos, i))
            
            return ax1,
        
        
        # maintains a cache of vehicle information (width, height, class)        
        # cache_vehicle[car_id] = [width, height, coarse_vehicle_class]
        cache_vehicle = {}
        cache_colors = {}
        
        cursor = self.timestamp_dbr.collection.find().sort([("timestamp", pymongo.ASCENDING)]).limit(frames)
        
        if self.MODE == "RAW":
            to_animate = animate_raw
            to_args = (cursor, cache_colors,)
        else:
            to_animate = animate_reconciled
            to_args = (cursor, cache_vehicle, cache_colors,)
        
        self.anim = animation.FuncAnimation(fig, func=to_animate,
                                            init_func=init,
                                            frames=frames,
                                            repeat=False,
                                            interval=2,
                                            fargs=to_args,
                                            blit=False)
        
        if save:
            self.anim.save('animation.mp4', writer='ffmpeg', fps=self.framerate)
        plt.show()
        print("complete")
    
    """
    press spacebar to pause/resume animation
    """
    def toggle_pause(self, event):
        if event.key == " ":
            if self.paused:
                self.anim.resume()
                print("Animation Resumed")
                self.cursor.remove()
            else:
                self.anim.pause()
                print("Animation Paused")
                self.cursor = mplcursors.cursor(hover=True)
                def on_add(sel):
                    if self.paused and (sel.artist.get_label()[0] != "_"):
                        print(sel.artist.get_label())
                        sel.annotation.set_text(sel.artist.get_label())
                # connect mouse event to hover for car ID
                self.cursor.connect("add", lambda sel: on_add(sel))
            self.paused = not self.paused
    
if True and __name__=="__main__":
    
    os.chdir("/isis/home/teohz/Desktop/videowall")
    with open('config.json') as f:
        config = json.load(f)
    
    test = 4
    
    if test == 1:
        # Collection with vehicle ID index 
        vehicle_database = "zitest"
        vehicle_collection = "ground_truth_two"
        
        # Collection with timestamp index
        timestamp_database = "zitest"
        timestamp_collection = "ground_truth_two_transformed"
        
        x_start=16000
        x_end=15000
        
        MODE = "RECONCILED"
    elif test == 2:
        # Collection with vehicle ID index 
        vehicle_database = "zitest"
        vehicle_collection = "tracking_v1"
        
        # Collection with timestamp index
        timestamp_database = "zitest"
        timestamp_collection = "tracking_v1_transformed"
        
        x_start=2000
        x_end=1000
        
        MODE = "RAW"
    elif test == 3:
        # Collection with vehicle ID index 
        vehicle_database = "zitest"
        vehicle_collection = "tracking_v1_reconciled_l1"
        
        # Collection with timestamp index
        timestamp_database = "zitest"
        timestamp_collection = "tracking_v1_reconciled_l1_transformed"
        
        x_start=2000
        x_end=1000
        
        MODE = "RECONCILED"
    elif test == 4:
        # Collection with vehicle ID index 
        vehicle_database = "zitest"
        vehicle_collection = "batch_5_07072022"
        
        # Collection with timestamp index
        timestamp_database = "zitest"
        timestamp_collection = "batch_5_07072022_transformed"
        
        x_start=2000
        x_end=1000
        
        MODE = "RAW"
    
    # Plot and visualize
    viz = OverheadVisualizer(config, MODE, 
                             vehicle_database, vehicle_collection,
                             timestamp_database, timestamp_collection,
                             x_start, x_end, framerate=25)

    viz.visualize(frames=500, verbose=True, save=False)
