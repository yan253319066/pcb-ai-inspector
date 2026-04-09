"""
PCB AI Inspector UI 模块。

包含主窗口、图像查看器、缺陷覆盖层、设置对话框、历史记录对话框及其他 UI 组件。
"""

from .main_window import MainWindow
from .image_viewer import ImageViewer
from .defect_overlay import DetectionOverlay, DetectionResult
from .defect_list import DefectListWidget, StatisticsWidget
from .detection_pipeline import DetectionPipeline, DetectionMode
from .detection_result_handler import DetectionResultHandler
from .settings_dialog import SettingsDialog
from .history_dialog import HistoryDialog
from .manual_panel import ManualDetectionPanel
from .realtime_panel import RealtimeDetectionPanel
from .batch_handler import BatchDetectionHandler

__all__ = [
    "MainWindow",
    "ImageViewer",
    "DetectionOverlay",
    "DetectionResult",
    "DefectListWidget",
    "StatisticsWidget",
    "DetectionPipeline",
    "DetectionMode",
    "DetectionResultHandler",
    "SettingsDialog",
    "HistoryDialog",
    "ManualDetectionPanel",
    "RealtimeDetectionPanel",
    "BatchDetectionHandler",
]
