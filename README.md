# i24-overhead-visualizer

Overhead and time-space visualizer library for i24 motion. 

Key:
- Press [spacebar] to pause/resume animation

## Example
### run ```overhead_compare.py``` to visualize ground truth, raw and reconciled collection together. GT is plotted in light grey.
```python
parameters = {
  "host": "<mongodb-host>",
  "port": 27017,
  "username": "<mongodb-username>",
  "password": "<mongodb-password>"
}
gt = "groundtruth_scene_1"
raw = "sibilant_zebra--RAW_GT1" # collection name is the same in both databases
rec = "sibilant_zebra--RAW_GT1__lionizes"

framerate = 25
x_min = 0
x_max = 1500
offset = 0
duration = None

p = OverheadCompare(parameters, 
            collections = [gt, raw, rec],
            framerate = framerate, x_min = x_min, x_max=x_max, offset = offset, duration=duration)
p.animate(save=False, extra="")
```

Results: 

![anim_batch_reconciled_timespace_overhead](https://user-images.githubusercontent.com/30248823/180271610-6baf4307-e4a1-4cb5-ae86-3df0d31e3319.gif)
