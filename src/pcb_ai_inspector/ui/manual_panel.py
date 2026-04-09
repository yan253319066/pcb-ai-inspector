"""
PCB AI Inspector 手动检测面板模块。

提供手动检测界面的完整面板组件，包括：
- 原始图像与标记图像双面板
- 检测设置（置信度、设备）
- 显示设置（缩放、边界框、标签）
- 检测结果列表和统计信息
- 拖拽导入支持
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from PyQt6 import QtCore
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QDragMoveEvent
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QGroupBox,
    QLabel,
    QPushButton,
    QComboBox,
    QSlider,
    QDoubleSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QCheckBox,
)

from ..core.settings import get_settings_manager
from ..models.detector import YOLODetector
from ..utils.device import get_device_info
from .defect_overlay import DetectionOverlay, DetectionResult
from .defect_list import DefectListWidget, StatisticsWidget
from .detection_result_handler import DetectionResultHandler
from .image_viewer import ImageViewer


class ManualDetectionPanel(QWidget):
    """
    手动检测面板组件。

    包含图像查看器、检测设置、结果显示的完整界面。
    支持拖拽导入图像文件。

    Signals:
        image_selected: 选中结果表格中的一行 (image_path: str, detections: list, marked_image: np.ndarray)
        zoom_changed: 缩放级别改变 (zoom_level: float)
        detect_requested: 用户点击检测按钮
    """

    # 信号定义
    image_selected = pyqtSignal(str, list, object)  # path, detections, marked_image
    zoom_changed = pyqtSignal(float)
    detect_requested = pyqtSignal()
    cancel_requested = pyqtSignal()  # 取消检测
    files_dropped = pyqtSignal(list)  # 拖拽文件信号
    open_file_requested = pyqtSignal()  # 请求打开文件
    open_folder_requested = pyqtSignal()  # 请求打开文件夹
    report_requested = pyqtSignal()  # 请求生成报告
    history_requested = pyqtSignal()  # 请求查看历史

    def __init__(
        self,
        detector: Optional[YOLODetector] = None,
        result_handler: Optional[DetectionResultHandler] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """初始化手动检测面板。"""
        super().__init__(parent)

        self._detector = detector
        self._result_handler = result_handler or DetectionResultHandler()
        self._device_info = get_device_info()

        # 存储结果的字典 {image_path: {'detections': [], 'marked_image': np.ndarray, 'image': np.ndarray}}
        self._all_results: dict[str, dict] = {}

        # 启用拖拽
        self.setAcceptDrops(True)

        # 初始化UI
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置用户界面。"""
        # 主分割器（垂直）
        self._main_splitter = QSplitter(Qt.Orientation.Vertical)

        # 上半部分：水平分割器（原始图 | 标记图）
        image_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左：原始图像面板
        left_panel = self._create_image_panel("原始图像")
        image_splitter.addWidget(left_panel)

        # 右：检测结果面板
        right_panel = self._create_image_panel("检测结果", is_result=True)
        image_splitter.addWidget(right_panel)

        image_splitter.setStretchFactor(0, 1)
        image_splitter.setStretchFactor(1, 1)
        self._main_splitter.addWidget(image_splitter)

        # 下半部分：控制面板
        control_panel = self._create_right_panel()
        self._main_splitter.addWidget(control_panel)

        # 设置分割器比例
        settings = get_settings_manager().settings
        self._main_splitter.setStretchFactor(
            0, int(settings.ui_layout.image_panel_ratio * 10)
        )
        self._main_splitter.setStretchFactor(
            1, int(settings.ui_layout.control_panel_ratio * 10)
        )

        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._main_splitter)

    def _create_image_panel(self, title: str, is_result: bool = False) -> QWidget:
        """创建图像查看面板（带标题）。"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)

        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; color: #888; padding: 4px;")
        layout.addWidget(title_label)

        # 图像查看器
        if is_result:
            self._image_viewer_marked = DetectionOverlay()
            layout.addWidget(self._image_viewer_marked)
        else:
            self._image_viewer_original = ImageViewer()
            self._image_viewer_original.zoom_changed.connect(
                self._on_viewer_zoom_changed
            )
            layout.addWidget(self._image_viewer_original)

        return panel

    def _create_right_panel(self) -> QWidget:
        """创建右侧面板，显示检测结果。"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 使用水平分割：左-检测设置，右-结果列表+详情
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：检测设置
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # 检测设置
        settings_group = QGroupBox("检测设置")
        settings_layout = QHBoxLayout(settings_group)

        settings_layout.addWidget(QLabel("置信度:"))
        self._confidence_spin = QDoubleSpinBox()
        self._confidence_spin.setRange(0.0, 1.0)
        self._confidence_spin.setSingleStep(0.05)
        settings_mgr = get_settings_manager()
        self._confidence_spin.setValue(
            settings_mgr.settings.detection.confidence_threshold
        )
        self._confidence_spin.setMaximumWidth(100)
        settings_layout.addWidget(self._confidence_spin)
        # 置信度变化时自动保存
        self._confidence_spin.valueChanged.connect(self._on_confidence_changed)

        # 添加问号图标显示置信度提示
        confidence_help = QLabel("⚠")
        confidence_help.setToolTip(
            "<b>置信度说明</b><br>"
            "• 0.25-0.35: 常规检测（推荐）<br>"
            "• 0.1-0.2: 更敏感<br>"
            "• 0.4-0.5: 高置信度"
        )
        confidence_help.setStyleSheet("color: #666;")
        settings_layout.addWidget(confidence_help)

        settings_layout.addWidget(QLabel("设备:"))
        device_name = self._device_info.device_name or "CPU"
        device_label = QLabel(device_name)
        device_label.setStyleSheet("font-weight: bold;")
        settings_layout.addWidget(device_label)

        settings_layout.addStretch()

        # 打开按钮 - 支持文件和文件夹
        self._open_btn = QPushButton("📂 打开")
        self._open_btn.setMinimumWidth(80)
        self._open_btn.clicked.connect(self._on_open_clicked)
        settings_layout.addWidget(self._open_btn)

        self._detect_btn = QPushButton("🔍 检测")
        self._detect_btn.setMinimumWidth(70)
        self._detect_btn.clicked.connect(self.detect_requested.emit)
        settings_layout.addWidget(self._detect_btn)

        self._cancel_btn = QPushButton("⏹ 停止")
        self._cancel_btn.setMinimumWidth(70)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self.cancel_requested.emit)
        settings_layout.addWidget(self._cancel_btn)

        self._report_btn = QPushButton("📊 报告")
        self._report_btn.setMinimumWidth(70)
        self._report_btn.clicked.connect(self.report_requested.emit)
        settings_layout.addWidget(self._report_btn)

        self._history_btn = QPushButton("📜 历史")
        self._history_btn.setMinimumWidth(70)
        self._history_btn.clicked.connect(self.history_requested.emit)
        settings_layout.addWidget(self._history_btn)

        left_layout.addWidget(settings_group)

        # 显示设置（缩放+显示选项）
        display_group = QGroupBox("显示设置")
        display_layout = QHBoxLayout(display_group)

        display_layout.addWidget(QLabel("缩放:"))
        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setMinimum(10)
        self._zoom_slider.setMaximum(500)
        self._zoom_slider.setValue(100)
        self._zoom_slider.setMaximumWidth(120)
        self._zoom_slider.valueChanged.connect(self._on_zoom_changed)
        display_layout.addWidget(self._zoom_slider)
        self._zoom_label = QLabel("100%")
        display_layout.addWidget(self._zoom_label)

        display_layout.addStretch()

        self._show_boxes_check = self._create_checkbox("边界框", True)
        self._show_boxes_check.toggled.connect(self._on_show_boxes_toggled)
        display_layout.addWidget(self._show_boxes_check)

        self._show_labels_check = self._create_checkbox("标签", True)
        self._show_labels_check.toggled.connect(self._on_show_labels_toggled)
        display_layout.addWidget(self._show_labels_check)

        left_layout.addWidget(display_group)

        # 统计信息
        self._stats_widget = StatisticsWidget()
        left_layout.addWidget(self._stats_widget)

        left_layout.addStretch()

        # 右侧：结果列表 + 缺陷列表
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 检测结果列表（统一表格）
        results_group = QGroupBox("检测结果")
        results_layout = QVBoxLayout(results_group)

        self._results_table = QTableWidget()
        self._results_table.setColumnCount(4)
        self._results_table.setHorizontalHeaderLabels(
            ["文件名", "缺陷数", "置信度", "状态"]
        )
        self._results_table.setAlternatingRowColors(True)
        self._results_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._results_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._results_table.horizontalHeader().setStretchLastSection(True)
        self._results_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._results_table.itemSelectionChanged.connect(self._on_result_selected)
        results_layout.addWidget(self._results_table)

        right_layout.addWidget(results_group)

        # 缺陷列表
        defect_list_group = QGroupBox("缺陷列表")
        defect_list_layout = QVBoxLayout(defect_list_group)

        self._defect_list = DefectListWidget()
        self._defect_list.detection_selected.connect(self._on_detection_selected)
        defect_list_layout.addWidget(self._defect_list)

        right_layout.addWidget(defect_list_group)

        # 添加到分割器
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)

        return panel

    def _create_checkbox(self, text: str, checked: bool = True) -> QCheckBox:
        """创建一个带样式的复选框。"""
        checkbox = QCheckBox(text)
        checkbox.setChecked(checked)
        return checkbox

    def _on_result_selected(self) -> None:
        """处理结果行选择。"""
        selected_rows = self._results_table.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        image_name = self._results_table.item(row, 0).text()

        # 查找匹配的图像（通过文件名）
        matched_key = None
        for key in self._all_results:
            if Path(key).name == image_name:
                matched_key = key
                break

        if matched_key and matched_key in self._all_results:
            result = self._all_results[matched_key]
            detections = result.get("detections", [])
            marked_image = result.get("marked_image")

            # 更新缺陷列表和统计
            self._defect_list.set_detections(detections)
            self._stats_widget.update_statistics(detections)

            # 显示原始图像
            original_image = result.get("image")
            if original_image is not None:
                self._image_viewer_original.load_image(original_image)

            # 显示带标记的图像
            if marked_image is not None:
                self._image_viewer_marked.set_image(marked_image)
                self._image_viewer_marked.set_detections(detections)

            # 发送信号
            self.image_selected.emit(matched_key, detections, marked_image)

    def _on_detection_selected(self, row: int) -> None:
        """处理检测结果选择。"""
        detection = self._defect_list.get_selected_detection()
        if detection:
            pass  # 可用于在图像查看器中高亮显示

    def _on_zoom_changed(self, value: int) -> None:
        """处理缩放滑块变化。"""
        zoom_factor = value / 100.0
        self._image_viewer_original.resetTransform()
        self._image_viewer_original.scale(zoom_factor, zoom_factor)
        self._image_viewer_marked.resetTransform()
        self._image_viewer_marked.scale(zoom_factor, zoom_factor)
        self._zoom_label.setText(f"{value}%")
        self.zoom_changed.emit(zoom_factor)

    def _on_viewer_zoom_changed(self, zoom_level: float) -> None:
        """处理查看器缩放变化（同步缩放滑块）。"""
        value = int(zoom_level * 100)
        self._zoom_slider.blockSignals(True)
        self._zoom_slider.setValue(value)
        self._zoom_slider.blockSignals(False)
        self._zoom_label.setText(f"{value}%")
        self.zoom_changed.emit(zoom_level)

    def _on_show_boxes_toggled(self, checked: bool) -> None:
        """处理显示边界框切换。"""
        self._image_viewer_marked.set_show_boxes(checked)

    def _on_show_labels_toggled(self, checked: bool) -> None:
        """处理显示标签切换。"""
        self._image_viewer_marked.set_show_labels(checked)

    # ==================== 公开方法 ====================

    def set_detector(self, detector: Optional[YOLODetector]) -> None:
        """设置检测器引用。"""
        self._detector = detector

    def set_result_handler(self, handler: Optional[DetectionResultHandler]) -> None:
        """设置结果处理器。"""
        if handler:
            self._result_handler = handler

    def load_image(self, image_path: Path, image: np.ndarray) -> None:
        """加载并显示图像。"""
        # 显示原始图像
        self._image_viewer_original.load_image(image)

        # 清空标记图像
        self._image_viewer_marked.clear()

        # 清空缺陷列表
        self._defect_list.clear()
        self._stats_widget.update_statistics([])

    def display_detections(
        self,
        image_path: Path,
        detections: list[DetectionResult],
        marked_image: np.ndarray,
    ) -> None:
        """显示检测结果。"""
        # 显示带标记的图像
        self._image_viewer_marked.set_image(marked_image)
        self._image_viewer_marked.set_detections(detections)

        # 存储结果
        image_key = str(image_path)
        self._all_results[image_key] = {
            "detections": detections,
            "marked_image": marked_image,
            "image": marked_image,  # 使用原始图像，由 DetectionOverlay 处理渲染
        }

        # 添加到结果表格
        self.add_result_to_table(image_path.name, detections)

        # 默认选中第一行
        if self._results_table.rowCount() > 0:
            self._results_table.selectRow(0)

    def add_result_to_table(
        self, image_name: str, detections: list[DetectionResult]
    ) -> None:
        """将检测结果添加到结果表格。"""
        row = self._results_table.rowCount()
        self._results_table.insertRow(row)

        # 文件名
        self._results_table.setItem(row, 0, QTableWidgetItem(image_name))

        # 缺陷数量
        self._results_table.setItem(row, 1, QTableWidgetItem(str(len(detections))))

        # 平均置信度
        if detections:
            avg_conf = sum(d.confidence for d in detections) / len(detections)
            self._results_table.setItem(row, 2, QTableWidgetItem(f"{avg_conf:.0%}"))
        else:
            self._results_table.setItem(row, 2, QTableWidgetItem("-"))

        # 状态
        status = "✓" if detections else "无缺陷"
        self._results_table.setItem(row, 3, QTableWidgetItem(status))

    def set_results(self, results_dict: dict[str, dict]) -> None:
        """设置批量检测结果。"""
        self._all_results = results_dict.copy()

        # 清空表格
        self._results_table.setRowCount(0)

        # 添加所有结果
        for image_key, result in results_dict.items():
            image_path = Path(image_key)
            detections = result.get("detections", [])
            self.add_result_to_table(image_path.name, detections)

        # 选中第一行
        if self._results_table.rowCount() > 0:
            self._results_table.selectRow(0)
            self._on_result_selected()

    def get_all_results(self) -> dict[str, dict]:
        """获取所有检测结果。"""
        return self._all_results

    def get_confidence(self) -> float:
        """获取当前置信度设置。"""
        return self._confidence_spin.value()

    def _on_confidence_changed(self, value: float) -> None:
        """置信度变化时自动保存到设置。"""
        from ..core.settings import get_settings_manager

        settings_mgr = get_settings_manager()
        settings_mgr.set("detection.confidence_threshold", value)

    def clear_results(self) -> None:
        """清空所有结果。"""
        self._all_results.clear()
        self._image_viewer_original.clear()
        self._image_viewer_marked.clear()
        self._defect_list.clear()
        self._stats_widget.update_statistics([])
        self._results_table.setRowCount(0)

    def enable_detect_button(self, enabled: bool) -> None:
        """启用/禁用检测按钮。"""
        self._detect_btn.setEnabled(enabled)

    def set_detecting_state(self, is_detecting: bool) -> None:
        """设置检测状态（用于禁用UI）。"""
        self._confidence_spin.setEnabled(not is_detecting)
        self._detect_btn.setEnabled(not is_detecting)
        self._cancel_btn.setEnabled(is_detecting)

    # ===== 拖拽导入支持 =====

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """拖拽进入事件。"""
        if event.mimeData().hasUrls():
            # 检查是否是文件
            urls = event.mimeData().urls()
            if urls and urls[0].isLocalFile():
                # 接受拖拽
                event.acceptProposedAction()

    def dragMoveEvent(self, event: QDropEvent) -> None:
        """拖拽移动事件。"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """拖拽放下事件 - 处理 dropped files."""
        if not event.mimeData().hasUrls():
            return

        # 获取文件路径
        valid_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}
        file_paths = []

        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if path.exists() and path.suffix.lower() in valid_extensions:
                file_paths.append(str(path))

        if file_paths:
            # 发送信号通知主窗口处理这些文件
            self.files_dropped.emit(file_paths)

        event.acceptProposedAction()

    def _on_open_clicked(self) -> None:
        """处理打开按钮点击 - 弹出菜单选择文件或文件夹。"""
        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self)
        menu.addAction("📄 打开图片文件", self.open_file_requested.emit)
        menu.addAction("📁 打开文件夹", self.open_folder_requested.emit)
        menu.exec(self._open_btn.mapToGlobal(self._open_btn.rect().bottomLeft()))
