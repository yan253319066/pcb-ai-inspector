"""
PCB AI Inspector 检测结果处理服务。

提供单图检测和批量检测共用的结果处理逻辑，
包括检测结果格式转换、UI 数据更新等。
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import numpy as np

from ..core.defect_types import DefectType
from .defect_overlay import DetectionResult as UIDetectionResult

if TYPE_CHECKING:
    from ..models.detector import YOLODetector, DetectionResult as ModelDetectionResult


@dataclass
class DetectionContext:
    """检测上下文，包含检测所需的所有信息。"""

    image: np.ndarray
    image_path: Path
    confidence_threshold: float
    detector: "YOLODetector"


class DetectionResultHandler:
    """
    检测结果处理器。

    封装单图和批量检测共用的结果处理逻辑：
    1. 格式转换：模型 DetectionResult -> UI DetectionResult
    2. 结果存储：保存到 _all_results 字典
    3. 表格更新：添加到结果表格
    4. 统计更新：更新缺陷统计
    """

    def __init__(self) -> None:
        """初始化检测结果处理器。"""
        # 类别映射缓存
        self._type_to_id: dict = {}

    def set_class_mapping(self, class_mapping: dict[int, "DefectType"]) -> None:
        """设置类别映射。"""
        self._type_to_id = {v: k for k, v in class_mapping.items()}

    def convert_to_ui_result(
        self,
        model_detections: list,
    ) -> list[UIDetectionResult]:
        """
        将模型检测结果转换为 UI 专用的 DetectionResult。

        参数:
            model_detections: 模型输出的检测结果列表

        返回:
            UI 专用的 DetectionResult 列表
        """
        return [
            UIDetectionResult(
                bbox=det.bbox,
                confidence=det.confidence,
                defect_type=det.defect_type,
                class_id=self._type_to_id.get(det.defect_type, 0),
            )
            for det in model_detections
        ]

    def get_image_name(self, image_path: Path) -> str:
        """获取图像文件名。"""
        return image_path.name

    def calculate_average_confidence(
        self,
        detections: list[UIDetectionResult],
    ) -> Optional[float]:
        """计算平均置信度。"""
        if not detections:
            return None
        return sum(d.confidence for d in detections) / len(detections)

    def create_result_status(
        self,
        detections: list[UIDetectionResult],
    ) -> str:
        """创建检测状态文本。"""
        return "✓" if detections else "无缺陷"

    def create_marked_image(
        self,
        original_image: np.ndarray,
    ) -> np.ndarray:
        """
        创建带标记的图像。

        参数:
            original_image: 原始图像

        返回:
            标记图像（当前直接返回原始图像，由 DetectionOverlay 处理渲染）
        """
        return original_image


def create_result_handler() -> DetectionResultHandler:
    """创建检测结果处理器的工厂函数。"""
    return DetectionResultHandler()
