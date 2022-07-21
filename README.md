# i24-overhead-visualizer

Overhead visualizer library for i24 motion. 

Key:
- Press [spacebar] to pause/resume animation

## Example

```python
config = {
  "host": "<mongodb-host>",
  "port": 27017,
  "username": "<mongodb-username>",
  "password": "<mongodb-password>"
}

# Collection with vehicle ID index 
vehicle_database = "lisatest"
vehicle_collection = "tracking_v1_reconciled_l1"
        
# Collection with timestamp index
timestamp_database = "lisatest"
timestamp_collection = "tracking_v1_reconciled_l1_transformed"

viz = OverheadVisualizer(config, vehicle_database, vehicle_collection,
                        timestamp_database, timestamp_collection,
                        framerate=25)
viz.visualize(verbose=True)
```

Results: 

#![Demo](https://user-images.githubusercontent.com/58854510/177853829-d756915c-c928-4953-bd07-2fe2993bdb39.gif)
![anim_batch_reconciled_timespace_overhead](https://user-images.githubusercontent.com/30248823/180271610-6baf4307-e4a1-4cb5-ae86-3df0d31e3319.gif)
