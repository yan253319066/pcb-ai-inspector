"""
报警控制器模块。

提供声光报警功能：
- 声音报警（系统蜂鸣器/自定义音频文件）
- 视觉报警（界面闪烁/颜色变化）
- 报警延迟控制
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional


class AlarmController:
    """报警控制器，管理声光报警。"""

    def __init__(
        self,
        enable_sound: bool = True,
        sound_path: Optional[str] = None,
        delay_ms: int = 500,
    ) -> None:
        """初始化报警控制器。

        Args:
            enable_sound: 是否启用声音报警
            sound_path: 报警声音文件路径（可选）
            delay_ms: 报警延迟（毫秒）
        """
        self._enable_sound = enable_sound
        self._sound_path = sound_path
        self._delay_ms = delay_ms
        self._last_alarm_time = 0.0

    def trigger_alarm(self) -> bool:
        """触发报警。

        Returns:
            是否成功触发
        """
        # 检查延迟
        current_time = time.time()
        if current_time - self._last_alarm_time < self._delay_ms / 1000.0:
            return False

        self._last_alarm_time = current_time

        if self._enable_sound:
            self._play_sound()

        return True

    def _play_sound(self) -> None:
        """播放报警声音。"""
        if self._sound_path and Path(self._sound_path).exists():
            # 播放自定义音频文件
            try:
                import winsound

                winsound.PlaySound(self._sound_path, winsound.SND_FILENAME)
            except (ImportError, Exception):
                # 降级到系统蜂鸣器
                self._beep()
        else:
            # 使用系统蜂鸣器
            self._beep()

    def _beep(self) -> None:
        """系统蜂鸣器报警。"""
        try:
            import winsound

            # 频率 800Hz，持续 300ms
            winsound.Beep(800, 300)
        except (ImportError, Exception):
            # Windows 不可用时静默处理
            pass

    def trigger_pass(self) -> None:
        """触发通过提示音。"""
        try:
            import winsound

            # 短促提示音
            winsound.Beep(600, 100)
        except (ImportError, Exception):
            pass

    @property
    def enable_sound(self) -> bool:
        """是否启用声音。"""
        return self._enable_sound

    @enable_sound.setter
    def enable_sound(self, value: bool) -> None:
        self._enable_sound = value

    @property
    def delay_ms(self) -> int:
        """报警延迟（毫秒）。"""
        return self._delay_ms

    @delay_ms.setter
    def delay_ms(self, value: int) -> None:
        self._delay_ms = max(0, value)

    @property
    def sound_path(self) -> Optional[str]:
        """报警声音文件路径。"""
        return self._sound_path

    @sound_path.setter
    def sound_path(self, value: Optional[str]) -> None:
        self._sound_path = value
