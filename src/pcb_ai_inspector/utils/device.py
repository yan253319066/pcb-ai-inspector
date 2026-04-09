"""
PCB AI Inspector 设备管理模块。

本模块提供 GPU/CPU 兼容性的自动设备检测和管理。
"""

from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass
class DeviceInfo:
    """计算设备信息。"""

    device: torch.device
    device_type: str  # "cuda" 或 "cpu"
    device_name: str | None
    memory_total: int | None  # 字节
    memory_available: int | None  # 字节
    cuda_available: bool
    device_count: int


def get_device_info() -> DeviceInfo:
    """获取可用计算设备的信息。

    Returns:
        包含 GPU/CPU 可用性详情的 DeviceInfo
    """
    cuda_available = torch.cuda.is_available()

    if cuda_available:
        device = torch.device("cuda")
        device_name = torch.cuda.get_device_name(0)
        memory_total = torch.cuda.get_device_properties(0).total_memory
        # 获取当前内存使用量
        memory_available = memory_total - torch.cuda.memory_allocated(0)
        device_count = torch.cuda.device_count()
    else:
        device = torch.device("cpu")
        device_name = None
        memory_total = None
        memory_available = None
        device_count = 0

    return DeviceInfo(
        device=device,
        device_type=device.type,
        device_name=device_name,
        memory_total=memory_total,
        memory_available=memory_available,
        cuda_available=cuda_available,
        device_count=device_count,
    )


def get_device() -> torch.device:
    """获取最佳可用设备（ GPU 可用则用 GPU，否则用 CPU）。

    Returns:
        torch.device: 要使用的计算设备
    """
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def get_device_name() -> str:
    """获取当前设备的人类可读名称。

    Returns:
        设备名称字符串
    """
    if torch.cuda.is_available():
        return torch.cuda.get_device_name(0)
    return "CPU"


def format_memory(bytes_value: int | None) -> str:
    """格式化内存大小为人类可读格式。

    Args:
        bytes_value: 以字节为单位的内存

    Returns:
        格式化后的字符串，如 "6.5 GB"
    """
    if bytes_value is None:
        return "N/A"

    gb = bytes_value / (1024**3)
    return f"{gb:.1f} GB"


def print_device_info() -> None:
    """将设备信息打印到控制台。"""
    info = get_device_info()

    print("=" * 50)
    print("设备信息")
    print("=" * 50)
    print(f"CUDA 可用: {info.cuda_available}")
    print(f"设备类型:   {info.device_type}")
    print(f"设备名称:   {info.device_name or 'N/A'}")
    print(f"设备数量:  {info.device_count}")

    if info.cuda_available:
        print(f"内存总量:    {format_memory(info.memory_total)}")
        print(f"可用内存: {format_memory(info.memory_available)}")

    print("=" * 50)


if __name__ == "__main__":
    print_device_info()
