# i24-overhead-visualizer

Overhead visualizer library for i24 motion. 

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

![demo](https://user-images.githubusercontent.com/58854510/172712278-d5912ce8-c8ef-4b0b-a8d4-6143cb282995.gif)
