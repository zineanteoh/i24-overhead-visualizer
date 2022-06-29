#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 16 14:11:40 2022

Test mongodb queries

@author: teohz
"""

from i24_database_api.db_reader import DBReader
import pymongo
import json
import os
import pandas as pd
import time # measure speed

def resample(car):
    # resample timestamps to 30hz, leave nans for missing data
    '''
    Original Author: Yanbing Wang
    Repository: I24-trajectory-generation/utils/reconciliation_module.py
    Modified by Zi Teoh to resample when car object has no positions
    
    resample the original time-series to uniformly sampled time series in 30Hz
    car: document
    '''
    
    if "x_position" in car and "y_position" in car:
        has_position = True

    # Select time series only
    try:
        if has_position:
            time_series_field = ["timestamp", "x_position", "y_position"]
        else:
            time_series_field = ["timestamp"]
        data = {key: car[key] for key in time_series_field}
        
        # Read to dataframe and resample
        df = pd.DataFrame(data, columns=data.keys()) 
        print(df)
        index = pd.to_timedelta(df["timestamp"], unit='s')
        print(df)
        df = df.set_index(index)
        print(df)
        df = df.drop(columns = "timestamp")
        print(df)
        df = df.resample('0.033333333S').mean() # close to 30Hz
        print(df)
        df.index = df.index.values.astype('datetime64[ns]').astype('int64')*1e-9
    
        if has_position:
            car['x_position'] = df['x_position'].values
            car['y_position'] = df['y_position'].values
        car['timestamp'] = df.index.values
        print(df)
    except Exception as e:
        print("Exception caught", e)
    return car

def pipeline_add_start_end_index(start_time, end_time):
    """
    Returns a pymongo aggregate stage that adds start_index and end_index to
    each document.
    
    start_index maintains the index of the first item in timestamp array 
    that is greater than or equal to start_time
    
    end_index maintains the index of the first item in timestamp array
    that is less than or equal to end_time
    
    if no such element exists in the timestamp array, then index = -1
    """
    return { 
        "$addFields": {
            "start_index": {
              "$let": {
                "vars": {
                  "matched": {
                    "$arrayElemAt": [
                      {
                        "$filter": {
                          "input": {
                            "$zip": {
                              "inputs": [
                                  "$timestamp", { "$range": [0, { "$size": "$timestamp"}]}
                              ]
                            }
                          },
                          "cond": {
                            "$gte": [
                                {"$arrayElemAt": ["$$this", 0]},
                                start_time
                            ]
                          }
                        }
                      },
                      0
                    ]
                  }
                },
                "in": {
                  "$arrayElemAt": [
                    {
                      "$ifNull": [
                        "$$matched",
                        [
                          0,
                          -1
                        ]
                      ]
                    },
                    1
                  ]
                }
              }
            },
            "end_index": {
              "$let": {
                "vars": {
                  "matched": {
                    "$arrayElemAt": [
                      {
                        "$filter": {
                          "input": {
                            "$zip": {
                              "inputs": [
                                  "$timestamp", { "$range": [0, { "$size": "$timestamp"}]}
                              ]
                            }
                          },
                          "cond": {
                            "$lte": [
                                {"$arrayElemAt": ["$$this", 0]},
                                end_time
                            ]
                          }
                        }
                      },
                      -1
                    ]
                  }
                },
                "in": {
                  "$arrayElemAt": [
                    {
                      "$ifNull": [
                        "$$matched",
                        [
                          0,
                          -1
                        ]
                      ]
                    },
                    1
                  ]
                }
              }
            }
          }
        }

def pipeline_filter_by_matching():
    """
    Returns a pymongo aggregate stage that filters out documents and only
    keep those whose start and end index are not -1 
    """
    return {
        "$match": {
            "$and": [
                { "start_index" : { "$ne" : -1 } },
                { "end_index" : { "$ne" : -1 } }
            ]
        }
    }

def pipeline_project_and_slice():
    """
    Returns a pymongo aggregate stage that projects the documents to only 
    include necessary fields while slicing the arrays based on start and end
    indices.
    """
    return {
        "$project": {
            "coarse_vehicle_class": 1,
            "timestamp": { "$slice": ["$timestamp", 
                                      {"$subtract" : ["$start_index", 1]}, 
                                      {"$add" : [ {"$subtract" : ["$end_index", "$start_index"]} , 1]} ] },
            "x_position": { "$slice": ["$x_position", 
                                       {"$subtract" : ["$start_index", 1]},
                                       {"$add" : [ {"$subtract" : ["$end_index", "$start_index"]} , 1]} ] },
            "y_position": { "$slice": ["$y_position", 
                                       {"$subtract" : ["$start_index", 1]},
                                       {"$add" : [ {"$subtract" : ["$end_index", "$start_index"]} , 1]} ] },
            "first_timestamp": 1,
            "last_timestamp": 1,
            "length": 1,
            "width": 1,
            "height": 1,
            "direction": 1,
            "start_index": 1,
            "end_index": 1,
        }
    }

if __name__=="__main__":
    # load config
    os.chdir("/isis/home/teohz/Desktop/videowall")
    with open('config.json') as f:
        config = json.load(f)
    
    # initialize DBReader
    dbr = DBReader(host=config["host"], 
                   port=config["port"], 
                   username=config["username"], 
                   password=config["password"], 
                   database_name=config["database_name"], 
                   collection_name=config["collection_name"])
    
    num_of_doc = 100
    
    t_1 = time.time()
    list(dbr.collection.find({}).limit(num_of_doc))
    t_2 = time.time()
    print("time taken: {}".format(t_2 - t_1))
    
    t_1 = time.time()
    first_n_doc = dbr.collection.find({}).limit(num_of_doc)
    for doc in first_n_doc:
        print(doc["coarse_vehicle_class"])
    t_2 = time.time()
    print("time taken: {}".format(t_2 - t_1))
    # print(first_5_doc[0])
    
    # three stages to querying trajectories
    # 1. add start_index and end_index to the documents
    # 2. filter to keep only documents with valid start_index & end_index
    # 3. project and slice document to get the necessary information
    # pipeline = [pipeline_add_start_end_index(1.01, 10.01),
    #             pipeline_filter_by_matching(),
    #             pipeline_project_and_slice()]
    
    # tt1 = time.time()
    # traj_cursor = dbr.collection.aggregate(pipeline)
    # count = 0
    
    # for car_data in traj_cursor:
    #     start_index = car_data["start_index"]
    #     end_index = car_data["end_index"]
        
    #     count += 1
    # print("index: [{}, {}]".format(start_index, end_index))
    # print("length of timestamps: {}".format(len(car_data["timestamp"])))
    # print("timestamp: {}...".format(car_data["timestamp"][0:3]))
    
    # tt2 = time.time()
    # print("time taken: {}".format(tt2 - tt1))
    # print(count)