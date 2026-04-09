"""
统计看板模块。

提供实时检测统计功能：
- 今日检测数、良品数、不良品数、良率
- 班次统计
- 缺陷分布统计
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class DailyStatistics:
    """每日统计数据。"""

    date: str  # YYYY-MM-DD
    total_count: int = 0
    pass_count: int = 0
    fail_count: int = 0
    total_defects: int = 0
    # 各类缺陷数量
    short_count: int = 0
    open_circuit_count: int = 0
    missing_hole_count: int = 0
    spur_count: int = 0
    mouse_bite_count: int = 0
    spurious_copper_count: int = 0

    @property
    def pass_rate(self) -> float:
        """合格率。"""
        if self.total_count == 0:
            return 100.0
        return (self.pass_count / self.total_count) * 100

    @property
    def fail_rate(self) -> float:
        """不良率。"""
        if self.total_count == 0:
            return 0.0
        return (self.fail_count / self.total_count) * 100

    @property
    def average_defects(self) -> float:
        """平均每片缺陷数。"""
        if self.fail_count == 0:
            return 0.0
        return self.total_defects / self.fail_count


@dataclass
class ShiftStatistics:
    """班次统计数据。"""

    shift_name: str  # 日班/夜班
    start_time: str  # HH:MM
    end_time: str  # HH:MM
    total_count: int = 0
    pass_count: int = 0
    fail_count: int = 0
    total_defects: int = 0

    @property
    def pass_rate(self) -> float:
        if self.total_count == 0:
            return 100.0
        return (self.pass_count / self.total_count) * 100


class StatisticsManager:
    """统计管理器，管理实时检测统计数据。"""

    def __init__(self) -> None:
        """初始化统计管理器。"""
        self._daily_stats: dict[str, DailyStatistics] = {}
        self._current_shift: Optional[ShiftStatistics] = None
        self._today = datetime.now().strftime("%Y-%m-%d")

    def record_pass(self) -> None:
        """记录一次通过。"""
        today_stats = self._get_or_create_today()
        today_stats.total_count += 1
        today_stats.pass_count += 1

        if self._current_shift:
            self._current_shift.total_count += 1
            self._current_shift.pass_count += 1

    def record_fail(self, defect_types: list[str]) -> None:
        """记录一次失败。

        Args:
            defect_types: 缺陷类型列表
        """
        today_stats = self._get_or_create_today()
        today_stats.total_count += 1
        today_stats.fail_count += 1
        today_stats.total_defects += len(defect_types)

        # 统计各类缺陷
        for dt in defect_types:
            if dt == "short":
                today_stats.short_count += 1
            elif dt == "open_circuit":
                today_stats.open_circuit_count += 1
            elif dt == "missing_hole":
                today_stats.missing_hole_count += 1
            elif dt == "spur":
                today_stats.spur_count += 1
            elif dt == "mouse_bite":
                today_stats.mouse_bite_count += 1
            elif dt == "spurious_copper":
                today_stats.spurious_copper_count += 1

        # 更新班次统计
        if self._current_shift:
            self._current_shift.total_count += 1
            self._current_shift.fail_count += 1
            self._current_shift.total_defects += len(defect_types)

    def _get_or_create_today(self) -> DailyStatistics:
        """获取或创建今日统计。"""
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self._daily_stats:
            self._daily_stats[today] = DailyStatistics(date=today)
            self._today = today
        return self._daily_stats[today]

    def set_shift(self, shift_name: str, start_time: str, end_time: str) -> None:
        """设置当前班次。

        Args:
            shift_name: 班次名称
            start_time: 开始时间
            end_time: 结束时间
        """
        self._current_shift = ShiftStatistics(
            shift_name=shift_name,
            start_time=start_time,
            end_time=end_time,
        )

    def get_today_stats(self) -> DailyStatistics:
        """获取今日统计。"""
        return self._get_or_create_today()

    def get_shift_stats(self) -> Optional[ShiftStatistics]:
        """获取当前班次统计。"""
        return self._current_shift

    def reset_today(self) -> None:
        """重置今日统计。"""
        today = datetime.now().strftime("%Y-%m-%d")
        self._daily_stats[today] = DailyStatistics(date=today)

    def reset_shift(self) -> None:
        """重置班次统计。"""
        if self._current_shift:
            self._current_shift = ShiftStatistics(
                shift_name=self._current_shift.shift_name,
                start_time=self._current_shift.start_time,
                end_time=self._current_shift.end_time,
            )
