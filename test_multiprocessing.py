#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun  9 13:17:18 2022

@author: teohz
"""

import multiprocessing
import time

class Process(multiprocessing.Process):
    def __init__(self, id):
        super(Process, self).__init__()
        self.id = id
        
    def run(self):
        time.sleep(1)
        print("I am the proces with id: {}".format(self.id))

def square(x):
    return x * x

if __name__ == '__main__':
    pool = multiprocessing.Pool(processes=4)
    inputs = range(100)
    outputs_async = pool.map_async(square, inputs)
    outputs = outputs_async.get()
    print("Output: {}".format(outputs))