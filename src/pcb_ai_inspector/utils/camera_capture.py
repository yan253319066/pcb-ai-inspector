"""
摄像头捕获模块。

提供实时摄像头预览和图像捕获功能。
"""

from __future__ import annotations

import cv2
import numpy as np
from dataclasses import dataclass
from typing import Callable, Optional

from loguru import logger


@dataclass
class CameraInfo:
    """摄像头信息。"""

    index: int
    name: str
    resolution: tuple[int, int]
    fps: float


class CameraCapture:
    """摄像头捕获类，支持实时预览和拍照。"""

    def __init__(self, camera_index: int = 0) -> None:
        """初始化摄像头。

        Args:
            camera_index: 摄像头索引（0=默认摄像头）
        """
        self._camera_index = camera_index
        self._capture: Optional[cv2.VideoCapture] = None
        self._is_opened = False

    def open(self) -> bool:
        """打开摄像头。

        Returns:
            是否成功打开
        """
        if self._capture is not None:
            self.close()

        self._capture = cv2.VideoCapture(self._camera_index)

        if not self._capture.isOpened():
            return False

        # 设置默认分辨率
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        self._is_opened = True
        return True

    def close(self) -> None:
        """关闭摄像头。"""
        if self._capture is not None:
            self._capture.release()
            self._capture = None
        self._is_opened = False

    def is_opened(self) -> bool:
        """检查摄像头是否已打开。

        Returns:
            是否已打开
        """
        return self._is_opened and self._capture is not None

    def read_frame(self) -> Optional[np.ndarray]:
        """读取下一帧。

        Returns:
            帧图像（BGR格式），失败返回 None
        """
        if not self.is_opened():
            return None

        ret, frame = self._capture.read()
        if not ret:
            return None

        return frame

    def get_info(self) -> Optional[CameraInfo]:
        """获取摄像头信息。

        Returns:
            摄像头信息
        """
        if not self.is_opened():
            return None

        width = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self._capture.get(cv2.CAP_PROP_FPS)

        return CameraInfo(
            index=self._camera_index,
            name=f"Camera {self._camera_index}",
            resolution=(width, height),
            fps=fps,
        )


class CameraPreview:
    """摄像头预览控制器，支持回调式预览。"""

    def __init__(
        self,
        camera_index: int = 0,
        on_frame: Optional[Callable[[np.ndarray], None]] = None,
    ) -> None:
        """初始化预览控制器。

        Args:
            camera_index: 摄像头索引
            on_frame: 每帧回调函数，参数为 BGR 图像
        """
        self._camera = CameraCapture(camera_index)
        self._on_frame = on_frame
        self._is_running = False

    def start(self) -> bool:
        """开始预览。

        Returns:
            是否成功开始
        """
        if not self._camera.open():
            return False

        self._is_running = True
        return True

    def stop(self) -> None:
        """停止预览。"""
        self._is_running = False
        self._camera.close()

    def is_running(self) -> bool:
        """检查是否正在预览。

        Returns:
            是否正在运行
        """
        return self._is_running

    def get_next_frame(self) -> Optional[np.ndarray]:
        """获取下一帧（手动调用模式）。

        Returns:
            帧图像
        """
        return self._camera.read_frame()


def list_available_cameras(max_count: int = 5) -> list[CameraInfo]:
    """列出可用的摄像头。

    Args:
        max_count: 最大检测数量

    Returns:
        可用摄像头列表
    """
    cameras = []
    logger.info(f"正在扫描可用摄像头 (最大检测: {max_count}) ...")

    for i in range(max_count):
        cap = cv2.VideoCapture(i)
        if not cap.isOpened():
            cap.release()
            logger.debug(f"摄像头索引 {i} 不可用，停止扫描")
            break

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        cameras.append(
            CameraInfo(
                index=i,
                name=f"Camera {i}",
                resolution=(width, height),
                fps=fps,
            )
        )
        logger.info(f"找到摄像头 {i}: {width}x{height} @ {fps}fps")
        cap.release()

    logger.info(f"扫描完成，找到 {len(cameras)} 个设备")
    return cameras


if __name__ == "__main__":
    # 测试摄像头检测
    print("检测可用摄像头...")
    cameras = list_available_cameras()

    if cameras:
        print(f"找到 {len(cameras)} 个摄像头:")
        for cam in cameras:
            print(
                f"  - {cam.name}: {cam.resolution[0]}x{cam.resolution[1]} @ {cam.fps:.1f} FPS"
            )
    else:
        print("未找到可用摄像头")