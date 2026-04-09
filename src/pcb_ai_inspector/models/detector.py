"""
YOLO 检测器模块，用于 PCB 缺陷检测。

本模块处理模型加载、推理和结果处理，支持自动 GPU/CPU 设备选择。
支持从配置读取参数。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import cv2
import numpy as np
import torch
from PIL import Image
from ultralytics import YOLO

from pcb_ai_inspector.core.defect_types import (
    MODEL_CLASS_MAPPING,
    DefectType,
)
from pcb_ai_inspector.utils.device import get_device
from loguru import logger

if TYPE_CHECKING:
    from ultralytics.engine.results import Results


# 从设置管理器获取默认配置
from pcb_ai_inspector.core.settings import (
    DEFAULT_MODEL_PATH,
    get_settings_manager,
)

_settings = get_settings_manager().settings

# 默认置信度阈值（从设置读取）
DEFAULT_CONFIDENCE = _settings.detection.confidence_threshold

# 默认输入图像尺寸（YOLO 期望）
DEFAULT_INPUT_SIZE = _settings.model.input_size


class BinarizationMethod(Enum):
    """二值化方法枚举。"""

    ADAPTIVE_GAUSSIAN = "adaptive_gaussian"
    """自适应高斯阈值（推荐，光照不均时效果好）"""

    ADAPTIVE_MEAN = "adaptive_mean"
    """自适应均值阈值（较快）"""

    OTSU = "otsu"
    """大津算法（自动计算最佳阈值）"""

    OTSU_GAUSSIAN = "otsu_gaussian"
    """大津 + 高斯模糊（噪声较多时）"""

    FIXED = "fixed"
    """固定阈值（已知光照条件时）"""


class LightingPreset(Enum):
    """光照预设枚举。"""

    UNIFORM = "uniform"
    """均匀光照 - 工厂/无影灯环境下"""

    UNEVEN = "uneven"
    """光照不均 - 有阴影或 반사情况下"""

    LOW_LIGHT = "low_light"
    """弱光环境 - 光源不足时"""

    UNKNOWN = "unknown"
    """自动检测（尝试多种方法）"""


# 预设配置
LIGHTING_PRESETS: dict[LightingPreset, dict[str, Any]] = {
    LightingPreset.UNIFORM: {
        "enable_denoise": True,
        "denoise_kernel": 3,
        "binarization_method": BinarizationMethod.OTSU,
        "otsu_blur_kernel": 5,
        "adaptive_block_size": 11,
        "adaptive_c": 2,
        "enable_clahe": False,
        "clahe_clip_limit": 2.0,
        "clahe_tile_size": 8,
    },
    LightingPreset.UNEVEN: {
        "enable_denoise": True,
        "denoise_kernel": 3,
        "binarization_method": BinarizationMethod.ADAPTIVE_GAUSSIAN,
        "otsu_blur_kernel": 5,
        "adaptive_block_size": 15,  # 更大块处理不均匀光照
        "adaptive_c": 4,  # 更高阈值
        "enable_clahe": True,  # 增强对比度
        "clahe_clip_limit": 2.5,
        "clahe_tile_size": 8,
    },
    LightingPreset.LOW_LIGHT: {
        "enable_denoise": True,
        "denoise_kernel": 5,  # 更大核去噪
        "binarization_method": BinarizationMethod.OTSU_GAUSSIAN,
        "otsu_blur_kernel": 5,
        "adaptive_block_size": 11,
        "adaptive_c": 3,
        "enable_clahe": True,  # 必须增强对比度
        "clahe_clip_limit": 3.0,  # 更高对比度
        "clahe_tile_size": 8,
    },
    LightingPreset.UNKNOWN: {
        "enable_denoise": True,
        "denoise_kernel": 3,
        "binarization_method": BinarizationMethod.ADAPTIVE_GAUSSIAN,
        "otsu_blur_kernel": 5,
        "adaptive_block_size": 11,
        "adaptive_c": 2,
        "enable_clahe": True,
        "clahe_clip_limit": 2.0,
        "clahe_tile_size": 8,
    },
}


class ImagePreprocessor:
    """PCB 相机图像预处理器，将实拍图处理为与 DeepPCB 训练数据一致的格式。

    使用示例：
        # 默认配置（光照未知）
        preprocessor = ImagePreprocessor()

        # 均匀光照环境
        preprocessor = ImagePreprocessor(lighting_preset=LightingPreset.UNIFORM)

        # 自定义参数
        preprocessor = ImagePreprocessor(
            binarization_method=BinarizationMethod.OTSU,
            adaptive_block_size=15,
            adaptive_c=3
        )
    """

    def __init__(
        self,
        target_size: int = DEFAULT_INPUT_SIZE,
        lighting_preset: LightingPreset | None = None,
        # 去噪参数
        enable_denoise: bool = True,
        denoise_kernel: int = 3,
        # 二值化参数
        binarization_method: BinarizationMethod = BinarizationMethod.ADAPTIVE_GAUSSIAN,
        otsu_blur_kernel: int = 5,
        adaptive_block_size: int = 11,
        adaptive_c: int = 2,
        fixed_threshold: int = 127,
        # CLAHE 对比度增强
        enable_clahe: bool = True,
        clahe_clip_limit: float = 2.0,
        clahe_tile_size: int = 8,
        # ROI 提取参数
        enable_roi: bool = True,
        roi_margin: int = 10,
        roi_min_area_ratio: float = 0.1,
    ) -> None:
        """初始化预处理器。

        参数:
            target_size: YOLO 输入尺寸（默认 640）
            lighting_preset: 光照预设（会自动填充上述参数）
            enable_denoise: 是否启用去噪
            denoise_kernel: 高斯模糊核大小（奇数）
            binarization_method: 二值化方法
            otsu_blur_kernel: Otsu 预处理的高斯核大小
            adaptive_block_size: 自适应阈值块大小（奇数）
            adaptive_c: 自适应阈值常数
            fixed_threshold: 固定阈值方法的阈值
            enable_clahe: 是否启用 CLAHE 对比度增强
            clahe_clip_limit: CLAHE 对比度限制
            clahe_tile_size: CLAHE 网格大小
            enable_roi: 是否启用 ROI 提取（自动检测 PCB 区域）
            roi_margin: ROI 边缘保留像素
            roi_min_area_ratio: ROI 最小面积占比（低于则不使用）

        注意:
            如果指定了 lighting_preset，会忽略其他二值化参数，使用预设值。
        """
        self.target_size = target_size

        # 如果指定了预设，使用预设配置
        if lighting_preset is not None and lighting_preset != LightingPreset.UNKNOWN:
            preset = LIGHTING_PRESETS[lighting_preset]
            self.enable_denoise = preset["enable_denoise"]
            self.denoise_kernel = preset["denoise_kernel"]
            self.binarization_method = BinarizationMethod[
                preset["binarization_method"].name
            ]
            self.otsu_blur_kernel = preset["otsu_blur_kernel"]
            self.adaptive_block_size = preset["adaptive_block_size"]
            self.adaptive_c = preset["adaptive_c"]
            self.enable_clahe = preset["enable_clahe"]
            self.clahe_clip_limit = preset["clahe_clip_limit"]
            self.clahe_tile_size = preset["clahe_tile_size"]
            self.enable_roi = enable_roi
            self.roi_margin = roi_margin
            self.roi_min_area_ratio = roi_min_area_ratio
        else:
            self.enable_denoise = enable_denoise
            self.denoise_kernel = denoise_kernel
            self.binarization_method = binarization_method
            self.otsu_blur_kernel = otsu_blur_kernel
            self.adaptive_block_size = adaptive_block_size
            self.adaptive_c = adaptive_c
            self.fixed_threshold = fixed_threshold
            self.enable_clahe = enable_clahe
            self.clahe_clip_limit = clahe_clip_limit
            self.clahe_tile_size = clahe_tile_size
            self.enable_roi = enable_roi
            self.roi_margin = roi_margin
            self.roi_min_area_ratio = roi_min_area_ratio

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """预处理图像：ROI 提取 -> CLAHE -> 去噪 -> 二值化 -> Letterbox 填充。

        参数:
            image: 输入图像（BGR 或 Gray）

        返回:
            预处理后的 RGB 图像（640x640）
        """
        # 确保是 BGR 格式（3通道）
        if len(image.shape) == 2:
            # 灰度图转为 BGR
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        elif image.shape[2] == 4:
            # RGBA 转为 BGR
            image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)

        # 0. ROI 提取（自动检测 PCB 区域）
        if self.enable_roi:
            roi = self._extract_roi(image)
            if roi is not None:
                image = roi

        # 确保是灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # 1. CLAHE 对比度增强（可选）
        if self.enable_clahe:
            clahe = cv2.createCLAHE(
                clipLimit=self.clahe_clip_limit,
                tileGridSize=(self.clahe_tile_size, self.clahe_tile_size),
            )
            gray = clahe.apply(gray)

        # 2. 去噪（高斯模糊）
        if self.enable_denoise:
            gray = cv2.GaussianBlur(gray, (self.denoise_kernel, self.denoise_kernel), 0)

        # 3. 二值化
        gray = self._binarize(gray)

        # 4. Letterbox 填充（保持长宽比）
        processed = self._letterbox(gray)

        # 4. 转回 RGB（YOLO 期望 3 通道）
        rgb = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)

        return rgb

    def _binarize(self, gray: np.ndarray) -> np.ndarray:
        """根据配置执行二值化。

        参数:
            gray: 灰度图

        返回:
            二值化后的灰度图
        """
        if self.binarization_method == BinarizationMethod.ADAPTIVE_GAUSSIAN:
            return cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                blockSize=self.adaptive_block_size,
                C=self.adaptive_c,
            )
        elif self.binarization_method == BinarizationMethod.ADAPTIVE_MEAN:
            return cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_MEAN_C,
                cv2.THRESH_BINARY,
                blockSize=self.adaptive_block_size,
                C=self.adaptive_c,
            )
        elif self.binarization_method == BinarizationMethod.OTSU:
            # Otsu 需要单通道图像
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return binary
        elif self.binarization_method == BinarizationMethod.OTSU_GAUSSIAN:
            # 先高斯模糊，再 Otsu
            blurred = cv2.GaussianBlur(
                gray, (self.otsu_blur_kernel, self.otsu_blur_kernel), 0
            )
            _, binary = cv2.threshold(
                blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
            return binary
        elif self.binarization_method == BinarizationMethod.FIXED:
            _, binary = cv2.threshold(
                gray, self.fixed_threshold, 255, cv2.THRESH_BINARY
            )
            return binary
        else:
            # 默认返回原图
            return gray

    def _letterbox(self, image: np.ndarray) -> np.ndarray:
        """Letterbox 填充：保持长宽比，填充灰色像素。

        参数:
            image: 输入灰度图

        返回:
            填充后的正方形灰度图
        """
        h, w = image.shape[:2]
        scale = min(self.target_size / h, self.target_size / w)
        new_h = int(h * scale)
        new_w = int(w * scale)

        # 使用 INTER_LINEAR 插值（更平滑）
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # 创建灰色画布
        canvas = np.full((self.target_size, self.target_size), 128, dtype=np.uint8)

        # 居中放置
        dy = (self.target_size - new_h) // 2
        dx = (self.target_size - new_w) // 2
        canvas[dy : dy + new_h, dx : dx + new_w] = resized

        return canvas

    def _extract_roi(self, image: np.ndarray) -> np.ndarray | None:
        """提取 PCB 感兴趣区域（ROI）。

        使用轮廓检测找到 PCB 边界，跳过黑色背景区域。
        这可以显著提升检测速度（减少推理区域）。

        参数:
            image: 输入 BGR 图像

        返回:
            裁剪后的 PCB 区域图像，如果检测失败返回 None
        """
        h, w = image.shape[:2]
        total_pixels = h * w

        # 转为灰度
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # 方法1: 自适应阈值检测 PCB 区域
        # PCB 通常比背景亮（或暗），使用自适应阈值找到边界
        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=15,
            C=5,
        )

        # 形态学操作：闭运算连接相邻区域
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        # 找轮廓
        contours, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return None

        # 找最大轮廓（应该是 PCB）
        max_area = 0
        best_rect = None

        for contour in contours:
            area = cv2.contourArea(contour)
            # 过滤太小或太大的轮廓
            if area < total_pixels * self.roi_min_area_ratio:
                continue
            if area > total_pixels * 0.95:
                continue

            x, y, cw, ch = cv2.boundingRect(contour)
            if area > max_area:
                max_area = area
                best_rect = (x, y, cw, ch)

        if best_rect is None:
            return None

        x, y, cw, ch = best_rect

        # 边缘保留
        x = max(0, x - self.roi_margin)
        y = max(0, y - self.roi_margin)
        cw = min(image.shape[1] - x, cw + 2 * self.roi_margin)
        ch = min(image.shape[0] - y, ch + 2 * self.roi_margin)

        return image[y : y + ch, x : x + cw]

    def preprocess_pil(self, image: Image.Image) -> np.ndarray:
        """预处理 PIL 图像。

        参数:
            image: PIL Image

        返回:
            预处理后的 numpy 数组（RGB，640x640）
        """
        # 转换为 numpy BGR
        img_array = np.array(image.convert("RGB"))
        bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        return self.preprocess(bgr)


@dataclass
class DetectionResult:
    """单个缺陷检测结果。"""

    defect_type: DefectType
    confidence: float
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    label: str  # 显示标签，包含类型和置信度


@dataclass
class ImageDetectionResult:
    """单张图像的检测结果。"""

    image_path: Path
    width: int
    height: int
    detections: list[DetectionResult]
    has_defects: bool
    defect_count: int
    device_used: str


class YOLODetector:
    """支持 GPU/CPU 的基于 YOLO 的 PCB 缺陷检测器。"""

    def __init__(
        self,
        model_path: str | Path | None = None,
        confidence_threshold: float = DEFAULT_CONFIDENCE,
        enable_preprocessing: bool = False,
    ) -> None:
        """初始化 YOLO 检测器。

        参数:
            model_path: YOLO 模型文件路径（.pt 或 .onnx）。必须指定且文件存在。
            confidence_threshold: 检测的最小置信度
            enable_preprocessing: 是否启用图像预处理（默认关闭，预处理会降低检测精度）
        """
        self.confidence_threshold = confidence_threshold
        self.device = get_device()
        self.model = None
        self.enable_preprocessing = enable_preprocessing
        self.preprocessor = ImagePreprocessor() if enable_preprocessing else None
        self.input_size = DEFAULT_INPUT_SIZE

        # 如果是字符串，转换为 Path 对象
        if model_path is not None:
            self.model_path = Path(model_path)
        else:
            self.model_path = None

    def load_model(self, model_path: str | Path | None = None) -> None:
        """加载或重新加载 YOLO 模型。

        参数:
            model_path: 模型文件路径。不能为 None 或不存在的文件。

        异常:
            FileNotFoundError: 如果模型文件不存在或未指定模型
        """
        if model_path is not None:
            self.model_path = Path(model_path)

        # 加载模型
        if self.model_path and self.model_path.exists():
            self.model = YOLO(str(self.model_path))
        else:
            # 如果没有指定模型或模型文件不存在，直接报错
            if self.model_path:
                raise FileNotFoundError(f"模型文件不存在: {self.model_path}")
            else:
                raise FileNotFoundError("未指定模型文件")

        # 将模型移动到适当的设备（GPU 或 CPU）
        # ultralytics 会根据 torch.cuda.is_available() 自动处理
        self.model.to(self.device)

    def detect(
        self,
        image: Image.Image | np.ndarray | str | Path,
    ) -> ImageDetectionResult:
        """检测图像中的缺陷。

        参数:
            image: PIL Image、numpy 数组或图像文件路径

        返回:
            包含所有检测结果的 ImageDetectionResult
        """
        if self.model is None:
            self.load_model()

        if self.model is None:
            raise RuntimeError("模型加载失败")

        # 处理 None 输入
        if image is None:
            return ImageDetectionResult(
                image_path=Path("unknown"),
                width=0,
                height=0,
                detections=[],
                has_defects=False,
                defect_count=0,
                device_used=self.device,
            )

        # 获取图像路径（如果可用）
        if isinstance(image, (str, Path)):
            image_path = Path(image)
            # 加载图像并转换为灰度（如果需要）
            img = Image.open(str(image_path))
            if img.mode != "L":
                # 彩色图像转换为灰度图（与训练数据一致）
                img = img.convert("L")
                # 转换回 RGB（YOLO 期望 3 通道）
                img = img.convert("RGB")
            image = img
        else:
            image_path = Path("unknown")

        # 预处理（去噪 + 二值化 + Letterbox）
        if self.enable_preprocessing and self.preprocessor is not None:
            # 转换为 numpy 进行预处理
            if isinstance(image, Image.Image):
                processed_image = self.preprocessor.preprocess_pil(image)
            elif isinstance(image, np.ndarray):
                processed_image = self._preprocess_numpy(image)
            else:
                # 其他类型（如已处理的）直接使用
                processed_image = image
        else:
            # 不使用预处理时直接使用原始图像（彩色）
            if isinstance(image, Image.Image):
                if img.mode != "RGB":
                    img_array = np.array(image.convert("RGB"))
                else:
                    img_array = np.array(image)
                processed_image = img_array
            elif (
                isinstance(image, np.ndarray)
                and len(image.shape) == 3
                and image.shape[2] == 3
            ):
                # numpy 彩色图（BGR 格式）- 转换为 RGB
                processed_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                processed_image = image

        # 运行推理
        results: list[Results] = self.model.predict(
            source=processed_image,
            conf=self.confidence_threshold,
            verbose=False,
        )

        # 处理结果
        detections: list[DetectionResult] = []

        # 获取原始图像尺寸（在预处理之前）
        if isinstance(image, (str, Path)):
            if hasattr(image, "size"):
                orig_w, orig_h = image.size
            else:
                orig_w, orig_h = 640, 640
        elif isinstance(image, Image.Image):
            orig_w, orig_h = image.size
        elif isinstance(image, np.ndarray):
            orig_h, orig_w = image.shape[:2]
        else:
            orig_w, orig_h = 640, 640

        # 获取模型输入图像的尺寸（预处理后）
        if len(processed_image.shape) == 3:
            model_h, model_w = processed_image.shape[:2]
        else:
            model_h, model_w = processed_image.shape[:2], processed_image.shape[1]

        # 计算坐标缩放比例：模型输入 -> 原始图像
        scale_x = orig_w / model_w if model_w > 0 else 1.0
        scale_y = orig_h / model_h if model_h > 0 else 1.0

        # 计算 letterbox 偏移（如果使用了 letterbox）
        letterbox_offset_x = 0
        letterbox_offset_y = 0
        # 获取实际使用的 target_size（优先使用预处理器的设置）
        target_size = (
            self.target_size if hasattr(self, "target_size") else DEFAULT_INPUT_SIZE
        )
        if model_w == target_size and model_h == target_size:
            # 可能是 letterbox 填充，需要计算偏移
            scale = min(orig_h / target_size, orig_w / target_size)
            if scale < 1.0:
                new_w = int(orig_w / scale)
                new_h = int(orig_h / scale)
                if new_w <= target_size and new_h <= target_size:
                    letterbox_offset_x = (target_size - new_w) // 2
                    letterbox_offset_y = (target_size - new_h) // 2

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for box in boxes:
                # 获取类别 ID 并映射到缺陷类型
                class_id = int(box.cls.cpu().numpy()[0])
                confidence = float(box.conf.cpu().numpy()[0])

                # 将类别 ID 映射到 DefectType（处理未知类别）
                if class_id in MODEL_CLASS_MAPPING:
                    defect_type = MODEL_CLASS_MAPPING[class_id]
                else:
                    # 未知类别的备用方案
                    defect_type = DefectType.SHORT_CIRCUIT

                # 获取边界框坐标（模型输入尺寸）
                xyxy = box.xyxy[0].cpu().numpy()  # x1, y1, x2, y2
                # 应用坐标变换：模型输入 -> 原始图像
                x1 = int((xyxy[0] - letterbox_offset_x) * scale_x)
                y1 = int((xyxy[1] - letterbox_offset_y) * scale_y)
                x2 = int((xyxy[2] - letterbox_offset_x) * scale_x)
                y2 = int((xyxy[3] - letterbox_offset_y) * scale_y)

                # 确保坐标在有效范围内
                x1 = max(0, min(x1, orig_w - 1))
                y1 = max(0, min(y1, orig_h - 1))
                x2 = max(0, min(x2, orig_w - 1))
                y2 = max(0, min(y2, orig_h - 1))

                # 创建检测结果
                detection = DetectionResult(
                    defect_type=defect_type,
                    confidence=confidence,
                    bbox=(x1, y1, x2, y2),
                    label=f"{defect_type.display_name} - {confidence:.0%}",
                )
                detections.append(detection)

        # 获取原始输入图像的尺寸（不是处理后的）
        if isinstance(image, (str, Path)):
            # 已经转换为 Image.Image
            if hasattr(image, "size"):
                width, height = image.size
            else:
                width, height = 640, 640
        elif isinstance(image, Image.Image):
            width, height = image.size
        elif isinstance(image, np.ndarray):
            height, width = image.shape[:2]
        else:
            width, height = 640, 640

        return ImageDetectionResult(
            image_path=image_path,
            width=width,
            height=height,
            detections=detections,
            has_defects=len(detections) > 0,
            defect_count=len(detections),
            device_used=str(self.device),
        )

    def _preprocess_numpy(self, image: np.ndarray) -> np.ndarray:
        """预处理 numpy 数组图像。

        参数:
            image: BGR 格式的 numpy 数组

        返回:
            预处理后的 RGB 图像
        """
        if self.preprocessor is not None:
            return self.preprocessor.preprocess(image)
        # 无预处理器时直接转换
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            return cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        return image

    def detect_from_path(self, image_path: str | Path) -> ImageDetectionResult:
        """从文件路径检测的便捷方法。

        参数:
            image_path: 图像文件路径

        返回:
            检测结果
        """
        return self.detect(str(image_path))

    def set_confidence_threshold(self, threshold: float) -> None:
        """更新置信度阈值。

        参数:
            threshold: 新的置信度阈值（0.0 到 1.0）
        """
        self.confidence_threshold = max(0.0, min(1.0, threshold))

    def has_pcb_region(
        self,
        frame: np.ndarray,
        center_ratio: float = 0.5,
        min_green_ratio: float = 0.25,
    ) -> bool:
        """检测画面中是否包含 PCB 区域。

        使用更严格的策略：要求中心区域必须有足够比例的绿色/蓝色 PCB 颜色

        参数:
            frame: BGR 格式的图像帧
            center_ratio: PCB 中心区域占比（0.0-1.0），默认 0.5 表示中心 50% 区域
            min_green_ratio: 中心区域绿色/蓝色像素最低占比，默认 15%

        返回:
            True 表示画面中包含 PCB 区域
        """
        if frame is None or frame.size == 0:
            return False

        h, w = frame.shape[:2]

        center_x, center_y = w // 2, h // 2
        center_w, center_h = int(w * center_ratio), int(h * center_ratio)
        center_roi = frame[
            center_y - center_h // 2 : center_y + center_h // 2,
            center_x - center_w // 2 : center_x + center_w // 2,
        ]

        if center_roi.size == 0:
            return False

        center_area = center_roi.shape[0] * center_roi.shape[1]
        if center_area == 0:
            return False

        hsv = cv2.cvtColor(center_roi, cv2.COLOR_BGR2HSV)

        green_mask = cv2.inRange(
            hsv,
            np.array([35, 50, 50]),
            np.array([85, 255, 255]),
        )
        green_pixels = cv2.countNonZero(green_mask)

        blue_mask = cv2.inRange(
            hsv,
            np.array([100, 50, 50]),
            np.array([130, 255, 255]),
        )
        blue_pixels = cv2.countNonZero(blue_mask)

        gold_mask = cv2.inRange(
            hsv,
            np.array([15, 60, 80]),
            np.array([25, 255, 255]),
        )
        gold_pixels = cv2.countNonZero(gold_mask)

        total_pcb_pixels = green_pixels + blue_pixels + gold_pixels
        pcb_ratio = total_pcb_pixels / center_area

        logger.debug(f"绿色:{green_pixels} 蓝色:{blue_pixels} 金色:{gold_pixels} 总计:{total_pcb_pixels}/{center_area} 比例:{pcb_ratio:.2%} 阈值:{min_green_ratio:.2%}")

        if pcb_ratio >= min_green_ratio:
            logger.debug(f"判定: 有PCB")
            return True

        logger.debug(f"判定: 无PCB")
        return False


def create_detector(
    model_path: str | Path | None = None,
    confidence: float = DEFAULT_CONFIDENCE,
    preprocessing_settings: dict | None = None,
) -> YOLODetector:
    """创建检测器实例的工厂函数。

    参数:
        model_path: 自定义模型的路径（可选）
        confidence: 置信度阈值
        preprocessing_settings: 预处理设置字典（可选）

    返回:
        配置好的 YOLODetector 实例
    """
    # 解析预处理设置
    enable_preprocessing = True
    preprocessor = None

    if preprocessing_settings is not None:
        enable_preprocessing = preprocessing_settings.get("enable_preprocessing", True)

        if enable_preprocessing:
            from .detector import (
                BinarizationMethod,
                ImagePreprocessor,
                LightingPreset,
            )

            lighting_preset_str = preprocessing_settings.get(
                "lighting_preset", "unknown"
            )
            binarization_method_str = preprocessing_settings.get(
                "binarization_method", "adaptive_gaussian"
            )

            preprocessor = ImagePreprocessor(
                lighting_preset=LightingPreset(lighting_preset_str)
                if lighting_preset_str != "unknown"
                else None,
                binarization_method=BinarizationMethod(binarization_method_str),
                enable_denoise=preprocessing_settings.get("enable_denoise", True),
                denoise_kernel=preprocessing_settings.get("denoise_kernel", 3),
                adaptive_block_size=preprocessing_settings.get(
                    "adaptive_block_size", 11
                ),
                adaptive_c=preprocessing_settings.get("adaptive_c", 2),
                fixed_threshold=preprocessing_settings.get("fixed_threshold", 127),
                enable_clahe=preprocessing_settings.get("enable_clahe", True),
                clahe_clip_limit=preprocessing_settings.get("clahe_clip_limit", 2.0),
                clahe_tile_size=preprocessing_settings.get("clahe_tile_size", 8),
                enable_roi=preprocessing_settings.get("enable_roi", True),
                roi_margin=preprocessing_settings.get("roi_margin", 10),
                roi_min_area_ratio=preprocessing_settings.get(
                    "roi_min_area_ratio", 0.1
                ),
            )

    detector = YOLODetector(
        model_path=model_path,
        confidence_threshold=confidence,
        enable_preprocessing=enable_preprocessing,
    )

    if preprocessor is not None:
        detector.preprocessor = preprocessor

    return detector


if __name__ == "__main__":
    # 测试检测器
    import argparse
    from pathlib import Path
    from pcb_ai_inspector.utils.device import print_device_info

    parser = argparse.ArgumentParser()
    parser.add_argument("image", nargs="?", help="图片路径")
    parser.add_argument("--conf", type=float, default=0.5, help="置信度阈值")
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL_PATH,
        help="模型路径",
    )
    args = parser.parse_args()

    print_device_info()
    print("\n初始化检测器...")

    # 创建检测器（使用用户指定的模型，预处理默认关闭）
    model_path = Path(args.model) if args.model else None
    detector = YOLODetector(
        model_path=str(model_path) if model_path and model_path.exists() else None,
        confidence_threshold=args.conf,
        enable_preprocessing=False,  # 默认关闭预处理
    )
    print(f"检测器就绪。使用设备: {detector.device}")

    if args.image:
        print(f"\n检测图片: {args.image}")
        result = detector.detect(args.image)
        print(f"\n图片尺寸: {result.width} x {result.height}")
        print(f"缺陷数量: {result.defect_count}")
        if result.defect_count == 0:
            print("未检测到缺陷")
        else:
            print(f"\n检测到的缺陷:")
            for i, d in enumerate(result.detections, 1):
                x1, y1, x2, y2 = d.bbox
                print(
                    f"  {i}. {d.defect_type.display_name} - {d.confidence:.1%} - 位置:({x1},{y1},{x2},{y2})"
                )
