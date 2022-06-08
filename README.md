# i24-overhead-visualizer

Overhead visualizer library for i24 motion. 

## Example

```python
config = {
  "host": "<mongodb-host>",
  "port": 27017,
  "username": "<mongodb-username>",
  "password": "<mongodb-password>",
  "database_name": "trajectories",
  "collection_name": "ground_truth_two",
}

viz = OverheadVisualizer(config)
viz.visualize_road_segment(frames=100, start=14500, end=15000, save=True)
```

Results: 

![demo](https://user-images.githubusercontent.com/58854510/172712278-d5912ce8-c8ef-4b0b-a8d4-6143cb282995.gif)
