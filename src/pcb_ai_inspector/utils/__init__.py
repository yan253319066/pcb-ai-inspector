"""
PCB AI Inspector 工具模块。

包含设备检测、日志配置和其他辅助功能。
"""

from .device import (
    get_device_info,
    get_device,
    get_device_name,
    DeviceInfo,
    print_device_info,
    format_memory,
)
from .logging_config import (
    setup_logging,
    get_logger,
    OperationLogger,
    init_logging,
)

__all__ = [
    # 设备
    "get_device_info",
    "get_device",
    "get_device_name",
    "DeviceInfo",
    "print_device_info",
    "format_memory",
    # 日志
    "setup_logging",
    "get_logger",
    "OperationLogger",
    "init_logging",
]
