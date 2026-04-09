"""
PCB AI Inspector 缺陷可视化覆盖层。

提供带有边界框、颜色编码和标签的缺陷检测注释渲染。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import (
    QImage,
    QPixmap,
    QPainter,
    QPen,
    QBrush,
    QColor,
    QFont,
    QTransform,
)
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem

from ..core.defect_types import DefectType, DEFECT_COLORS, DEFECT_LABELS


@dataclass
class DetectionResult:
    """
    模型输出的单个检测结果。

    Attributes:
        bbox: 边界框 [x1, y1, x2, y2] 格式（像素坐标）
        confidence: 检测置信度（0.0 到 1.0）
        defect_type: Type of defect detected
        class_id: Class ID from the model
    """

    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2
    confidence: float
    defect_type: DefectType
    class_id: int

    @property
    def x1(self) -> float:
        """Get x1 coordinate."""
        return self.bbox[0]

    @property
    def y1(self) -> float:
        """Get y1 coordinate."""
        return self.bbox[1]

    @property
    def x2(self) -> float:
        """Get x2 coordinate."""
        return self.bbox[2]

    @property
    def y2(self) -> float:
        """Get y2 coordinate."""
        return self.bbox[3]

    @property
    def width(self) -> float:
        """Get bounding box width."""
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        """Get bounding box height."""
        return self.y2 - self.y1

    @property
    def area(self) -> float:
        """Get bounding box area."""
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        """Get center point."""
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "bbox": self.bbox,
            "confidence": self.confidence,
            "defect_type": self.defect_type.value,
            "class_id": self.class_id,
            "label": self.defect_type.display_name,
        }


class DetectionOverlay(QGraphicsView):
    """
    Graphics view for rendering detection overlays on images.

    Renders bounding boxes, labels, and confidence scores
    on top of the source image.
    """

    zoom_changed = pyqtSignal(float)
    selection_changed = pyqtSignal(object)  # Optional[DetectionResult]

    def __init__(self, parent: Optional[QGraphicsView] = None) -> None:
        """初始化覆盖层视图。"""
        super().__init__(parent)

        # 场景设置
        self._scene = DetectionScene(None)  # 场景不需要父级，由此视图拥有
        self.setScene(self._scene)

        # 图像
        self._source_image: Optional[np.ndarray] = None
        self._pixmap_item: Optional[QGraphicsPixmapItem] = None

        # 检测结果
        self._detections: list[DetectionResult] = []
        self._selected_detection: Optional[DetectionResult] = None

        # 渲染选项
        self._show_boxes = True
        self._show_labels = True
        self._show_confidence = True
        self._show_confidence_threshold = 0.0  # 默认显示全部

        # 视图设置
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setBackgroundBrush(QColor("#2b2b2b"))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def set_image(self, image: np.ndarray) -> None:
        """
        Set the source image for overlay.

        Args:
            image: Image as numpy array in BGR format
        """
        self._source_image = image
        self._scene.set_image(image)
        self._update_pixmap()

    def set_detections(self, detections: list[DetectionResult]) -> None:
        """
        Set detection results to display.

        Args:
            detections: List of DetectionResult objects
        """
        self._detections = detections
        self._scene.set_detections(detections)
        self._update_overlay()

    def clear(self) -> None:
        """Clear the view."""
        self._source_image = None
        self._detections.clear()
        self._selected_detection = None
        self._scene.clear()
        self.update()

    @property
    def detections(self) -> list[DetectionResult]:
        """Get current detections."""
        return self._detections

    @property
    def selected_detection(self) -> Optional[DetectionResult]:
        """Get currently selected detection."""
        return self._selected_detection

    def set_show_boxes(self, show: bool) -> None:
        """Toggle bounding box visibility."""
        self._show_boxes = show
        self._update_overlay()

    def set_show_labels(self, show: bool) -> None:
        """Toggle label visibility."""
        self._show_labels = show
        self._update_overlay()

    def set_show_confidence(self, show: bool) -> None:
        """Toggle confidence score visibility."""
        self._show_confidence = show
        self._update_overlay()

    def set_confidence_threshold(self, threshold: float) -> None:
        """Set minimum confidence to display."""
        self._show_confidence_threshold = threshold
        self._update_overlay()

    def _update_pixmap(self) -> None:
        """Update the base pixmap from source image."""
        if self._source_image is None:
            return

        rgb = cv2.cvtColor(self._source_image, cv2.COLOR_BGR2RGB)
        h, w, _ = rgb.shape
        q_image = QImage(rgb.data, w, h, w * 3, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)

        self._scene.clear()
        self._pixmap_item = self._scene.addPixmap(pixmap)
        # 重新设置检测结果
        if self._detections:
            self._scene.set_detections(self._detections)
            self._update_overlay()
        # 重置缩放级别为1.0，保持100%缩放
        self._zoom_level = 1.0
        self.zoom_changed.emit(self._zoom_level)

    def fit_in_view(self, rect: Optional[QRectF] = None) -> None:
        """
        Fit the view to show the scene contents.

        Args:
            rect: Optional rectangle to fit in view. If None, fits the entire scene.
        """
        if rect is None:
            rect = self._scene.sceneRect()

        if rect is not None and rect.isValid():
            self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    # Zoom constraints
    MIN_ZOOM = 0.1
    MAX_ZOOM = 10.0
    ZOOM_STEP = 0.1

    # Zoom state
    _zoom_level: float = 1.0

    def zoom_in(self) -> None:
        """Zoom in by one step."""
        self._set_zoom(self._zoom_level + self.ZOOM_STEP)

    def zoom_out(self) -> None:
        """Zoom out by one step."""
        self._set_zoom(self._zoom_level - self.ZOOM_STEP)

    def zoom_fit(self) -> None:
        """Fit image in view."""
        self.fit_in_view()
        self._update_zoom_from_transform()

    def zoom_100(self) -> None:
        """Set zoom to 100%."""
        self._set_zoom(1.0)

    @property
    def zoom_level(self) -> float:
        """Get current zoom level."""
        return self._zoom_level

    def _set_zoom(self, level: float) -> None:
        """Set zoom level with constraints."""
        self._zoom_level = max(self.MIN_ZOOM, min(self.MAX_ZOOM, level))
        self.zoom_changed.emit(self._zoom_level)
        self.update()

    def _update_zoom_from_transform(self) -> None:
        """Update zoom level from current transform."""
        transform = self.transform()
        self._zoom_level = transform.m11()
        self._zoom_level = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self._zoom_level))
        self.zoom_changed.emit(self._zoom_level)

    def wheelEvent(self, event) -> None:
        """Handle mouse wheel for zooming."""
        if event is None:
            return
        modifiers = event.modifiers()
        if modifiers is not None and modifiers == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def _update_overlay(self) -> None:
        """Update the overlay rendering."""
        self._scene.update_overlay(
            show_boxes=self._show_boxes,
            show_labels=self._show_labels,
            show_confidence=self._show_confidence,
            confidence_threshold=self._show_confidence_threshold,
        )
        self.update()


class DetectionScene(QGraphicsScene):
    """Graphics scene for detection overlay rendering."""

    def __init__(self, parent: Optional[QGraphicsScene] = None) -> None:
        """Initialize the detection scene."""
        super().__init__(parent)
        self._source_image: Optional[np.ndarray] = None
        self._detections: list[DetectionResult] = []
        self._pixmap_item: Optional[QGraphicsPixmapItem] = None

        # Rendering options
        self._show_boxes = True
        self._show_labels = True
        self._show_confidence = True
        self._confidence_threshold = 0.0

        # Font for labels
        self._font = QFont("Arial", 10, QFont.Weight.Bold)

    def set_image(self, image: np.ndarray) -> None:
        """Set the source image."""
        self._source_image = image

    def set_detections(self, detections: list[DetectionResult]) -> None:
        """Set detection results."""
        self._detections = detections

    def clear(self) -> None:
        """Clear the scene."""
        super().clear()
        self._pixmap_item = None

    def update_overlay(
        self,
        show_boxes: bool = True,
        show_labels: bool = True,
        show_confidence: bool = True,
        confidence_threshold: float = 0.0,
    ) -> None:
        """Update overlay rendering options."""
        self._show_boxes = show_boxes
        self._show_labels = show_labels
        self._show_confidence = show_confidence
        self._confidence_threshold = confidence_threshold
        self.update()

    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:
        """Draw the foreground (detections) on top of the image."""
        if self._source_image is None:
            super().drawForeground(painter, rect)
            return

        # Draw detections on top of the image
        self._draw_detections(painter)

    def _draw_detections(self, painter: QPainter) -> None:
        """Draw all detection bounding boxes."""
        for detection in self._detections:
            # Filter by confidence threshold
            if detection.confidence < self._confidence_threshold:
                continue

            # Get color for defect type
            color_rgb = DEFECT_COLORS.get(detection.defect_type, (255, 255, 255))
            color = QColor(*color_rgb)

            x1, y1, x2, y2 = detection.bbox

            # Draw bounding box
            if self._show_boxes:
                pen = QPen(color, 2)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(int(x1), int(y1), int(x2 - x1), int(y2 - y1))

            # Draw label background
            if self._show_labels:
                label_parts = []

                # Add defect type label
                label = DEFECT_LABELS.get(
                    detection.defect_type, detection.defect_type.value
                )
                label_parts.append(label)

                # Add confidence if enabled
                if self._show_confidence:
                    conf_text = f"{detection.confidence:.0%}"
                    label_parts.append(conf_text)

                full_label = " ".join(label_parts)

                # Calculate label size
                painter.setFont(self._font)
                text_width = painter.fontMetrics().horizontalAdvance(full_label)
                text_height = painter.fontMetrics().height()

                # Label background position (above the box)
                label_x = int(x1)
                label_y = int(y1) - text_height - 4

                # Ensure label stays within image bounds
                if label_y < 0:
                    label_y = int(y1)

                # Draw label background
                bg_rect = QRectF(
                    label_x - 2,
                    label_y - 2,
                    text_width + 4,
                    text_height + 4,
                )
                painter.fillRect(bg_rect, color)

                # Draw label text
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(
                    QPointF(label_x, label_y + text_height - 2),
                    full_label,
                )

                # Reset pen
                painter.setPen(QPen(color, 2))


def draw_detections_on_image(
    image: np.ndarray,
    detections: list[DetectionResult],
    show_labels: bool = True,
    show_confidence: bool = True,
) -> np.ndarray:
    """
    Draw detection bounding boxes on an image (returns a copy).

    Args:
        image: Source image in BGR format
        detections: List of DetectionResult objects
        show_labels: Whether to show defect type labels
        show_confidence: Whether to show confidence scores

    Returns:
        Image with drawn detections (BGR format)
    """
    from PIL import Image, ImageDraw, ImageFont

    # 转换为 PIL Image 进行中文绘制
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(rgb)
    draw = ImageDraw.Draw(pil_image)

    # 尝试加载中文字体
    try:
        # Windows 系统字体路径
        font_path = "C:/Windows/Fonts/simhei.ttf"  # 黑体
        font = ImageFont.truetype(font_path, 16)
    except Exception:
        # 回退到默认字体
        font = ImageFont.load_default()

    for detection in detections:
        # Get color
        color_rgb = DEFECT_COLORS.get(detection.defect_type, (255, 255, 255))

        x1, y1, x2, y2 = map(int, detection.bbox)

        # 绘制边界框 (使用 PIL)
        draw.rectangle([(x1, y1), (x2, y2)], outline=color_rgb, width=2)

        if show_labels:
            # Build label
            label_parts = []
            label = DEFECT_LABELS.get(
                detection.defect_type, detection.defect_type.value
            )
            label_parts.append(label)

            if show_confidence:
                label_parts.append(f"{detection.confidence:.0%}")

            label_text = " ".join(label_parts)

            # 计算文本大小
            bbox = draw.textbbox((0, 0), label_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # 绘制标签背景
            label_y = y1 - text_height - 4 if y1 > text_height + 10 else y2 + 4
            draw.rectangle(
                [(x1, label_y), (x1 + text_width + 4, label_y + text_height + 2)],
                fill=color_rgb,
            )

            # 绘制文本
            draw.text((x1 + 2, label_y), label_text, fill=(255, 255, 255), font=font)

    # 转换回 OpenCV 格式
    result_rgb = np.array(pil_image)
    result = cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR)

    return result
