"""
PCB AI Inspector - PCB 缺陷检测系统

一款使用 YOLO11 AI 模型检测 10 种 PCB 缺陷的桌面应用程序。
支持离线运行，自动检测 GPU/CPU。
"""

__version__ = "1.0.0"
__author__ = "PCB AI Inspector Team"

from .core.defect_types import (
    DefectType,
    DefectDefinition,
    DEFECT_DEFINITIONS,
    DEFECT_LABELS,
    DEFECT_COLORS,
    MODEL_CLASS_MAPPING,
)
from .core.activation import (
    ActivationManager,
    ActivationInfo,
    LicenseState,
    check_activation,
)
from .core.history import (
    HistoryManager,
    DetectionRecord,
    HistoryStatistics,
    get_history_manager,
)
from .core.settings import (
    SettingsManager,
    ApplicationSettings,
    DetectionSettings,
    DisplaySettings,
    ReportSettings,
    PerformanceSettings,
    get_settings_manager,
)
from .models.detector import YOLODetector, DetectionResult, ImageDetectionResult
from .utils.device import get_device_info, get_device, DeviceInfo
from .utils.logging_config import setup_logging, get_logger, OperationLogger

__all__ = [
    # 版本
    "__version__",
    # 核心模块 - 缺陷类型
    "DefectType",
    "DefectDefinition",
    "DEFECT_DEFINITIONS",
    "DEFECT_LABELS",
    "DEFECT_COLORS",
    "MODEL_CLASS_MAPPING",
    # 核心模块 - 授权
    "ActivationManager",
    "ActivationInfo",
    "LicenseState",
    "check_activation",
    # 核心模块 - 历史记录
    "HistoryManager",
    "DetectionRecord",
    "HistoryStatistics",
    "get_history_manager",
    # 核心模块 - 设置
    "SettingsManager",
    "ApplicationSettings",
    "DetectionSettings",
    "DisplaySettings",
    "ReportSettings",
    "PerformanceSettings",
    "get_settings_manager",
    # 模型
    "YOLODetector",
    "DetectionResult",
    "ImageDetectionResult",
    # 工具
    "get_device_info",
    "get_device",
    "DeviceInfo",
    "setup_logging",
    "get_logger",
    "OperationLogger",
]
