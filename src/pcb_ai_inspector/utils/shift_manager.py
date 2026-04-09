"""
班次管理器模块。

提供班次自动切换功能：
- 预设班次日班/夜班
- 自定义班次配置
- 基于时间的自动切换
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional


@dataclass
class ShiftConfig:
    """班次配置。"""

    name: str  # 班次名称
    start_time: str  # 开始时间 HH:MM
    end_time: str  # 结束时间 HH:MM
    color: str = "#3B82F6"  # 界面显示颜色


# 预设班次配置
DEFAULT_SHIFTS: dict[str, ShiftConfig] = {
    "day": ShiftConfig(
        name="日班",
        start_time="08:00",
        end_time="20:00",
        color="#22C55E",
    ),
    "night": ShiftConfig(
        name="夜班",
        start_time="20:00",
        end_time="08:00",
        color="#8B5CF6",
    ),
    "morning": ShiftConfig(
        name="早班",
        start_time="06:00",
        end_time="14:00",
        color="#F59E0B",
    ),
    "afternoon": ShiftConfig(
        name="中班",
        start_time="14:00",
        end_time="22:00",
        color="#EF4444",
    ),
    "evening": ShiftConfig(
        name="晚班",
        start_time="22:00",
        end_time="06:00",
        color="#6366F1",
    ),
}


class ShiftManager:
    """班次管理器，支持自动和手动班次切换。"""

    def __init__(self) -> None:
        """初始化班次管理器。"""
        self._current_shift: Optional[ShiftConfig] = None
        self._custom_shifts: dict[str, ShiftConfig] = {}
        self._auto_shift_enabled: bool = True

        # 默认使用日班
        self._set_shift(DEFAULT_SHIFTS["day"])

    def enable_auto_shift(self, enabled: bool) -> None:
        """启用/禁用自动班次切换。

        Args:
            enabled: 是否启用自动切换
        """
        self._auto_shift_enabled = enabled

    @property
    def is_auto_shift_enabled(self) -> bool:
        """是否启用自动班次切换。"""
        return self._auto_shift_enabled

    def add_custom_shift(self, shift: ShiftConfig) -> None:
        """添加自定义班次。

        Args:
            shift: 班次配置
        """
        self._custom_shifts[shift.name] = shift

    def get_available_shifts(self) -> list[ShiftConfig]:
        """获取所有可用班次。

        Returns:
            班次配置列表
        """
        shifts = list(DEFAULT_SHIFTS.values())
        shifts.extend(self._custom_shifts.values())
        return shifts

    def get_shift_by_name(self, name: str) -> Optional[ShiftConfig]:
        """根据名称获取班次配置。

        Args:
            name: 班次名称

        Returns:
            班次配置，如果不存在返回 None
        """
        return DEFAULT_SHIFTS.get(name) or self._custom_shifts.get(name)

    def set_shift(self, shift: ShiftConfig) -> None:
        """手动设置当前班次。

        Args:
            shift: 班次配置
        """
        self._current_shift = shift

    def set_shift_by_name(self, name: str) -> bool:
        """根据名称设置班次。

        Args:
            name: 班次名称

        Returns:
            是否设置成功
        """
        shift = self.get_shift_by_name(name)
        if shift:
            self._set_shift(shift)
            return True
        return False

    def _set_shift(self, shift: ShiftConfig) -> None:
        """内部设置班次。"""
        self._current_shift = shift

    def check_and_switch_shift(self) -> Optional[ShiftConfig]:
        """检查是否需要切换班次（自动模式下）。

        如果启用了自动切换，根据当前时间判断是否需要切换班次。

        Returns:
            如果切换了班次返回新的班次配置，否则返回 None
        """
        if not self._auto_shift_enabled or self._current_shift is None:
            return None

        now = datetime.now()
        current_time = now.time()

        # 检查当前班次
        start = self._parse_time(self._current_shift.start_time)
        end = self._parse_time(self._current_shift.end_time)

        # 处理跨天的情况（如 20:00 - 08:00）
        if start > end:
            # 夜班模式：20:00 - 08:00
            if current_time >= start or current_time < end:
                return None  # 仍在当前班次
        else:
            # 普通模式：08:00 - 20:00
            if start <= current_time < end:
                return None  # 仍在当前班次

        # 需要切换班次
        new_shift = self._find_next_shift(now)
        if new_shift and new_shift.name != self._current_shift.name:
            self._set_shift(new_shift)
            return new_shift

        return None

    def _find_next_shift(self, now: datetime) -> Optional[ShiftConfig]:
        """查找下一个应该切换到的班次。

        Args:
            now: 当前时间

        Returns:
            下一个班次配置
        """
        all_shifts = self.get_available_shifts()
        if not all_shifts:
            return None

        # 按开始时间排序
        sorted_shifts = sorted(all_shifts, key=lambda s: self._parse_time(s.start_time))

        current_time = now.time()
        for shift in sorted_shifts:
            start = self._parse_time(shift.start_time)
            if start > current_time:
                return shift

        # 如果没有找到，返回第一个班次
        return sorted_shifts[0] if sorted_shifts else None

    def _parse_time(self, time_str: str) -> time:
        """解析时间字符串。

        Args:
            time_str: 时间字符串 HH:MM

        Returns:
            time 对象
        """
        try:
            return datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            return time(0, 0)

    @property
    def current_shift(self) -> Optional[ShiftConfig]:
        """获取当前班次。"""
        return self._current_shift

    @property
    def current_shift_name(self) -> str:
        """获取当前班次名称。"""
        if self._current_shift:
            return self._current_shift.name
        return ""

    def should_reset_shift(self) -> bool:
        """检查是否需要重置班次（每天首次使用）。

        Returns:
            是否需要重置
        """
        # 这里可以添加逻辑：比如检查是否是每天第一次使用
        # 目前简单实现：每次初始化都会重置
        return False


def create_shift_manager() -> ShiftManager:
    """创建班次管理器实例。"""
    return ShiftManager()
