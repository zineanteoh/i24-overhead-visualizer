# i24-overhead-visualizer

Overhead visualizer library for i24 motion. 

## Example

```python
config = {
  "host": "<mongodb-host>",
  "port": 27017,
  "username": "<mongodb-username>",
  "password": "<mongodb-password>",
  "timestamp_database": "lisatest",
  "timestamp_collection": "transformed_trajectories",
  "traj_database": "lisatest",
  "traj_collection": "read_v1"
}

viz = OverheadVisualizer(config)
viz.visualize(frames=1000, save=True)
```

Results: 

![demo](https://user-images.githubusercontent.com/58854510/172712278-d5912ce8-c8ef-4b0b-a8d4-6143cb282995.gif)
