"""
PCB AI Inspector 模型模块。

包含 YOLO 检测器及模型管理。
"""

from .detector import (
    YOLODetector,
    DetectionResult,
    ImageDetectionResult,
    create_detector,
)

__all__ = [
    "YOLODetector",
    "DetectionResult",
    "ImageDetectionResult",
    "create_detector",
]
