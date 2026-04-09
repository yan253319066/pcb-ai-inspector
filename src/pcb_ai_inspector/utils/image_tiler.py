"""
图像分块模块 - 将大图像分割为小图块进行检测。

用于检测小缺陷：将高分辨率图像分割为多个重叠的小块，
每个小块单独检测，最后合并结果。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class Tile:
    """单个图块。"""

    image: np.ndarray
    x: int  # 在原图中的 x 坐标
    y: int  # 在原图中的 y 坐标
    width: int
    height: int
    tile_index: int


@dataclass
class TileResult:
    """图块检测结果。"""

    tile_index: int
    detections: list  # 检测结果列表


class ImageTiler:
    """图像分块器。"""

    def __init__(
        self,
        tile_size: int = 640,
        overlap: float = 0.2,
        min_tile_size: int = 256,
    ) -> None:
        """初始化分块器。

        Args:
            tile_size: 图块目标尺寸（默认 640，与 YOLO 输入一致）
            overlap: 重叠比例（0.2 = 20% 重叠）
            min_tile_size: 最小图块尺寸
        """
        self.tile_size = tile_size
        self.overlap = overlap
        self.min_tile_size = min_tile_size

    def tile_image(self, image: np.ndarray) -> list[Tile]:
        """将图像分割为多个图块。

        Args:
            image: 输入图像

        Returns:
            图块列表
        """
        h, w = image.shape[:2]

        # 计算步长（有重叠）
        step = int(self.tile_size * (1 - self.overlap))

        tiles = []
        index = 0
        y = 0

        while y < h:
            x = 0
            while x < w:
                # 计算当前块边界
                tile_w = min(self.tile_size, w - x)
                tile_h = min(self.tile_size, h - y)

                # 裁剪图块
                tile_img = image[y : y + tile_h, x : x + tile_w]

                # 确保图块足够大
                if tile_w >= self.min_tile_size and tile_h >= self.min_tile_size:
                    tiles.append(
                        Tile(
                            image=tile_img,
                            x=x,
                            y=y,
                            width=tile_w,
                            height=tile_h,
                            tile_index=index,
                        )
                    )
                    index += 1

                x += step

            y += step

        return tiles

    def merge_detections(
        self,
        tiles: list[Tile],
        tile_results: list[TileResult],
        original_size: tuple[int, int],
    ) -> list:
        """合并所有图块的检测结果。

        Args:
            tiles: 图块列表
            tile_results: 每个图块的检测结果
            original_size: 原始图像尺寸 (height, width)

        Returns:
            合并后的检测结果列表
        """
        all_detections = []

        for tile, result in zip(tiles, tile_results):
            for det in result.detections:
                # 转换坐标到原始图像坐标系
                # 假设检测结果是相对于图块的 (x1, y1, x2, y2)
                if hasattr(det, "bbox"):
                    x1, y1, x2, y2 = det.bbox
                    # 添加图块偏移量
                    new_bbox = (
                        x1 + tile.x,
                        y1 + tile.y,
                        x2 + tile.x,
                        y2 + tile.y,
                    )
                    # 创建新的检测结果（需要根据实际检测结果类型调整）
                    merged_det = {
                        "label": det.label,
                        "confidence": det.confidence,
                        "bbox": new_bbox,
                        "tile_index": tile.tile_index,
                    }
                    all_detections.append(merged_det)

        # NMS 去除重复检测
        return self._nms_detections(all_detections, iou_threshold=0.3)

    def _nms_detections(
        self,
        detections: list,
        iou_threshold: float = 0.3,
    ) -> list:
        """非极大值抑制，去除重复检测。

        Args:
            detections: 检测结果列表
            iou_threshold: IOU 阈值

        Returns:
            去重后的检测结果
        """
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

            # 移除与最佳检测重叠度高的
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
        """计算两个框的 IOU。

        Args:
            box1, box2: (x1, y1, x2, y2)

        Returns:
            IOU 值
        """
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


def create_tiler(
    image_size: int = 640,
    overlap: float = 0.2,
) -> ImageTiler:
    """创建分块器的工厂函数。

    Args:
        image_size: 图块尺寸
        overlap: 重叠比例

    Returns:
        ImageTiler 实例
    """
    return ImageTiler(
        tile_size=image_size,
        overlap=overlap,
    )


if __name__ == "__main__":
    # 测试分块
    import cv2

    # 创建测试图像
    test_image = np.random.randint(0, 255, (1200, 1600, 3), dtype=np.uint8)

    tiler = ImageTiler(tile_size=640, overlap=0.2)
    tiles = tiler.tile_image(test_image)

    print(f"图像尺寸: {test_image.shape}")
    print(f"分割为 {len(tiles)} 个图块")

    for tile in tiles[:5]:
        print(
            f"  Tile {tile.tile_index}: pos=({tile.x}, {tile.y}), size={tile.width}x{tile.height}"
        )
