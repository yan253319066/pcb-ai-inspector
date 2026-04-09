# Utilities

**Parent:** `./AGENTS.md`

## OVERVIEW

Device detection, logging configuration, industrial camera support, and shared utilities.

## WHERE TO LOOK

| Task | File | Description |
|------|------|-------------|
| GPU/CPU detection | `device.py` | torch + onnxruntime provider detection |
| Logging setup | `logging_config.py` | loguru configuration |
| Industrial camera | `industrial_camera.py` | USB/GigE camera abstraction |
| Camera capture | `camera_capture.py` | Camera frame capture utilities |
| Multi-scale detection | `multi_scale.py` | Multi-scale image processing |
| Image tiling | `image_tiler.py` | Large image splitting |

## CAMERA ABSTRACTION

```python
from .industrial_camera import create_camera, CameraConfig, TriggerMode, discover_cameras

# Create camera
config = CameraConfig(
    camera_type="usb",  # or "gige"
    camera_id="0",
    resolution=(1920, 1080),
    exposure=10000,
    gain=0.0,
)
camera = create_camera(config)
camera.connect()
camera.start_streaming()
frame = camera.get_frame()
```

## CONVENTIONS

- Device detection: `torch.cuda.is_available()` + `onnxruntime.get_available_providers()`
- Logging via `loguru`
- Camera abstraction for industrial scenarios

## NOTES

- Supports USB webcams and GigE industrial cameras
- Camera config includes resolution, exposure, gain, trigger mode
- Frame capture returns numpy arrays for detection pipeline
