"""
工业相机模块。

支持多种工业相机协议：
- GigE Vision (千兆网相机)
- USB3 Vision
- USB 工业相机 (兼容普通 USB 摄像头)

触发模式：
- 外部触发 (External Trigger)
- 软件触发 (Software Trigger)
- 连续采集 (Continuous)
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

import cv2
import numpy as np

from loguru import logger


class TriggerMode(Enum):
    """触发模式。"""

    CONTINUOUS = "continuous"  # 连续采集
    EXTERNAL = "external"  # 外部触发（GPIO/光电开关）
    SOFTWARE = "software"  # 软件触发


class CameraStatus(Enum):
    """相机状态。"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    STREAMING = "streaming"
    ERROR = "error"


@dataclass
class CameraConfig:
    """相机配置。"""

    camera_type: str  # "gige", "usb3", "usb"
    camera_id: str  # IP 地址或设备索引
    resolution: tuple[int, int] = (1920, 1080)
    exposure: float = 10000.0  # 曝光时间 (微秒)
    gain: float = 0.0  # 增益
    trigger_mode: TriggerMode = TriggerMode.CONTINUOUS
    trigger_source: int = 0  # 触发源 (0=Line0, 1=Line1, etc.)
    timeout_ms: int = 5000  # 超时时间 (毫秒)


@dataclass
class CameraDeviceInfo:
    """相机设备信息。"""

    device_id: str  # IP 地址或设备索引
    device_name: str  # 设备名称
    manufacturer: str  # 制造商
    model: str  # 型号
    serial_number: str  # 序列号
    firmware_version: str  # 固件版本
    resolution: tuple[int, int]  # 最大分辨率
    ip_address: Optional[str] = None  # IP 地址 (GigE)


class IndustrialCamera(ABC):
    """工业相机抽象基类。"""

    def __init__(self, config: CameraConfig) -> None:
        """初始化相机。

        Args:
            config: 相机配置
        """
        self._config = config
        self._status = CameraStatus.DISCONNECTED
        self._is_streaming = False
        self._frame_lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None

    @property
    def config(self) -> CameraConfig:
        """获取配置。"""
        return self._config

    @property
    def status(self) -> CameraStatus:
        """获取状态。"""
        return self._status

    @property
    def is_connected(self) -> bool:
        """检查是否已连接。"""
        return self._status in (CameraStatus.CONNECTED, CameraStatus.STREAMING)

    @abstractmethod
    def connect(self) -> bool:
        """连接相机。

        Returns:
            是否成功连接
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """断开连接。"""
        pass

    @abstractmethod
    def start_streaming(self) -> bool:
        """开始采集。

        Returns:
            是否成功开始
        """
        pass

    @abstractmethod
    def stop_streaming(self) -> None:
        """停止采集。"""
        pass

    @abstractmethod
    def trigger_software(self) -> bool:
        """软件触发一次采集。

        Returns:
            是否成功触发
        """
        pass

    @abstractmethod
    def get_frame(self) -> Optional[np.ndarray]:
        """获取最新一帧。

        Returns:
            BGR 格式图像，失败返回 None
        """
        pass

    @abstractmethod
    def get_device_info(self) -> Optional[CameraDeviceInfo]:
        """获取设备信息。

        Returns:
            设备信息
        """
        pass

    @abstractmethod
    def set_exposure(self, exposure_us: float) -> bool:
        """设置曝光时间。

        Args:
            exposure_us: 曝光时间（微秒）

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    def set_gain(self, gain: float) -> bool:
        """设置增益。

        Args:
            gain: 增益值

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    def set_resolution(self, width: int, height: int) -> bool:
        """设置分辨率。

        Args:
            width: 宽度
            height: 高度

        Returns:
            是否成功
        """
        pass

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """获取最新一帧（线程安全）。

        Returns:
            BGR 格式图像
        """
        with self._frame_lock:
            return self._latest_frame.copy() if self._latest_frame is not None else None

    def _update_frame(self, frame: np.ndarray) -> None:
        """更新最新帧（子类调用）。"""
        with self._frame_lock:
            self._latest_frame = frame.copy()


class USBCamera(IndustrialCamera):
    """USB 工业相机/普通摄像头。"""

    def __init__(self, config: CameraConfig) -> None:
        """初始化 USB 相机。

        Args:
            config: 相机配置，camera_id 为设备索引 (0, 1, ...)
        """
        super().__init__(config)
        self._camera_index = int(config.camera_id) if config.camera_id.isdigit() else 0
        self._capture = None

    def connect(self) -> bool:
        """连接相机。"""
        import cv2

        try:
            self._status = CameraStatus.CONNECTING
            self._capture = cv2.VideoCapture(self._camera_index)

            if not self._capture.isOpened():
                self._status = CameraStatus.ERROR
                return False

            # 设置分辨率
            w, h = self._config.resolution
            self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, w)
            self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, h)

            # 设置曝光
            if self._config.exposure > 0:
                self._capture.set(cv2.CAP_PROP_EXPOSURE, self._config.exposure / 1000)

            # 设置增益
            if self._config.gain > 0:
                self._capture.set(cv2.CAP_PROP_GAIN, self._config.gain)

            self._status = CameraStatus.CONNECTED
            return True

        except Exception:
            self._status = CameraStatus.ERROR
            return False

    def disconnect(self) -> None:
        """断开连接。"""
        if self._capture is not None:
            self._capture.release()
            self._capture = None
        self._status = CameraStatus.DISCONNECTED

    def start_streaming(self) -> bool:
        """开始采集。"""
        if not self.is_connected:
            return False
        self._is_streaming = True
        self._status = CameraStatus.STREAMING
        return True

    def stop_streaming(self) -> None:
        """停止采集。"""
        self._is_streaming = False
        if self._status == CameraStatus.STREAMING:
            self._status = CameraStatus.CONNECTED

    def trigger_software(self) -> bool:
        """软件触发。USB 相机在连续模式下自动采集，返回当前帧。"""
        return True

    def get_frame(self) -> Optional[np.ndarray]:
        """获取一帧。"""
        import cv2

        if not self.is_connected or self._capture is None:
            return None

        ret, frame = self._capture.read()
        if not ret:
            return None

        self._update_frame(frame)
        return frame

    def get_device_info(self) -> Optional[CameraDeviceInfo]:
        """获取设备信息。"""
        import cv2

        if not self.is_connected or self._capture is None:
            return None

        w = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

        return CameraDeviceInfo(
            device_id=str(self._camera_index),
            device_name=f"USB Camera {self._camera_index}",
            manufacturer="Unknown",
            model="USB Camera",
            serial_number="N/A",
            firmware_version="N/A",
            resolution=(w, h),
        )

    def set_exposure(self, exposure_us: float) -> bool:
        """设置曝光。"""
        if not self.is_connected or self._capture is None:
            return False
        import cv2

        # OpenCV exposure 是相对值 0-100，转换为微秒需要约除以 1000
        exp_value = max(1, min(100, exposure_us / 1000))
        self._capture.set(cv2.CAP_PROP_EXPOSURE, exp_value)
        self._config.exposure = exposure_us
        return True

    def set_gain(self, gain: float) -> bool:
        """设置增益。"""
        if not self.is_connected or self._capture is None:
            return False

        self._capture.set(cv2.CAP_PROP_GAIN, gain)
        self._config.gain = gain
        return True

    def set_resolution(self, width: int, height: int) -> bool:
        """设置分辨率。"""
        if not self.is_connected or self._capture is None:
            return False

        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self._config.resolution = (width, height)
        return True


class GigECamera(IndustrialCamera):
    """GigE Vision 工业相机。

    支持主流厂商：
    - Basler (pypylon)
    - Hikvision (hxkit)
    - Dahua (dhimaging)
    - 海康机器人

    使用 PyGige 或通用 GigE Vision 协议。
    """

    def __init__(self, config: CameraConfig) -> None:
        """初始化 GigE 相机。

        Args:
            config: 相机配置，camera_id 为 IP 地址或 MAC 地址
        """
        super().__init__(config)
        self._camera = None
        self._sdk_available = False

    def connect(self) -> bool:
        """连接 GigE 相机。"""
        # 尝试加载各个厂商的 SDK
        self._camera = self._try_connect_pypylon()
        if self._camera is not None:
            self._sdk_available = True
            self._status = CameraStatus.CONNECTED
            return True

        # 尝试通用 GigE Vision (opencv gstreamer or genapi)
        self._camera = self._try_connect_gige()
        if self._camera is not None:
            self._sdk_available = True
            self._status = CameraStatus.CONNECTED
            return True

        # 如果都不可用，使用模拟模式（开发测试用）
        self._status = CameraStatus.ERROR
        return False

    def _try_connect_pypylon(self):
        """尝试使用 Basler pypylon 连接。"""
        try:
            from pypylon import pylon

            # 通过 IP 连接
            ip = self._config.camera_id
            devices = pylon.TlFactory.GetInstance().EnumerateDevices()

            for dev in devices:
                if dev.GetDeviceIPAddress() == ip or dev.GetSerialNumber() == ip:
                    camera = pylon.InstantCamera(
                        pylon.TlFactory.GetInstance().CreateDevice(dev)
                    )
                    camera.Open()
                    return camera
        except ImportError:
            pass
        return None

    def _try_connect_gige(self) -> None:
        """尝试使用通用 GigE 连接。"""
        # 可以使用 opencv 的 GigE 采集卡或 genapi
        # 这里预留接口，实际根据环境配置
        pass

    def disconnect(self) -> None:
        """断开连接。"""
        if self._camera is not None:
            try:
                if hasattr(self._camera, "Close"):
                    self._camera.Close()
            except Exception:
                pass
            self._camera = None
        self._status = CameraStatus.DISCONNECTED

    def start_streaming(self) -> bool:
        """开始采集。"""
        if not self.is_connected:
            return False

        try:
            if hasattr(self._camera, "StartGrabbing"):
                self._camera.StartGrabbing()
            self._is_streaming = True
            self._status = CameraStatus.STREAMING
            return True
        except Exception:
            return False

    def stop_streaming(self) -> None:
        """停止采集。"""
        try:
            if hasattr(self._camera, "StopGrabbing"):
                self._camera.StopGrabbing()
        except Exception:
            pass
        self._is_streaming = False
        if self._status == CameraStatus.STREAMING:
            self._status = CameraStatus.CONNECTED

    def trigger_software(self) -> bool:
        """软件触发。"""
        if not self.is_connected:
            return False

        try:
            if hasattr(self._camera, "TriggerSoftware"):
                self._camera.TriggerSoftware()
                return True
        except Exception:
            pass
        return False

    def get_frame(self) -> Optional[np.ndarray]:
        """获取一帧。"""
        if not self.is_streaming:
            return None

        try:
            from pypylon import pylon

            if hasattr(self._camera, "RetrieveResult"):
                result = self._camera.RetrieveResult(
                    5000, pylon.TimeoutHandling_ThrowException
                )
                if result.GrabSucceeded():
                    frame = result.Array
                    # 转换为 BGR
                    import cv2

                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                    self._update_frame(frame_bgr)
                    return frame_bgr
        except Exception:
            pass
        return None

    def get_device_info(self) -> Optional[CameraDeviceInfo]:
        """获取设备信息。"""
        if not self.is_connected:
            return None

        try:
            if hasattr(self._camera, "GetDeviceInfo"):
                info = self._camera.GetDeviceInfo()
                return CameraDeviceInfo(
                    device_id=self._config.camera_id,
                    device_name=info.GetModelName(),
                    manufacturer=info.GetVendorName(),
                    model=info.GetModelName(),
                    serial_number=info.GetSerialNumber(),
                    firmware_version=info.GetDeviceVersion(),
                    resolution=self._config.resolution,
                    ip_address=self._config.camera_id,
                )
        except Exception:
            pass

        return CameraDeviceInfo(
            device_id=self._config.camera_id,
            device_name=f"GigE Camera {self._config.camera_id}",
            manufacturer="Unknown",
            model="GigE Camera",
            serial_number="N/A",
            firmware_version="N/A",
            resolution=self._config.resolution,
            ip_address=self._config.camera_id,
        )

    def set_exposure(self, exposure_us: float) -> bool:
        """设置曝光。"""
        if not self.is_connected:
            return False

        try:
            if hasattr(self._camera, "ExposureTime"):
                self._camera.ExposureTime.SetValue(exposure_us)
                self._config.exposure = exposure_us
                return True
        except Exception:
            pass
        return False

    def set_gain(self, gain: float) -> bool:
        """设置增益。"""
        if not self.is_connected:
            return False

        try:
            if hasattr(self._camera, "Gain"):
                self._camera.Gain.SetValue(gain)
                self._config.gain = gain
                return True
        except Exception:
            pass
        return False

    def set_resolution(self, width: int, height: int) -> bool:
        """设置分辨率。"""
        if not self.is_connected:
            return False

        try:
            if hasattr(self._camera, "Width") and hasattr(self._camera, "Height"):
                self._camera.Width.SetValue(width)
                self._camera.Height.SetValue(height)
                self._config.resolution = (width, height)
                return True
        except Exception:
            pass
        return False


def create_camera(config: CameraConfig) -> IndustrialCamera:
    """根据配置创建相机实例。

    Args:
        config: 相机配置

    Returns:
        相机实例

    Raises:
        ValueError: 不支持的相机类型
    """
    camera_type = config.camera_type.lower()

    if camera_type in ("usb", "usb2", "usb3", "webcam"):
        return USBCamera(config)
    elif camera_type in ("gige", "gige_vision", "gigabit", "ethernet"):
        return GigECamera(config)
    else:
        raise ValueError(f"不支持的相机类型: {camera_type}")


def discover_cameras() -> list[CameraDeviceInfo]:
    """发现可用的工业相机。

    Returns:
        可用相机列表
    """
    devices: list[CameraDeviceInfo] = []
    logger.info("正在扫描 USB 相机 ...")

    import cv2

    for i in range(5):
        cap = cv2.VideoCapture(i)
        if not cap.isOpened():
            cap.release()
            break

        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        devices.append(
            CameraDeviceInfo(
                device_id=str(i),
                device_name=f"USB Camera {i}",
                manufacturer="Unknown",
                model="USB Camera",
                serial_number="N/A",
                firmware_version="N/A",
                resolution=(w, h),
            )
        )
        logger.info(f"找到 USB 相机 {i}: {w}x{h}")
        cap.release()

    # 尝试扫描 GigE 相机
    try:
        from pypylon import pylon

        devices_pylon = pylon.TlFactory.GetInstance().EnumerateDevices()
        for dev in devices_pylon:
            ip = dev.GetDeviceIPAddress() if hasattr(dev, "GetDeviceIPAddress") else ""
            devices.append(
                CameraDeviceInfo(
                    device_id=ip or dev.GetSerialNumber(),
                    device_name=dev.GetModelName(),
                    manufacturer=dev.GetVendorName(),
                    model=dev.GetModelName(),
                    serial_number=dev.GetSerialNumber(),
                    firmware_version=dev.GetDeviceVersion(),
                    resolution=(1920, 1080),
                    ip_address=ip,
                )
            )
    except ImportError:
        pass

    return devices
