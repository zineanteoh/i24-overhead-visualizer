#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 22 10:22:38 2022

@author: yanbing_wang

"""

from i24_database_api.db_reader import DBReader
# from i24_configparse import parse_cfg
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os
import matplotlib.animation as animation
import matplotlib.ticker as mticker
from datetime import datetime
from i24_logger.log_writer import logger, catch_critical
import queue
import mplcursors
from collections import OrderedDict
import json
import sys

 
class LRUCache:
    """
    A least-recently-used cache with integer capacity
    To roll out of the cache for vehicle color and dimensions
    get(): return the key-value in cache if exists, otherwise return -1
    put(): (no update) 
    """
    def __init__(self, capacity: int):
        self.cache = OrderedDict()
        self.capacity = capacity
 
    def get(self, key: int) -> int:
        if key not in self.cache:
            return -1
        else:
            self.cache.move_to_end(key)
            return self.cache[key]
 
    def put(self, key: int, value: int) -> None:
        if key not in self.cache: # do not update with new value
            self.cache[key] = value
        self.cache.move_to_end(key)
        if len(self.cache) > self.capacity:
            self.cache.popitem(last = False)
            
            
            
            
class OverheadCompare():
    """
    compare the overhead views of two collecctions
    """
    
    def __init__(self, config, vehicle_database = None,
                 timestamp_database = None, collection1 = None, collection2 = None,
                 framerate = 25, x_min = 0, x_max = 1500, duration = 60):
        """
        Initializes a Plotter object
        
        Parameters
        ----------
        config : object or dictionary for database access
        vehicle_database: database name for vehicle ID indexed collection
        vehicle_colleciton: collection name for vehicle ID indexed collection
        timestamp_database: database name for time-indexed documents
        timestamp_collection1 and 2: collection name for time-indexed documents
        framerate: (FPS) rate to query timestamps and to advance the animation
        x_min/x_max: (feet) roadway range for overhead view
        duration: (sec) duration for animation
        """
        
        self.dbr1 = DBReader(config, host = config["host"], username = config["username"], password = config["password"], port = config["port"], database_name = timestamp_database, collection_name=collection1)
        self.dbr2 = DBReader(config, host = config["host"], username = config["username"], password = config["password"], port = config["port"], database_name = timestamp_database, collection_name=collection2)   
        # corresponding vehicle ID collection
        self.veh1 = DBReader(config, host = config["host"], username = config["username"], password = config["password"], port = config["port"], database_name = vehicle_database, collection_name=collection1)
        self.veh2 = DBReader(config, host = config["host"], username = config["username"], password = config["password"], port = config["port"], database_name = vehicle_database, collection_name=collection2)
        
        self.dbr1.create_index("timestamp")
        self.dbr2.create_index("timestamp")
        
        # get plotting ranges
        t_min = max(self.dbr1.get_min("timestamp"),self.dbr2.get_min("timestamp"))
        if duration: t_max = t_min+duration 
        else: t_max = min(self.dbr1.get_max("timestamp"),self.dbr2.get_max("timestamp"))
        
        self.x_start = x_min
        self.x_end = x_max
        self.t_min = t_min
        self.t_max = t_max
        
        # Initialize animation
        self.anim = None
        # TODO: framerate for timestmap
        self.framerate = framerate if framerate else 25
        
        self.lanes = [i*12 for i in range(-1,12)]   
        self.lane_name = [ "EBRS", "EB4", "EB3", "EB2", "EB1", "EBLS", "WBLS", "WB1", "WB2", "WB3", "WB4", "WBRS"]
        self.lane_idx = [i for i in range(12)]
        self.lane_ax = [[1,5],[1,4],[1,3],[1,2],[1,1],[1,0],[0,0],[0,1],[0,2],[0,3],[0,4],[0,5]]
        
        self.annot_queue = queue.Queue()
        self.cursor = None
        

    
        
    @catch_critical(errors = (Exception))
    def animate(self, save = False):
        """
        Advance time window by delta second, update left and right pointer, and cache
        """     
        # set figures: two rows. Top: dbr1 (ax_o), bottom: dbr2 (ax_o2). 4 lanes in each direction
        fig, axs = plt.subplots(2,6,figsize=(20,8))
             
        # TODO: make size parameters
        cache_vehicle = LRUCache(100)
        cache_colors = LRUCache(100)
        
        def on_xlims_change(event_ax):
            # print("updated xlims: ", event_ax.get_xlim())
            new_xlim = event_ax.get_xlim()
            # ax1.set(xlim=new_xlim)
            self.x_start = new_xlim[0]
            self.x_end = new_xlim[1]
            
        # OVERHEAD VIEW SETUP
        ax_o = plt.subplot(211) # overhead view
        ax_o2 = plt.subplot(212) # overhead view
        ax_o.set_title(self.dbr1.collection._Collection__name)
        ax_o2.set_title(self.dbr2.collection._Collection__name)
        
        for ax in [ax_o, ax_o2]:
            ax.set_aspect('equal', 'box')
            ax.set(ylim=[self.lanes[0], self.lanes[-1]])
            ax.set(xlim=[self.x_start, self.x_end])
            ax.set_ylabel("EB    WB")
            ax.set_xlabel("Distance in feet")
            ax.callbacks.connect('xlim_changed', on_xlims_change)

        
        self.time_cursor = self.dbr1.get_range("timestamp", self.t_min, self.t_max)
        plt.gcf().autofmt_xdate()
        
        
        @catch_critical(errors = (Exception))
        def init():
            for ax in [ax_o, ax_o2]:
                # plot lanes on overhead view
                for i in range(-1, 12):
                    if i in (-1, 5, 11):
                        ax.axhline(y=i*12, linewidth=0.5, color='k')
                    else:
                        ax.axhline(y=i*12, linewidth=0.1, color='k')
            
            return axs,
              

        @catch_critical(errors = (Exception))
        def update_cache(frame_text):
            """
            Returns
            -------
            delta : increment in time (sec)
                DESCRIPTION.
            """
            # Stop criteria
            doc1 = self.time_cursor.next()
            curr_time = doc1["timestamp"]
            doc2 = self.dbr2.find_one("timestamp", curr_time)
            if not doc2:
                # return axs
                doc2 = {"id": [], "position":[], "dimensions":[]}

            if curr_time >= self.t_max:
                print("Reach the end of time. Exit.")
                raise StopIteration
                
            time_text = datetime.utcfromtimestamp(int(curr_time)).strftime('%m/%d/%Y, %H:%M:%S')
            
            plt.suptitle(time_text, fontsize = 20)
            
            # remove all car_boxes and verticle lines
            for box in list(ax_o.patches) + list(ax_o2.patches):
                box.set_visible(False)
                box.remove()
            
            while not self.annot_queue.empty():
                self.annot_queue.get(block=False).remove()
                
            # Add vehicle ids in cache_colors             
            for veh_id in doc1['id'] + doc2['id']:
                cache_colors.put(veh_id, np.random.rand(3,))
                
            # query for vehicle dimensions if not in doc
            if "dimensions" not in doc1:
                # find in the corresponding vehicle-id database
                traj_cursor1 = self.veh1.collection.find({"_id": {"$in": doc1["id"]} }, 
                                                                {"width":1, "length":1, "coarse_vehicle_class": 1})
                # add vehicle dimension to cache
                for index, traj in enumerate(traj_cursor1):
                    # print("index: {} is {}".format(index, traj))
                    # { ObjectId('...') : [length, width, coarse_vehicle_class] }
                    cache_vehicle.put(traj["_id"], [traj["length"], traj["width"], traj["coarse_vehicle_class"]])
            else:
                for index, veh_id in enumerate(doc1['id']):
                    cache_vehicle.put(veh_id, doc1['dimensions'][index])     
                
            if "dimensions" not in doc2:
                traj_cursor2 = self.veh2.collection.find({"_id": {"$in": doc2["id"]} }, 
                                                                {"width":1, "length":1, "coarse_vehicle_class": 1}) 
                # add vehicle dimension to cache
                for index, traj in enumerate(traj_cursor2):
                    cache_vehicle.put(traj["_id"], [traj["length"], traj["width"], traj["coarse_vehicle_class"]])
            else:
                for index, veh_id in enumerate(doc2['id']):
                    cache_vehicle.put(veh_id, doc2['dimensions'][index])          
                    
            # plot vehicles
            for index in range(len(doc1["position"])):
                car_x_pos = doc1["position"][index][0]
                car_y_pos = doc1["position"][index][1]

                car_length, car_width, _ = cache_vehicle.get(doc1["id"][index])

                box = patches.Rectangle((car_x_pos, car_y_pos),
                                        car_length, car_width, 
                                        color=cache_colors.get(doc1["id"][index]),
                                        label=doc1["id"][index])
                ax_o.add_patch(box)   
                # add annotation
                annot = ax_o.annotate(doc1['_id'], xy=(car_x_pos,car_y_pos))
                annot.set_visible(False)
                self.annot_queue.put(annot)
                
            # plot vehicles
            for index in range(len(doc2["position"])):
                car_x_pos = doc2["position"][index][0]
                car_y_pos = doc2["position"][index][1]

                car_length, car_width, _ = cache_vehicle.get(doc2["id"][index])

                box = patches.Rectangle((car_x_pos, car_y_pos),
                                        car_length, car_width, 
                                        color=cache_colors.get(doc2["id"][index]),
                                        label=doc2["id"][index])
                ax_o2.add_patch(box)   
                # add annotation
                annot = ax_o2.annotate(doc2['_id'], xy=(car_x_pos,car_y_pos))
                annot.set_visible(False)
                self.annot_queue.put(annot)
            

            return axs
        
        
        frame_text = None
        self.anim = animation.FuncAnimation(fig, func=update_cache,
                                            init_func= init,
                                            frames=int(self.t_max-self.t_min)*self.framerate,
                                            repeat=False,
                                            interval=1/self.framerate * 1000, # in ms
                                            fargs=( frame_text), # specify time increment in sec to update query
                                            blit=False)
        self.paused = False
        fig.canvas.mpl_connect('key_press_event', self.toggle_pause)

        
        if save:
            file_name = "anim_overhead_compare_" + self.dbr1.collection._Collection__name + "_vs_" + self.dbr2.collection._Collection__name
            self.anim.save('{}.mp4'.format(file_name), writer='ffmpeg', fps=self.framerate)
            # self.anim.save('{}.gif'.format(file_name), writer='imagemagick', fps=self.framerate)
        else:
            fig.tight_layout()
            plt.show()
        print("complete")
        


    
    def toggle_pause(self, event):
        """
        press spacebar to pause/resume animation
        """
        printed = set()
        if event.key == " ":
            if self.paused:
                self.anim.resume()
                print("Animation Resumed")
                self.cursor.remove()
            else:
                self.anim.pause()
                print("Animation Paused")
                printed = set()
                self.cursor = mplcursors.cursor(hover=True)
                def on_add(sel):
                    if self.paused and (sel.artist.get_label()[0] != "_"):
                        label = sel.artist.get_label()
                        if label not in printed:
                            print(label)
                            printed.add(label)
                        sel.annotation.set_text(sel.artist.get_label())
                # connect mouse event to hover for car ID
                self.cursor.connect("add", lambda sel: on_add(sel))
            self.paused = not self.paused

    
    
if True and __name__=="__main__":
    

    with open('config.json') as f:
        parameters = json.load(f)
    
    vehicle_database = "trajectories"
    timestamp_database = "transformed"
    collection1 = "groundtruth_scene_1"
    collection2 = "21_07_2022_gt1_alpha"
    framerate = 25
    x_min = 0
    x_max = 1500
    duration = None
    
    # batch_5_07072022, batch_reconciled, 
    p = OverheadCompare(parameters, vehicle_database = vehicle_database, timestamp_database=timestamp_database, 
                collection1=collection1, collection2=collection2,
                framerate = framerate, x_min = x_min, x_max=x_max, duration=duration)
    p.animate(save=False)
    
    