"""
PCB AI Inspector 核心模块。

包含缺陷类型定义、授权管理、历史记录和设置管理。
"""

from .defect_types import (
    DefectType,
    DefectDefinition,
    DEFECT_DEFINITIONS,
    DEFECT_LABELS,
    DEFECT_COLORS,
    DEFECT_COLORS_LIGHT,
    MODEL_CLASS_MAPPING,
)
from .activation import (
    ActivationManager,
    ActivationInfo,
    LicenseState,
    HardwareFingerprint,
    LicenseKey,
    check_activation,
)
from .history import (
    HistoryManager,
    DetectionRecord,
    HistoryStatistics,
    get_history_manager,
)
from .settings import (
    SettingsManager,
    ApplicationSettings,
    DetectionSettings,
    DisplaySettings,
    ReportSettings,
    PerformanceSettings,
    DEFAULT_MODEL_PATH,
    get_settings_manager,
)

__all__ = [
    # 缺陷类型
    "DefectType",
    "DefectDefinition",
    "DEFECT_DEFINITIONS",
    "DEFECT_LABELS",
    "DEFECT_COLORS",
    "DEFECT_COLORS_LIGHT",
    # 授权管理
    "ActivationManager",
    "ActivationInfo",
    "LicenseState",
    "HardwareFingerprint",
    "LicenseKey",
    "check_activation",
    # 历史记录
    "HistoryManager",
    "DetectionRecord",
    "HistoryStatistics",
    "get_history_manager",
    # 设置管理
    "SettingsManager",
    "ApplicationSettings",
    "DetectionSettings",
    "DisplaySettings",
    "ReportSettings",
    "PerformanceSettings",
    "DEFAULT_MODEL_PATH",
    "get_settings_manager",
]
