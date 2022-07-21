# i24-overhead-visualizer

Overhead and time-space visualizer library for i24 motion. 

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
vehicle_database = "trajectories"
vehicle_collection = "batch_reconciled"
        
# Collection with timestamp index
timestamp_database = "transformed"
timestamp_collection = "batch_reconciled_transformed"

window_size = 10
framerate = 25
x_min = 0
x_max = 2000
duration = 7

p = Plotter(parameters, vehicle_database=vehicle_database, vehicle_collection=vehicle_collection,
            timestamp_database=timestamp_database, timestamp_collection=timestamp_collection,
            window_size = window_size, framerate = framerate, x_min = x_min, x_max=x_max, duration=duration)
p.animate(save=False)
```

Results: 

![anim_batch_reconciled_timespace_overhead](https://user-images.githubusercontent.com/30248823/180271610-6baf4307-e4a1-4cb5-ae86-3df0d31e3319.gif)
