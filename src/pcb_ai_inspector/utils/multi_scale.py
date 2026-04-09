"""
多尺度检测模块 - 同一图像多个尺度检测。

用于检测不同大小的缺陷：在不同尺度下检测图像，
小尺度检测大缺陷，大尺度检测小缺陷。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np


@dataclass
class ScaleResult:
    """单个尺度的检测结果。"""

    scale: float  # 缩放比例
    detections: list  # 检测结果列表


class MultiScaleDetector:
    """多尺度检测器。"""

    def __init__(
        self,
        min_scale: float = 0.5,
        max_scale: float = 2.0,
        scales: Optional[list[float]] = None,
    ) -> None:
        """初始化多尺度检测器。

        Args:
            min_scale: 最小缩放比例
            max_scale: 最大缩放比例
            scales: 指定缩放比例列表（优先使用）
        """
        if scales is not None:
            self.scales = scales
        else:
            # 默认使用几个常用尺度
            self.scales = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]

        self.min_scale = min_scale
        self.max_scale = max_scale

    def detect_at_scales(
        self,
        image: np.ndarray,
        detect_fn: Callable[[np.ndarray], list],
    ) -> list[ScaleResult]:
        """在多个尺度上检测。

        Args:
            image: 输入图像
            detect_fn: 检测函数，输入图像，返回检测结果列表

        Returns:
            每个尺度的检测结果
        """
        results = []

        for scale in self.scales:
            # 跳过超出范围的尺度
            if scale < self.min_scale or scale > self.max_scale:
                continue

            # 缩放图像
            scaled = self._scale_image(image, scale)

            # 检测
            detections = detect_fn(scaled)

            # 转换坐标回原始尺度
            scaled_detections = self._rescale_detections(detections, scale)

            results.append(
                ScaleResult(
                    scale=scale,
                    detections=scaled_detections,
                )
            )

        return results

    def _scale_image(self, image: np.ndarray, scale: float) -> np.ndarray:
        """缩放图像。

        Args:
            image: 输入图像
            scale: 缩放比例

        Returns:
            缩放后的图像
        """
        import cv2

        h, w = image.shape[:2]
        new_w = int(w * scale)
        new_h = int(h * scale)

        if scale < 1.0:
            # 缩小使用 INTER_AREA
            interpolation = cv2.INTER_AREA
        else:
            # 放大使用 INTER_LINEAR
            interpolation = cv2.INTER_LINEAR

        return cv2.resize(image, (new_w, new_h), interpolation=interpolation)

    def _rescale_detections(
        self,
        detections: list,
        scale: float,
    ) -> list:
        """将检测结果坐标转换回原始尺度。

        Args:
            detections: 检测结果列表
            scale: 缩放比例

        Returns:
            转换后的检测结果
        """
        scaled_detections = []

        for det in detections:
            if hasattr(det, "bbox"):
                x1, y1, x2, y2 = det.bbox
                # 反向缩放坐标
                new_bbox = (
                    int(x1 / scale),
                    int(y1 / scale),
                    int(x2 / scale),
                    int(y2 / scale),
                )
                # 克隆检测结果并更新坐标
                new_det = {
                    "label": det.label,
                    "confidence": det.confidence,
                    "bbox": new_bbox,
                    "scale": scale,
                }
                scaled_detections.append(new_det)

        return scaled_detections

    def merge_results(
        self,
        scale_results: list[ScaleResult],
        conf_threshold: float = 0.3,
    ) -> list:
        """合并多尺度检测结果。

        Args:
            scale_results: 多尺度检测结果
            conf_threshold: 置信度阈值

        Returns:
            合并后的检测结果
        """
        all_detections = []

        for result in scale_results:
            for det in result.detections:
                # 过滤低置信度
                if det.get("confidence", 0) >= conf_threshold:
                    all_detections.append(det)

        # NMS 去除重复
        return self._nms_detections(all_detections)

    def _nms_detections(
        self,
        detections: list,
        iou_threshold: float = 0.3,
    ) -> list:
        """非极大值抑制。"""
        if not detections:
            return []

        # 按置信度排序
        sorted_dets = sorted(
            detections, key=lambda d: d.get("confidence", 0), reverse=True
        )

        keep = []
        while sorted_dets:
            best = sorted_dets.pop(0)
            keep.append(best)

            filtered = []
            for det in sorted_dets:
                iou = self._compute_iou(best["bbox"], det["bbox"])
                if iou < iou_threshold:
                    filtered.append(det)
            sorted_dets = filtered

        return keep

    def _compute_iou(
        self,
        box1: tuple[int, int, int, int],
        box2: tuple[int, int, int, int],
    ) -> float:
        """计算 IOU。"""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        if x2 <= x1 or y2 <= y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0


class TileMultiScaleDetector:
    """分块 + 多尺度检测器。

    结合分块和多尺度检测，对大图像进行精细检测。
    """

    def __init__(
        self,
        tile_size: int = 640,
        tile_overlap: float = 0.2,
        scales: Optional[list[float]] = None,
    ) -> None:
        """初始化。

        Args:
            tile_size: 图块大小
            tile_overlap: 图块重叠
            scales: 缩放比例列表
        """
        from pcb_ai_inspector.utils.image_tiler import ImageTiler

        self.tiler = ImageTiler(
            tile_size=tile_size,
            overlap=tile_overlap,
        )
        self.multi_scale = MultiScaleDetector(scales=scales)

    def detect(
        self,
        image: np.ndarray,
        detect_fn: Callable[[np.ndarray], list],
    ) -> list:
        """分块 + 多尺度检测。

        Args:
            image: 输入图像
            detect_fn: 单图块检测函数

        Returns:
            检测结果列表
        """
        # 分块
        tiles = self.tiler.tile_image(image)

        if not tiles:
            return []

        # 对每个图块进行多尺度检测
        all_detections = []

        for tile in tiles:
            # 多尺度检测
            results = self.multi_scale.detect_at_scales(
                tile.image,
                detect_fn,
            )

            # 合并多尺度结果
            merged = self.multi_scale.merge_results(results)

            # 转换坐标到原图
            for det in merged:
                x1, y1, x2, y2 = det["bbox"]
                det["bbox"] = (
                    x1 + tile.x,
                    y1 + tile.y,
                    x2 + tile.x,
                    y2 + tile.y,
                )
                det["tile_index"] = tile.tile_index
                all_detections.append(det)

        # 最终 NMS
        return self.multi_scale._nms_detections(all_detections)


if __name__ == "__main__":
    # 测试多尺度检测器
    import cv2

    # 创建测试图像
    test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)

    detector = MultiScaleDetector(scales=[0.5, 1.0, 2.0])

    # 模拟检测函数
    def mock_detect(img):
        return []

    results = detector.detect_at_scales(test_image, mock_detect)

    print(f"多尺度检测完成，使用 {len(results)} 个尺度")
    for r in results:
        print(f"  Scale {r.scale}: {len(r.detections)} detections")
