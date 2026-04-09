"""
PCB AI Inspector 图像查看器模块。

提供可缩放、可平移的图像显示，支持
覆盖层注释（边界框、缺陷标记）。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import cv2
import numpy as np
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QTransform
from PyQt6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QStyleOptionGraphicsItem,
)


class ImageViewer(QGraphicsView):
    """可缩放、可平移的图像查看器小部件。"""

    # 信号
    zoom_changed = pyqtSignal(float)  # 当前缩放级别
    mouse_position_changed = pyqtSignal(QPointF)  # 图像坐标中的鼠标位置

    # 缩放约束
    MIN_ZOOM = 0.1
    MAX_ZOOM = 10.0
    ZOOM_STEP = 0.1

    def __init__(self, parent: Optional[QGraphicsView] = None) -> None:
        """初始化图像查看器。"""
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        # 图像处理
        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._current_image: Optional[np.ndarray] = None
        self._image_shape: tuple[int, int] = (0, 0)  # (height, width)

        # 视图状态
        self._zoom_level = 1.0
        self._is_panning = False
        self._pan_start = QPointF()

        # 注释层
        self._annotations: list[AnnotationItem] = []
        self._show_annotations = True

        # 设置视图
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        # 背景
        self.setBackgroundBrush(QColor("#2b2b2b"))

    def load_image(self, image: np.ndarray) -> None:
        """
        加载 numpy 数组图像（BGR 格式）。

        Args:
            image: BGR 格式的 numpy 数组图像
        """
        self._current_image = image
        self._image_shape = (image.shape[0], image.shape[1])

        # 转换为 RGB 用于 Qt
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        height, width, channels = rgb_image.shape
        bytes_per_line = channels * width

        # 创建 QImage
        q_image = QImage(
            rgb_image.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888,
        )
        pixmap = QPixmap.fromImage(q_image)

        # 清除场景并添加新的像素图
        self._scene.clear()
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(0, 0, width, height)

        # 添加注释
        for annotation in self._annotations:
            self._scene.addItem(annotation)

        # 重置视图
        self._zoom_level = 1.0
        self.zoom_changed.emit(self._zoom_level)
        # 不调用 fit_in_view()，保持100%缩放
        self.update()

    def clear(self) -> None:
        """清除当前图像。"""
        self._current_image = None
        self._image_shape = (0, 0)
        self._scene.clear()
        self._pixmap_item = None
        self._annotations.clear()
        self._zoom_level = 1.0
        self.zoom_changed.emit(self._zoom_level)

    @property
    def current_image(self) -> Optional[np.ndarray]:
        """获取当前图像数组。"""
        return self._current_image

    @property
    def image_shape(self) -> tuple[int, int]:
        """获取当前图像形状（高度，宽度）。"""
        return self._image_shape

    def set_annotations(self, annotations: list[AnnotationItem]) -> None:
        """
        设置要显示的注释项目。

        Args:
            annotations: AnnotationItem 对象列表
        """
        # 从场景中移除旧注释
        for ann in self._annotations:
            self._scene.removeItem(ann)

        self._annotations = annotations

        # 向场景添加新注释
        for ann in self._annotations:
            self._scene.addItem(ann)

        self.update()

    def clear_annotations(self) -> None:
        """Remove all annotations from display."""
        for ann in self._annotations:
            self._scene.removeItem(ann)
        self._annotations.clear()
        self.update()

    def set_show_annotations(self, show: bool) -> None:
        """Toggle annotation visibility."""
        self._show_annotations = show
        for ann in self._annotations:
            ann.setVisible(show)
        self.update()

    @property
    def zoom_level(self) -> float:
        """Get current zoom level."""
        return self._zoom_level

    def zoom_in(self) -> None:
        """Zoom in by one step."""
        self._set_zoom(self._zoom_level + self.ZOOM_STEP)

    def zoom_out(self) -> None:
        """Zoom out by one step."""
        self._set_zoom(self._zoom_level - self.ZOOM_STEP)

    def zoom_fit(self) -> None:
        """Fit image in view."""
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._update_zoom_from_transform()

    def zoom_100(self) -> None:
        """Set zoom to 100%."""
        self._set_zoom(1.0)

    def fit_in_view(self) -> None:
        """Fit image in view (convenience method)."""
        if self._scene.sceneRect().isValid():
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _set_zoom(self, level: float) -> None:
        """Set zoom level with constraints."""
        self._zoom_level = max(self.MIN_ZOOM, min(self.MAX_ZOOM, level))
        self.zoom_changed.emit(self._zoom_level)
        self.update()

    def _update_zoom_from_transform(self) -> None:
        """从当前变换更新缩放级别。"""
        transform = self.transform()
        # 变换矩阵的缩放因子
        self._zoom_level = transform.m11()
        self._zoom_level = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self._zoom_level))
        self.zoom_changed.emit(self._zoom_level)

    # 鼠标滚轮：缩放
    def wheelEvent(self, event) -> None:
        """处理鼠标滚轮缩放。"""
        if event is None:
            return
        modifiers = event.modifiers()
        if modifiers is not None and modifiers == Qt.KeyboardModifier.ControlModifier:
            # 使用 Ctrl+滚轮 缩放
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            # 正常滚动
            super().wheelEvent(event)

    # 鼠标事件用于平移
    def mousePressEvent(self, event) -> None:
        """处理鼠标按下进行平移。"""
        if event is None:
            return
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton:
            modifiers = event.modifiers()
            if modifiers is not None and modifiers == Qt.KeyboardModifier.ShiftModifier:
                # Shift+左键 平移模式
                self._is_panning = True
                self._pan_start = event.pos()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                event.accept()
            else:
                super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """处理鼠标移动进行平移。"""
        if event is None:
            return
        if self._is_panning:
            # event.pos() 返回 QPoint，使用 toPointF() 转换为 QPointF
            current_pos = event.pos().toPointF()
            delta_x = int(current_pos.x() - self._pan_start.x())
            delta_y = int(current_pos.y() - self._pan_start.y())
            self._pan_start = current_pos
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta_x
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta_y
            )
            event.accept()
        else:
            # 在图像坐标中发出鼠标位置
            pos = self.mapToScene(event.pos())
            self.mouse_position_changed.emit(pos)
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release."""
        if event is None:
            return
        if event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.LeftButton):
            if self._is_panning:
                self._is_panning = False
                self.setCursor(Qt.CursorShape.ArrowCursor)
                event.accept()
            else:
                super().mouseReleaseEvent(event)
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        """Handle keyboard shortcuts."""
        if event is None:
            return
        modifiers = event.modifiers()
        if modifiers is not None and modifiers == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_0:  # Ctrl+0: Fit
                self.zoom_fit()
                event.accept()
            elif event.key() == Qt.Key.Key_1:  # Ctrl+1: 100%
                self.zoom_100()
                event.accept()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)


class AnnotationType(Enum):
    """Types of annotations."""

    BOUNDING_BOX = "bounding_box"
    """Rectangle bounding box."""

    POLYGON = "polygon"
    """Polygon outline."""

    POINT = "point"
    """Single point marker."""

    LINE = "line"
    """Line segment."""


@dataclass
class AnnotationItem(QGraphicsPixmapItem):
    """
    Graphics item for annotations on the image.

    Can represent bounding boxes, polygons, points, etc.
    """

    annotation_type: AnnotationType
    coordinates: list[tuple[float, float]]  # List of (x, y) points
    color: QColor
    line_width: int = 2
    label: Optional[str] = None
    confidence: Optional[float] = None

    def __post_init__(self) -> None:
        """Initialize the annotation item."""
        # Initialize as invisible by default, added to scene separately
        self.setVisible(False)
        self.setZValue(1.0)  # Above the image

    def paint(
        self,
        painter: QPainter,
        option: "QStyleOptionGraphicsItem",  # noqa: F821
        widget: Optional[QGraphicsPixmapItem] = None,
    ) -> None:
        """
        Paint the annotation.

        This is called by Qt's graphics system. We don't paint anything here
        because annotations are rendered in the overlay layer.
        """
        pass

    def boundingRect(self) -> QRectF:
        """Return bounding rectangle."""
        if not self.coordinates:
            return QRectF()
        xs = [c[0] for c in self.coordinates]
        ys = [c[1] for c in self.coordinates]
        return QRectF(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
