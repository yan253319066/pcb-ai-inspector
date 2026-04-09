# AI Model Integration

**Parent:** `./AGENTS.md`

## OVERVIEW

YOLO detector integration with ONNX runtime support.

## WHERE TO LOOK

| Task | File |
|------|------|
| Main detector | `detector.py` |

## CONVENTIONS

- Load model via `YOLO()` or ONNX runtime
- Device auto-detection in `utils/device.py`
- TYPE_CHECKING guard for torch/cv2 imports

## ANTI-PATTERNS

- ❌ Direct `torch` imports in type hints → use `TYPE_CHECKING`
- ❌ Hardcoded model paths → use `settings.py`

## NOTES

- Supports .pt (PyTorch) and .onnx formats
- Inference via `model.predict()`