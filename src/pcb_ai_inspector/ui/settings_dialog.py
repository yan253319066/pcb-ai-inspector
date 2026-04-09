"""
PCB AI Inspector 设置对话框。

提供设置页面用于配置：
- UI 窗口和布局
- 检测参数
- 显示偏好
- 报告设置
- 性能选项
- 图像预处理
- 相机设置
- 工业场景
- 模型配置
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QGroupBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QComboBox,
    QPushButton,
    QFileDialog,
    QDialogButtonBox,
    QMessageBox,
    QScrollArea,
    QListWidget,
)

from ..core.settings import (
    SettingsManager,
    ApplicationSettings,
    UIWindowSettings,
    UILayoutSettings,
    ImageViewerSettings,
    DetectionSettings,
    DisplaySettings,
    ReportSettings,
    PerformanceSettings,
    PreprocessingSettings,
    CameraSettings,
    ModelSettings,
    IndustrialSettings,
    WindowSizePreset,
    LightingCondition,
    BinarizationMethod,
    CameraType,
    TriggerMode,
)
from ..core.activation import ActivationManager, check_activation


class UIWindowSettingsPage(QWidget):
    """UI 窗口设置页面。"""

    def __init__(
        self, settings: UIWindowSettings, parent: Optional[QWidget] = None
    ) -> None:
        """初始化 UI 窗口设置页面。

        Args:
            settings: UI 窗口设置
            parent: 父部件
        """
        super().__init__(parent)
        self._settings = settings
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置 UI。"""
        layout = QVBoxLayout(self)

        # 窗口标题
        group = QGroupBox("窗口标题")
        form = QFormLayout(group)

        self._window_title_edit = QLineEdit()
        self._window_title_edit.setText(self._settings.window_title)
        self._window_title_edit.setPlaceholderText("窗口标题")
        form.addRow("标题:", self._window_title_edit)

        layout.addWidget(group)

        # 窗口尺寸
        group2 = QGroupBox("窗口尺寸")
        form2 = QFormLayout(group2)

        self._size_preset_combo = QComboBox()
        self._size_preset_combo.addItems(
            ["标准 (1280x720)", "大屏 (1920x1080)", "紧凑 (1024x600)", "自定义"]
        )
        preset_map = {
            WindowSizePreset.STANDARD.value: 0,
            WindowSizePreset.LARGE.value: 1,
            WindowSizePreset.COMPACT.value: 2,
            WindowSizePreset.CUSTOM.value: 3,
        }
        self._size_preset_combo.setCurrentIndex(
            preset_map.get(self._settings.size_preset, 0)
        )
        form2.addRow("尺寸预设:", self._size_preset_combo)

        self._min_width_spin = QSpinBox()
        self._min_width_spin.setRange(640, 3840)
        self._min_width_spin.setSuffix(" px")
        self._min_width_spin.setValue(self._settings.min_width)
        form2.addRow("最小宽度:", self._min_width_spin)

        self._min_height_spin = QSpinBox()
        self._min_height_spin.setRange(480, 2160)
        self._min_height_spin.setSuffix(" px")
        self._min_height_spin.setValue(self._settings.min_height)
        form2.addRow("最小高度:", self._min_height_spin)

        self._resizable_check = QCheckBox("允许调整窗口大小")
        self._resizable_check.setChecked(self._settings.resizable)
        form2.addRow("", self._resizable_check)

        self._start_maximized_check = QCheckBox("启动时最大化")
        self._start_maximized_check.setChecked(self._settings.start_maximized)
        form2.addRow("", self._start_maximized_check)

        layout.addWidget(group2)
        layout.addStretch()

    def apply(self) -> None:
        """应用设置。"""
        self._settings.window_title = self._window_title_edit.text()
        preset_map = {
            0: WindowSizePreset.STANDARD.value,
            1: WindowSizePreset.LARGE.value,
            2: WindowSizePreset.COMPACT.value,
            3: WindowSizePreset.CUSTOM.value,
        }
        self._settings.size_preset = preset_map[self._size_preset_combo.currentIndex()]
        self._settings.min_width = self._min_width_spin.value()
        self._settings.min_height = self._min_height_spin.value()
        self._settings.resizable = self._resizable_check.isChecked()
        self._settings.start_maximized = self._start_maximized_check.isChecked()


class UILayoutSettingsPage(QWidget):
    """UI 布局设置页面。"""

    def __init__(
        self, settings: UILayoutSettings, parent: Optional[QWidget] = None
    ) -> None:
        """初始化 UI 布局设置页面。

        Args:
            settings: UI 布局设置
            parent: 父部件
        """
        super().__init__(parent)
        self._settings = settings
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置 UI。"""
        layout = QVBoxLayout(self)

        # 面板比例
        group = QGroupBox("面板比例")
        form = QFormLayout(group)

        self._image_ratio_spin = QDoubleSpinBox()
        self._image_ratio_spin.setRange(0.3, 0.9)
        self._image_ratio_spin.setSingleStep(0.05)
        self._image_ratio_spin.setDecimals(2)
        self._image_ratio_spin.setValue(self._settings.image_panel_ratio)
        self._image_ratio_spin.setSuffix(" (0-1)")
        form.addRow("图像区域比例:", self._image_ratio_spin)

        layout.addWidget(group)

        # 显示选项
        group2 = QGroupBox("显示选项")
        vbox2 = QVBoxLayout(group2)

        self._show_toolbar_check = QCheckBox("显示工具栏")
        self._show_toolbar_check.setChecked(self._settings.show_toolbar)
        vbox2.addWidget(self._show_toolbar_check)

        self._show_statusbar_check = QCheckBox("显示状态栏")
        self._show_statusbar_check.setChecked(self._settings.show_statusbar)
        vbox2.addWidget(self._show_statusbar_check)

        self._show_menubar_check = QCheckBox("显示菜单栏")
        self._show_menubar_check.setChecked(self._settings.show_menubar)
        vbox2.addWidget(self._show_menubar_check)

        layout.addWidget(group2)

        # 主题
        group3 = QGroupBox("外观")
        form3 = QFormLayout(group3)

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["浅色", "深色"])
        self._theme_combo.setCurrentIndex(0 if self._settings.theme == "light" else 1)
        form3.addRow("主题:", self._theme_combo)

        self._language_combo = QComboBox()
        self._language_combo.addItems(["中文", "English"])
        self._language_combo.setCurrentIndex(
            0 if self._settings.language == "zh-CN" else 1
        )
        form3.addRow("语言:", self._language_combo)

        layout.addWidget(group3)

        # 对话框默认尺寸
        dialog_group = QGroupBox("对话框默认尺寸")
        form4 = QFormLayout(dialog_group)

        self._camera_width_spin = QSpinBox()
        self._camera_width_spin.setRange(640, 1920)
        self._camera_width_spin.setSuffix(" px")
        self._camera_width_spin.setValue(self._settings.camera_dialog_width)
        form4.addRow("相机对话框宽度:", self._camera_width_spin)

        self._camera_height_spin = QSpinBox()
        self._camera_height_spin.setRange(480, 1200)
        self._camera_height_spin.setSuffix(" px")
        self._camera_height_spin.setValue(self._settings.camera_dialog_height)
        form4.addRow("相机对话框高度:", self._camera_height_spin)

        self._preview_width_spin = QSpinBox()
        self._preview_width_spin.setRange(320, 1280)
        self._preview_width_spin.setSuffix(" px")
        self._preview_width_spin.setValue(self._settings.camera_preview_min_width)
        form4.addRow("预览区域宽度:", self._preview_width_spin)

        self._preview_height_spin = QSpinBox()
        self._preview_height_spin.setRange(240, 960)
        self._preview_height_spin.setSuffix(" px")
        self._preview_height_spin.setValue(self._settings.camera_preview_min_height)
        form4.addRow("预览区域高度:", self._preview_height_spin)

        self._history_width_spin = QSpinBox()
        self._history_width_spin.setRange(640, 1920)
        self._history_width_spin.setSuffix(" px")
        self._history_width_spin.setValue(self._settings.history_dialog_width)
        form4.addRow("历史对话框宽度:", self._history_width_spin)

        self._history_height_spin = QSpinBox()
        self._history_height_spin.setRange(400, 1000)
        self._history_height_spin.setSuffix(" px")
        self._history_height_spin.setValue(self._settings.history_dialog_height)
        form4.addRow("历史对话框高度:", self._history_height_spin)

        self._report_width_spin = QSpinBox()
        self._report_width_spin.setRange(640, 1920)
        self._report_width_spin.setSuffix(" px")
        self._report_width_spin.setValue(self._settings.report_preview_width)
        form4.addRow("报告预览宽度:", self._report_width_spin)

        self._report_height_spin = QSpinBox()
        self._report_height_spin.setRange(400, 1000)
        self._report_height_spin.setSuffix(" px")
        self._report_height_spin.setValue(self._settings.report_preview_height)
        form4.addRow("报告预览高度:", self._report_height_spin)

        layout.addWidget(dialog_group)
        layout.addStretch()

    def apply(self) -> None:
        """应用设置。"""
        self._settings.image_panel_ratio = self._image_ratio_spin.value()
        self._settings.control_panel_ratio = 1.0 - self._image_ratio_spin.value()
        self._settings.show_toolbar = self._show_toolbar_check.isChecked()
        self._settings.show_statusbar = self._show_statusbar_check.isChecked()
        self._settings.show_menubar = self._show_menubar_check.isChecked()
        self._settings.theme = (
            "light" if self._theme_combo.currentIndex() == 0 else "dark"
        )
        self._settings.language = (
            "zh-CN" if self._language_combo.currentIndex() == 0 else "en-US"
        )
        # 对话框尺寸
        self._settings.camera_dialog_width = self._camera_width_spin.value()
        self._settings.camera_dialog_height = self._camera_height_spin.value()
        self._settings.camera_preview_min_width = self._preview_width_spin.value()
        self._settings.camera_preview_min_height = self._preview_height_spin.value()
        self._settings.history_dialog_width = self._history_width_spin.value()
        self._settings.history_dialog_height = self._history_height_spin.value()
        self._settings.report_preview_width = self._report_width_spin.value()
        self._settings.report_preview_height = self._report_height_spin.value()


class ImageViewerSettingsPage(QWidget):
    """图像查看器设置页面。"""

    def __init__(
        self, settings: ImageViewerSettings, parent: Optional[QWidget] = None
    ) -> None:
        """初始化图像查看器设置页面。

        Args:
            settings: 图像查看器设置
            parent: 父部件
        """
        super().__init__(parent)
        self._settings = settings
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置 UI。"""
        layout = QVBoxLayout(self)

        # 缩放设置
        group = QGroupBox("缩放设置")
        form = QFormLayout(group)

        self._default_zoom_spin = QSpinBox()
        self._default_zoom_spin.setRange(10, 500)
        self._default_zoom_spin.setSingleStep(10)
        self._default_zoom_spin.setSuffix(" %")
        self._default_zoom_spin.setValue(self._settings.default_zoom)
        form.addRow("默认缩放:", self._default_zoom_spin)

        self._min_zoom_spin = QSpinBox()
        self._min_zoom_spin.setRange(5, 50)
        self._min_zoom_spin.setSuffix(" %")
        self._min_zoom_spin.setValue(self._settings.min_zoom)
        form.addRow("最小缩放:", self._min_zoom_spin)

        self._max_zoom_spin = QSpinBox()
        self._max_zoom_spin.setRange(200, 1000)
        self._max_zoom_spin.setSuffix(" %")
        self._max_zoom_spin.setValue(self._settings.max_zoom)
        form.addRow("最大缩放:", self._max_zoom_spin)

        self._zoom_step_spin = QSpinBox()
        self._zoom_step_spin.setRange(5, 50)
        self._zoom_step_spin.setSuffix(" %")
        self._zoom_step_spin.setValue(self._settings.zoom_step)
        form.addRow("缩放步长:", self._zoom_step_spin)

        layout.addWidget(group)

        # 缩放模式
        group2 = QGroupBox("缩放模式")
        form2 = QFormLayout(group2)

        self._zoom_mode_combo = QComboBox()
        self._zoom_mode_combo.addItems(["适应窗口", "实际大小", "自由缩放"])
        mode_map = {"fit": 0, "actual": 1, "free": 2}
        self._zoom_mode_combo.setCurrentIndex(mode_map.get(self._settings.zoom_mode, 0))
        form2.addRow("默认模式:", self._zoom_mode_combo)

        layout.addWidget(group2)
        layout.addStretch()

    def apply(self) -> None:
        """应用设置。"""
        self._settings.default_zoom = self._default_zoom_spin.value()
        self._settings.min_zoom = self._min_zoom_spin.value()
        self._settings.max_zoom = self._max_zoom_spin.value()
        self._settings.zoom_step = self._zoom_step_spin.value()
        mode_map = {0: "fit", 1: "actual", 2: "free"}
        self._settings.zoom_mode = mode_map[self._zoom_mode_combo.currentIndex()]


class ModelSettingsPage(QWidget):
    """模型设置页面。"""

    def __init__(
        self, settings: ModelSettings, parent: Optional[QWidget] = None
    ) -> None:
        """初始化模型设置页面。

        Args:
            settings: 模型设置
            parent: 父部件
        """
        super().__init__(parent)
        self._settings = settings
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置 UI。"""
        layout = QVBoxLayout(self)

        # 模型路径
        group = QGroupBox("模型配置")
        form = QFormLayout(group)

        path_layout = QHBoxLayout()
        self._model_path_edit = QLineEdit()
        self._model_path_edit.setText(self._settings.model_path)
        self._model_path_edit.setPlaceholderText("模型文件路径 (.pt, .onnx)")
        path_layout.addWidget(self._model_path_edit)

        self._browse_btn = QPushButton("浏览...")
        self._browse_btn.clicked.connect(self._browse_model)
        path_layout.addWidget(self._browse_btn)
        form.addRow("模型路径:", path_layout)

        # 模型类型
        self._model_type_combo = QComboBox()
        self._model_type_combo.addItems(["YOLO11", "YOLOv8", "YOLOv10"])
        type_map = {"yolo11": 0, "yolov8": 1, "yolov10": 2}
        self._model_type_combo.setCurrentIndex(
            type_map.get(self._settings.model_type, 0)
        )
        form.addRow("模型类型:", self._model_type_combo)

        # 模型变体
        self._model_variant_combo = QComboBox()
        self._model_variant_combo.addItems(
            ["Nano (n)", "Small (s)", "Medium (m)", "Large (l)", "X-Large (x)"]
        )
        variant_map = {"n": 0, "s": 1, "m": 2, "l": 3, "x": 4}
        self._model_variant_combo.setCurrentIndex(
            variant_map.get(self._settings.model_variant, 1)
        )
        form.addRow("模型大小:", self._model_variant_combo)

        # 输入尺寸
        self._input_size_spin = QSpinBox()
        self._input_size_spin.setRange(320, 1280)
        self._input_size_spin.setSingleStep(32)
        self._input_size_spin.setSuffix(" px")
        self._input_size_spin.setValue(self._settings.input_size)
        form.addRow("输入尺寸:", self._input_size_spin)

        layout.addWidget(group)
        layout.addStretch()

    def _browse_model(self) -> None:
        """浏览模型文件。"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择模型文件",
            "",
            "模型文件 (*.pt *.onnx);;所有文件 (*.*)",
        )
        if file_path:
            self._model_path_edit.setText(file_path)

    def apply(self) -> None:
        """应用设置。"""
        self._settings.model_path = self._model_path_edit.text()
        type_map = {0: "yolov10", 1: "yolov8", 2: "yolov11"}
        self._settings.model_type = type_map[self._model_type_combo.currentIndex()]
        variant_map = {0: "n", 1: "s", 2: "m", 3: "l", 4: "x"}
        self._settings.model_variant = variant_map[
            self._model_variant_combo.currentIndex()
        ]
        self._settings.input_size = self._input_size_spin.value()


class IndustrialSettingsPage(QWidget):
    """工业场景设置页面。"""

    def __init__(
        self, settings: IndustrialSettings, parent: Optional[QWidget] = None
    ) -> None:
        """初始化工业场景设置页面。

        Args:
            settings: 工业场景设置
            parent: 父部件
        """
        super().__init__(parent)
        self._settings = settings
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置 UI。"""
        layout = QVBoxLayout(self)

        # 生产线配置
        group = QGroupBox("生产线配置")
        form = QFormLayout(group)

        self._production_line_edit = QLineEdit()
        self._production_line_edit.setText(self._settings.production_line)
        self._production_line_edit.setPlaceholderText("生产线名称")
        form.addRow("生产线:", self._production_line_edit)

        self._station_name_edit = QLineEdit()
        self._station_name_edit.setText(self._settings.station_name)
        self._station_name_edit.setPlaceholderText("工位名称")
        form.addRow("工位:", self._station_name_edit)

        self._shift_combo = QComboBox()
        self._shift_combo.addItems(["日班", "夜班", "自定义"])
        shift_map = {"day": 0, "night": 1, "custom": 2}
        self._shift_combo.setCurrentIndex(shift_map.get(self._settings.shift_config, 0))
        form.addRow("班次:", self._shift_combo)

        layout.addWidget(group)

        # 质量控制
        group2 = QGroupBox("质量控制")
        form2 = QFormLayout(group2)

        self._pass_threshold_spin = QDoubleSpinBox()
        self._pass_threshold_spin.setRange(0.0, 1.0)
        self._pass_threshold_spin.setSingleStep(0.05)
        self._pass_threshold_spin.setDecimals(2)
        self._pass_threshold_spin.setValue(self._settings.pass_threshold)
        form2.addRow("通过阈值:", self._pass_threshold_spin)

        self._fail_on_critical_check = QCheckBox("关键缺陷直接判定为不合格")
        self._fail_on_critical_check.setChecked(self._settings.fail_on_critical)
        form2.addRow("", self._fail_on_critical_check)

        self._severity_enabled_check = QCheckBox("启用缺陷分级")
        self._severity_enabled_check.setChecked(self._settings.defect_severity_enabled)
        form2.addRow("", self._severity_enabled_check)

        layout.addWidget(group2)

        # 数据追溯
        group3 = QGroupBox("数据追溯")
        vbox3 = QVBoxLayout(group3)

        self._traceability_check = QCheckBox("启用数据追溯")
        self._traceability_check.setChecked(self._settings.enable_traceability)
        vbox3.addWidget(self._traceability_check)

        self._save_original_check = QCheckBox("保存原始图像（需要更多存储空间）")
        self._save_original_check.setChecked(self._settings.save_original_images)
        vbox3.addWidget(self._save_original_check)

        self._save_marked_check = QCheckBox("保存标注图像")
        self._save_marked_check.setChecked(self._settings.save_marked_images)
        vbox3.addWidget(self._save_marked_check)

        layout.addWidget(group3)

        # 报警设置
        group4 = QGroupBox("报警设置")
        form4 = QFormLayout(group4)

        self._alarm_enabled_check = QCheckBox("启用缺陷报警")
        self._alarm_enabled_check.setChecked(self._settings.enable_alarm)
        form4.addRow("", self._alarm_enabled_check)

        self._alarm_count_spin = QSpinBox()
        self._alarm_count_spin.setRange(0, 100)
        self._alarm_count_spin.setValue(self._settings.alarm_on_defect_count)
        form4.addRow("报警阈值(缺陷数):", self._alarm_count_spin)

        layout.addWidget(group4)
        layout.addStretch()

    def apply(self) -> None:
        """应用设置。"""
        self._settings.production_line = self._production_line_edit.text() or "default"
        self._settings.station_name = self._station_name_edit.text() or "default"
        shift_map = {0: "day", 1: "night", 2: "custom"}
        self._settings.shift_config = shift_map[self._shift_combo.currentIndex()]
        self._settings.pass_threshold = self._pass_threshold_spin.value()
        self._settings.fail_on_critical = self._fail_on_critical_check.isChecked()
        self._settings.defect_severity_enabled = (
            self._severity_enabled_check.isChecked()
        )
        self._settings.enable_traceability = self._traceability_check.isChecked()
        self._settings.save_original_images = self._save_original_check.isChecked()
        self._settings.save_marked_images = self._save_marked_check.isChecked()
        self._settings.enable_alarm = self._alarm_enabled_check.isChecked()
        self._settings.alarm_on_defect_count = self._alarm_count_spin.value()


class DetectionSettingsPage(QWidget):
    """Detection settings page."""

    def __init__(
        self, settings: DetectionSettings, parent: Optional[QWidget] = None
    ) -> None:
        """Initialize detection settings page.

        Args:
            settings: Detection settings
            parent: Parent widget
        """
        super().__init__(parent)
        self._settings = settings
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the UI."""
        layout = QVBoxLayout(self)

        # Detection parameters
        group = QGroupBox("检测参数")
        form = QFormLayout(group)

        # Confidence threshold
        self._confidence_spin = QDoubleSpinBox()
        self._confidence_spin.setRange(0.0, 1.0)
        self._confidence_spin.setSingleStep(0.05)
        self._confidence_spin.setDecimals(2)
        self._confidence_spin.setValue(self._settings.confidence_threshold)
        self._confidence_spin.setPrefix("")
        self._confidence_spin.setSuffix("")
        form.addRow("置信度阈值:", self._confidence_spin)

        # IOU threshold
        self._iou_spin = QDoubleSpinBox()
        self._iou_spin.setRange(0.0, 1.0)
        self._iou_spin.setSingleStep(0.05)
        self._iou_spin.setDecimals(2)
        self._iou_spin.setValue(self._settings.iou_threshold)
        form.addRow("IOU 阈值:", self._iou_spin)

        # Max detections
        self._max_detections_spin = QSpinBox()
        self._max_detections_spin.setRange(1, 1000)
        self._max_detections_spin.setValue(self._settings.max_detections)
        form.addRow("最大检测数:", self._max_detections_spin)

        layout.addWidget(group)

        # 后处理过滤
        group2 = QGroupBox("后处理过滤")
        form2 = QFormLayout(group2)

        self._filtering_check = QCheckBox("启用过滤")
        self._filtering_check.setChecked(self._settings.enable_filtering)
        form2.addRow("", self._filtering_check)

        self._min_size_spin = QSpinBox()
        self._min_size_spin.setRange(1, 1000)
        self._min_size_spin.setValue(self._settings.min_defect_size)
        form2.addRow("最小缺陷尺寸(px):", self._min_size_spin)

        self._max_size_spin = QSpinBox()
        self._max_size_spin.setRange(1, 10000)
        self._max_size_spin.setValue(self._settings.max_defect_size)
        form2.addRow("最大缺陷尺寸(px):", self._max_size_spin)

        self._nms_check = QCheckBox("启用NMS重叠过滤")
        self._nms_check.setChecked(self._settings.enable_nms)
        form2.addRow("", self._nms_check)

        layout.addWidget(group2)
        layout.addStretch()

    def apply(self) -> None:
        """Apply settings to the settings object."""
        self._settings.confidence_threshold = self._confidence_spin.value()
        self._settings.iou_threshold = self._iou_spin.value()
        self._settings.max_detections = self._max_detections_spin.value()
        self._settings.enable_filtering = self._filtering_check.isChecked()
        self._settings.min_defect_size = self._min_size_spin.value()
        self._settings.max_defect_size = self._max_size_spin.value()
        self._settings.enable_nms = self._nms_check.isChecked()


class DisplaySettingsPage(QWidget):
    """Display settings page."""

    def __init__(
        self, settings: DisplaySettings, parent: Optional[QWidget] = None
    ) -> None:
        """Initialize display settings page.

        Args:
            settings: Display settings
            parent: Parent widget
        """
        super().__init__(parent)
        self._settings = settings
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the UI."""
        layout = QVBoxLayout(self)

        # Display options
        group = QGroupBox("显示选项")
        vbox = QVBoxLayout(group)

        self._show_boxes_check = QCheckBox("显示边界框")
        self._show_boxes_check.setChecked(self._settings.show_boxes)
        vbox.addWidget(self._show_boxes_check)

        self._show_labels_check = QCheckBox("显示标签")
        self._show_labels_check.setChecked(self._settings.show_labels)
        vbox.addWidget(self._show_labels_check)

        self._show_confidence_check = QCheckBox("显示置信度")
        self._show_confidence_check.setChecked(self._settings.show_confidence)
        vbox.addWidget(self._show_confidence_check)

        layout.addWidget(group)

        # Visual settings
        group2 = QGroupBox("视觉效果")
        form = QFormLayout(group2)

        self._box_thickness_spin = QSpinBox()
        self._box_thickness_spin.setRange(1, 10)
        self._box_thickness_spin.setValue(self._settings.box_thickness)
        form.addRow("边框粗细:", self._box_thickness_spin)

        self._font_scale_spin = QDoubleSpinBox()
        self._font_scale_spin.setRange(0.1, 2.0)
        self._font_scale_spin.setSingleStep(0.1)
        self._font_scale_spin.setDecimals(1)
        self._font_scale_spin.setValue(self._settings.font_scale)
        form.addRow("字体大小:", self._font_scale_spin)

        self._default_zoom_spin = QSpinBox()
        self._default_zoom_spin.setRange(10, 500)
        self._default_zoom_spin.setSingleStep(10)
        self._default_zoom_spin.setValue(self._settings.default_zoom)
        self._default_zoom_spin.setSuffix("%")
        form.addRow("默认缩放:", self._default_zoom_spin)

        layout.addWidget(group2)
        layout.addStretch()

    def apply(self) -> None:
        """Apply settings to the settings object."""
        self._settings.show_boxes = self._show_boxes_check.isChecked()
        self._settings.show_labels = self._show_labels_check.isChecked()
        self._settings.show_confidence = self._show_confidence_check.isChecked()
        self._settings.box_thickness = self._box_thickness_spin.value()
        self._settings.font_scale = self._font_scale_spin.value()
        self._settings.default_zoom = self._default_zoom_spin.value()


class ReportSettingsPage(QWidget):
    """Report settings page."""

    def __init__(
        self, settings: ReportSettings, parent: Optional[QWidget] = None
    ) -> None:
        """Initialize report settings page.

        Args:
            settings: Report settings
            parent: Parent widget
        """
        super().__init__(parent)
        self._settings = settings
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the UI."""
        layout = QVBoxLayout(self)

        # Default format
        group = QGroupBox("默认格式")
        form = QFormLayout(group)

        self._format_combo = QComboBox()
        self._format_combo.addItems(["PDF", "Excel"])
        self._format_combo.setCurrentText(
            "PDF" if self._settings.default_format == "pdf" else "Excel"
        )
        form.addRow("报告格式:", self._format_combo)

        layout.addWidget(group)

        # Include options
        group2 = QGroupBox("报告内容")
        vbox = QVBoxLayout(group2)

        self._include_stats_check = QCheckBox("包含统计信息")
        self._include_stats_check.setChecked(self._settings.include_statistics)
        vbox.addWidget(self._include_stats_check)

        self._include_image_check = QCheckBox("包含检测图像")
        self._include_image_check.setChecked(self._settings.include_image)
        vbox.addWidget(self._include_image_check)

        layout.addWidget(group2)

        # Company info
        group3 = QGroupBox("公司信息")
        form3 = QFormLayout(group3)

        self._company_name_edit = QLineEdit()
        self._company_name_edit.setText(self._settings.company_name)
        self._company_name_edit.setPlaceholderText("输入公司名称")
        form3.addRow("公司名称:", self._company_name_edit)

        logo_layout = QHBoxLayout()
        self._logo_path_edit = QLineEdit()
        self._logo_path_edit.setText(self._settings.company_logo)
        self._logo_path_edit.setPlaceholderText("选择公司Logo")
        self._logo_path_edit.setReadOnly(True)
        logo_layout.addWidget(self._logo_path_edit)

        self._browse_logo_btn = QPushButton("浏览...")
        self._browse_logo_btn.clicked.connect(self._browse_logo)
        logo_layout.addWidget(self._browse_logo_btn)

        form3.addRow("公司Logo:", logo_layout)

        layout.addWidget(group3)
        layout.addStretch()

    def _browse_logo(self) -> None:
        """Browse for logo file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择公司Logo",
            "",
            "图像文件 (*.png *.jpg *.jpeg *.bmp);;所有文件 (*.*)",
        )

        if file_path:
            self._logo_path_edit.setText(file_path)

    def apply(self) -> None:
        """Apply settings to the settings object."""
        self._settings.default_format = (
            "pdf" if self._format_combo.currentText() == "PDF" else "excel"
        )
        self._settings.include_statistics = self._include_stats_check.isChecked()
        self._settings.include_image = self._include_image_check.isChecked()
        self._settings.company_name = self._company_name_edit.text()
        self._settings.company_logo = self._logo_path_edit.text()


class PerformanceSettingsPage(QWidget):
    """Performance settings page."""

    def __init__(
        self, settings: PerformanceSettings, parent: Optional[QWidget] = None
    ) -> None:
        """Initialize performance settings page.

        Args:
            settings: Performance settings
            parent: Parent widget
        """
        super().__init__(parent)
        self._settings = settings
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the UI."""
        layout = QVBoxLayout(self)

        # GPU settings
        group = QGroupBox("GPU 设置")
        vbox = QVBoxLayout(group)

        self._use_gpu_check = QCheckBox("可用时使用 GPU 加速")
        self._use_gpu_check.setChecked(self._settings.use_gpu_if_available)
        vbox.addWidget(self._use_gpu_check)

        layout.addWidget(group)

        # Batch processing
        group2 = QGroupBox("批处理")
        form = QFormLayout(group2)

        self._batch_size_spin = QSpinBox()
        self._batch_size_spin.setRange(1, 64)
        self._batch_size_spin.setValue(self._settings.batch_size)
        form.addRow("批量大小:", self._batch_size_spin)

        self._num_workers_spin = QSpinBox()
        self._num_workers_spin.setRange(1, 32)
        self._num_workers_spin.setValue(self._settings.num_workers)
        form.addRow("工作线程数:", self._num_workers_spin)

        layout.addWidget(group2)

        # Caching
        group3 = QGroupBox("缓存")
        vbox3 = QVBoxLayout(group3)

        self._enable_cache_check = QCheckBox("启用图像缓存")
        self._enable_cache_check.setChecked(self._settings.enable_caching)
        vbox3.addWidget(self._enable_cache_check)

        cache_layout = QHBoxLayout()
        cache_layout.addWidget(QLabel("缓存大小:"))

        self._cache_size_spin = QSpinBox()
        self._cache_size_spin.setRange(64, 4096)
        self._cache_size_spin.setSingleStep(64)
        self._cache_size_spin.setValue(self._settings.cache_size_mb)
        self._cache_size_spin.setSuffix(" MB")
        cache_layout.addWidget(self._cache_size_spin)
        cache_layout.addStretch()

        vbox3.addLayout(cache_layout)

        layout.addWidget(group3)
        layout.addStretch()

    def apply(self) -> None:
        """Apply settings to the settings object."""
        self._settings.use_gpu_if_available = self._use_gpu_check.isChecked()
        self._settings.batch_size = self._batch_size_spin.value()
        self._settings.num_workers = self._num_workers_spin.value()
        self._settings.enable_caching = self._enable_cache_check.isChecked()
        self._settings.cache_size_mb = self._cache_size_spin.value()


class PreprocessingSettingsPage(QWidget):
    """图像预处理设置页面（用于相机实拍图）。"""

    def __init__(
        self, settings: PreprocessingSettings, parent: Optional[QWidget] = None
    ) -> None:
        """Initialize preprocessing settings page.

        Args:
            settings: Preprocessing settings
            parent: Parent widget
        """
        super().__init__(parent)
        self._settings = settings
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the UI."""
        layout = QVBoxLayout(self)

        # 开关
        group = QGroupBox("图像预处理")
        vbox = QVBoxLayout(group)

        self._enable_preprocessing_check = QCheckBox("启用图像预处理（相机实拍图）")
        self._enable_preprocessing_check.setChecked(self._settings.enable_preprocessing)
        vbox.addWidget(self._enable_preprocessing_check)

        layout.addWidget(group)

        # 光照预设
        group2 = QGroupBox("光照环境")
        form = QFormLayout(group2)

        self._lighting_combo = QComboBox()
        self._lighting_combo.addItems(
            [
                "均匀光照 (uniform)",
                "光照不均 (uneven)",
                "弱光环境 (low_light)",
                "自动检测 (unknown)",
            ]
        )
        lighting_map = {"uniform": 0, "uneven": 1, "low_light": 2, "unknown": 3}
        self._lighting_combo.setCurrentIndex(
            lighting_map.get(self._settings.lighting_preset, 3)
        )
        form.addRow("光照预设:", self._lighting_combo)

        layout.addWidget(group2)

        # 去噪设置
        group3 = QGroupBox("去噪")
        vbox3 = QVBoxLayout(group3)

        self._enable_denoise_check = QCheckBox("启用高斯去噪")
        self._enable_denoise_check.setChecked(self._settings.enable_denoise)
        vbox3.addWidget(self._enable_denoise_check)

        denoise_layout = QHBoxLayout()
        denoise_layout.addWidget(QLabel("核大小:"))
        self._denoise_kernel_spin = QSpinBox()
        self._denoise_kernel_spin.setRange(1, 15)
        self._denoise_kernel_spin.setSingleStep(2)
        self._denoise_kernel_spin.setValue(self._settings.denoise_kernel)
        self._denoise_kernel_spin.setSuffix("（奇数）")
        denoise_layout.addWidget(self._denoise_kernel_spin)
        denoise_layout.addStretch()
        vbox3.addLayout(denoise_layout)

        layout.addWidget(group3)

        # 二值化设置
        group4 = QGroupBox("二值化")
        form4 = QFormLayout(group4)

        self._binarization_combo = QComboBox()
        self._binarization_combo.addItems(
            [
                "自适应高斯 (adaptive_gaussian)",
                "自适应均值 (adaptive_mean)",
                "大津算法 (otsu)",
                "大津+高斯 (otsu_gaussian)",
                "固定阈值 (fixed)",
            ]
        )
        binarization_map = {
            "adaptive_gaussian": 0,
            "adaptive_mean": 1,
            "otsu": 2,
            "otsu_gaussian": 3,
            "fixed": 4,
        }
        self._binarization_combo.setCurrentIndex(
            binarization_map.get(self._settings.binarization_method, 0)
        )
        form4.addRow("二值化方法:", self._binarization_combo)

        self._adaptive_block_spin = QSpinBox()
        self._adaptive_block_spin.setRange(3, 51)
        self._adaptive_block_spin.setSingleStep(2)
        self._adaptive_block_spin.setValue(self._settings.adaptive_block_size)
        self._adaptive_block_spin.setSuffix(" 像素")
        form4.addRow("自适应块大小:", self._adaptive_block_spin)

        self._adaptive_c_spin = QSpinBox()
        self._adaptive_c_spin.setRange(0, 10)
        self._adaptive_c_spin.setValue(self._settings.adaptive_c)
        form4.addRow("阈值常数 C:", self._adaptive_c_spin)

        layout.addWidget(group4)

        # CLAHE 对比度增强
        group5 = QGroupBox("对比度增强 (CLAHE)")
        vbox5 = QVBoxLayout(group5)

        self._enable_clahe_check = QCheckBox("启用 CLAHE")
        self._enable_clahe_check.setChecked(self._settings.enable_clahe)
        vbox5.addWidget(self._enable_clahe_check)

        clahe_layout = QHBoxLayout()
        clahe_layout.addWidget(QLabel("对比度限制:"))
        self._clahe_clip_spin = QDoubleSpinBox()
        self._clahe_clip_spin.setRange(0.1, 5.0)
        self._clahe_clip_spin.setSingleStep(0.1)
        self._clahe_clip_spin.setDecimals(1)
        self._clahe_clip_spin.setValue(self._settings.clahe_clip_limit)
        clahe_layout.addWidget(self._clahe_clip_spin)
        clahe_layout.addStretch()
        vbox5.addLayout(clahe_layout)

        layout.addWidget(group5)

        # ROI 提取
        group6 = QGroupBox("ROI 提取")
        vbox6 = QVBoxLayout(group6)

        self._enable_roi_check = QCheckBox("启用自动 ROI 提取（跳过黑边）")
        self._enable_roi_check.setChecked(self._settings.enable_roi)
        vbox6.addWidget(self._enable_roi_check)

        roi_layout = QHBoxLayout()
        roi_layout.addWidget(QLabel("边缘留白:"))
        self._roi_margin_spin = QSpinBox()
        self._roi_margin_spin.setRange(0, 50)
        self._roi_margin_spin.setValue(self._settings.roi_margin)
        self._roi_margin_spin.setSuffix(" 像素")
        roi_layout.addWidget(self._roi_margin_spin)
        roi_layout.addStretch()
        vbox6.addLayout(roi_layout)

        layout.addWidget(group6)

        layout.addStretch()

    def apply(self) -> None:
        """Apply settings to the settings object."""
        self._settings.enable_preprocessing = (
            self._enable_preprocessing_check.isChecked()
        )

        lighting_values = ["uniform", "uneven", "low_light", "unknown"]
        self._settings.lighting_preset = lighting_values[
            self._lighting_combo.currentIndex()
        ]

        self._settings.enable_denoise = self._enable_denoise_check.isChecked()
        self._settings.denoise_kernel = self._denoise_kernel_spin.value()

        binarization_values = [
            "adaptive_gaussian",
            "adaptive_mean",
            "otsu",
            "otsu_gaussian",
            "fixed",
        ]
        self._settings.binarization_method = binarization_values[
            self._binarization_combo.currentIndex()
        ]
        self._settings.adaptive_block_size = self._adaptive_block_spin.value()
        self._settings.adaptive_c = self._adaptive_c_spin.value()

        self._settings.enable_clahe = self._enable_clahe_check.isChecked()
        self._settings.clahe_clip_limit = self._clahe_clip_spin.value()

        self._settings.enable_roi = self._enable_roi_check.isChecked()
        self._settings.roi_margin = self._roi_margin_spin.value()


class CameraSettingsPage(QWidget):
    """Camera settings page."""

    def __init__(
        self, settings: CameraSettings, parent: Optional[QWidget] = None
    ) -> None:
        """Initialize camera settings page.

        Args:
            settings: Camera settings
            parent: Parent widget
        """
        super().__init__(parent)
        self._settings = settings
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        """Setup the UI."""
        layout = QVBoxLayout(self)

        # Camera type
        type_group = QGroupBox("相机类型")
        type_layout = QVBoxLayout(type_group)

        self._camera_type_combo = QComboBox()
        self._camera_type_combo.addItems(["USB 摄像头", "GigE 工业相机"])
        type_layout.addWidget(self._camera_type_combo)

        layout.addWidget(type_group)

        # Camera connection
        conn_group = QGroupBox("连接设置")
        form = QFormLayout(conn_group)

        self._camera_id_edit = QLineEdit()
        self._camera_id_edit.setPlaceholderText("USB: 0,1,... / GigE: IP地址")
        form.addRow("相机ID:", self._camera_id_edit)

        res_layout = QHBoxLayout()
        self._width_spin = QSpinBox()
        self._width_spin.setRange(640, 4096)
        self._width_spin.setSuffix(" px")
        self._height_spin = QSpinBox()
        self._height_spin.setRange(480, 4096)
        self._height_spin.setSuffix(" px")
        res_layout.addWidget(self._width_spin)
        res_layout.addWidget(QLabel(" × "))
        res_layout.addWidget(self._height_spin)
        form.addRow("分辨率:", res_layout)

        self._exposure_spin = QDoubleSpinBox()
        self._exposure_spin.setRange(10, 100000)
        self._exposure_spin.setSuffix(" μs")
        form.addRow("曝光时间:", self._exposure_spin)

        self._gain_spin = QDoubleSpinBox()
        self._gain_spin.setRange(0, 20)
        self._gain_spin.setSingleStep(0.5)
        form.addRow("增益:", self._gain_spin)

        layout.addWidget(conn_group)

        # Trigger mode
        trigger_group = QGroupBox("触发模式")
        trigger_layout = QVBoxLayout(trigger_group)

        self._trigger_combo = QComboBox()
        self._trigger_combo.addItems(["连续采集", "外部触发", "软件触发"])
        trigger_layout.addWidget(self._trigger_combo)

        layout.addWidget(trigger_group)

        # Advanced
        adv_group = QGroupBox("高级设置")
        form2 = QFormLayout(adv_group)

        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(1000, 30000)
        self._timeout_spin.setSuffix(" ms")
        form2.addRow("超时时间:", self._timeout_spin)

        self._fps_spin = QSpinBox()
        self._fps_spin.setRange(0, 120)
        self._fps_spin.setSuffix(" FPS")
        self._fps_spin.setSpecialValueText("无限制")
        form2.addRow("帧率限制:", self._fps_spin)

        layout.addWidget(adv_group)

        layout.addStretch()

    def _load_settings(self) -> None:
        """Load settings into UI."""
        self._camera_type_combo.setCurrentIndex(
            0 if self._settings.camera_type == "usb" else 1
        )
        self._camera_id_edit.setText(self._settings.camera_id)
        self._width_spin.setValue(self._settings.resolution_width)
        self._height_spin.setValue(self._settings.resolution_height)
        self._exposure_spin.setValue(self._settings.exposure_us)
        self._gain_spin.setValue(self._settings.gain)

        trigger_map = {"continuous": 0, "external": 1, "software": 2}
        self._trigger_combo.setCurrentIndex(
            trigger_map.get(self._settings.trigger_mode, 0)
        )

        self._timeout_spin.setValue(self._settings.timeout_ms)
        self._fps_spin.setValue(self._settings.fps_limit)

    def apply(self) -> None:
        """Apply settings from UI."""
        self._settings.camera_type = (
            "usb" if self._camera_type_combo.currentIndex() == 0 else "gige"
        )
        self._settings.camera_id = self._camera_id_edit.text() or "0"
        self._settings.resolution_width = self._width_spin.value()
        self._settings.resolution_height = self._height_spin.value()
        self._settings.exposure_us = self._exposure_spin.value()
        self._settings.gain = self._gain_spin.value()

        trigger_modes = ["continuous", "external", "software"]
        self._settings.trigger_mode = trigger_modes[self._trigger_combo.currentIndex()]

        self._settings.timeout_ms = self._timeout_spin.value()
        self._settings.fps_limit = self._fps_spin.value()


class LicenseSettingsPage(QWidget):
    """License and activation settings page."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize license settings page.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._manager = ActivationManager()
        self._setup_ui()
        self._refresh_status()

    def _setup_ui(self) -> None:
        """Setup the UI."""
        layout = QVBoxLayout(self)

        # Status
        group = QGroupBox("授权状态")
        form = QFormLayout(group)

        self._hardware_id_label = QLabel()
        self._state_label = QLabel()
        self._activation_date_label = QLabel()
        self._expiration_date_label = QLabel()

        form.addRow("硬件ID:", self._hardware_id_label)
        form.addRow("授权状态:", self._state_label)
        form.addRow("激活日期:", self._activation_date_label)
        form.addRow("到期日期:", self._expiration_date_label)

        layout.addWidget(group)

        # Activation
        group2 = QGroupBox("激活")
        vbox = QVBoxLayout(group2)

        self._key_edit = QLineEdit()
        self._key_edit.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        vbox.addWidget(self._key_edit)

        btn_layout = QHBoxLayout()
        self._activate_btn = QPushButton("激活")
        self._activate_btn.clicked.connect(self._on_activate)
        btn_layout.addWidget(self._activate_btn)

        self._trial_btn = QPushButton("开始试用")
        self._trial_btn.clicked.connect(self._on_start_trial)
        btn_layout.addWidget(self._trial_btn)

        btn_layout.addStretch()
        vbox.addLayout(btn_layout)

        layout.addWidget(group2)

        # Info
        info_label = QLabel(
            "离线激活：无需联网即可完成激活。\n试用版本提供30天完整功能体验。"
        )
        info_label.setStyleSheet("color: gray; padding: 10px;")
        layout.addWidget(info_label)

        layout.addStretch()

    def _refresh_status(self) -> None:
        """Refresh the activation status display."""
        info = self._manager.get_activation_info()

        self._hardware_id_label.setText(info.hardware_id)
        self._state_label.setText(info.message)

        if info.activation_date:
            self._activation_date_label.setText(info.activation_date[:10])
        else:
            self._activation_date_label.setText("-")

        if info.expiration_date:
            self._expiration_date_label.setText(info.expiration_date[:10])
        else:
            self._expiration_date_label.setText("-")

    def _on_activate(self) -> None:
        """Handle activation button click."""
        key = self._key_edit.text().strip()

        if not key:
            QMessageBox.warning(self, "提示", "请输入授权码")
            return

        success, message = self._manager.activate(key)

        if success:
            QMessageBox.information(self, "激活成功", message)
            self._key_edit.clear()
        else:
            QMessageBox.warning(self, "激活失败", message)

        self._refresh_status()

    def _on_start_trial(self) -> None:
        """Handle trial button click."""
        reply = QMessageBox.question(
            self,
            "开始试用",
            "确定要开始30天试用吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._manager.start_evaluation(days=30)
            self._refresh_status()
            QMessageBox.information(self, "试用开始", "试用版已激活，剩余30天。")


class SettingsDialog(QDialog):
    """Main settings dialog."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize settings dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._manager = SettingsManager()
        self._settings = self._manager.settings

        # 从配置读取窗口标题和尺寸
        self.setWindowTitle(self._settings.ui_window.window_title)
        self.setMinimumSize(700, 550)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the UI."""
        layout = QVBoxLayout(self)

        # Tabs
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        # UI 窗口设置页面
        self._ui_window_page = UIWindowSettingsPage(self._settings.ui_window)
        self._tabs.addTab(self._ui_window_page, "窗口")

        # UI 布局设置页面
        self._ui_layout_page = UILayoutSettingsPage(self._settings.ui_layout)
        self._tabs.addTab(self._ui_layout_page, "布局")

        # 图像查看器设置页面
        self._ui_viewer_page = ImageViewerSettingsPage(self._settings.ui_viewer)
        self._tabs.addTab(self._ui_viewer_page, "查看器")

        # Detection page
        self._detection_page = DetectionSettingsPage(self._settings.detection)
        self._tabs.addTab(self._detection_page, "检测")

        # Display page
        self._display_page = DisplaySettingsPage(self._settings.display)
        self._tabs.addTab(self._display_page, "显示")

        # Report page
        self._report_page = ReportSettingsPage(self._settings.report)
        self._tabs.addTab(self._report_page, "报告")

        # Performance page
        self._performance_page = PerformanceSettingsPage(self._settings.performance)
        self._tabs.addTab(self._performance_page, "性能")

        # 注意：预处理页面已隐藏 - 预处理功能默认关闭，且会降低检测精度

        # Camera page
        self._camera_page = CameraSettingsPage(self._settings.camera)
        self._tabs.addTab(self._camera_page, "相机")

        # Model page
        self._model_page = ModelSettingsPage(self._settings.model)
        self._tabs.addTab(self._model_page, "模型")

        # Industrial page
        self._industrial_page = IndustrialSettingsPage(self._settings.industrial)
        self._tabs.addTab(self._industrial_page, "工业")

        # License page
        self._license_page = LicenseSettingsPage()
        self._tabs.addTab(self._license_page, "授权")

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Reset
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)

        reset_btn = button_box.button(QDialogButtonBox.StandardButton.Reset)
        reset_btn.setText("恢复默认")
        reset_btn.clicked.connect(self._on_reset)

        layout.addWidget(button_box)

    def _on_accept(self) -> None:
        """Handle OK button click."""
        # Apply all pages (注意：预处理页面已移除)
        self._ui_window_page.apply()
        self._ui_layout_page.apply()
        self._ui_viewer_page.apply()
        self._detection_page.apply()
        self._display_page.apply()
        self._report_page.apply()
        self._performance_page.apply()
        self._camera_page.apply()
        self._model_page.apply()
        self._industrial_page.apply()

        # Validate
        errors = self._manager.validate()
        if errors:
            QMessageBox.warning(self, "设置错误", "\n".join(errors))
            return

        # Save
        self._manager.save()

        # 重新加载全局设置管理器，使新设置立即生效
        from ..core.settings import get_settings_manager

        get_settings_manager(force_reload=True)

        self.accept()

    def _on_reset(self) -> None:
        """Handle reset button click."""
        reply = QMessageBox.question(
            self,
            "恢复默认设置",
            "确定要恢复所有设置为默认值吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._manager.reset_to_defaults()
            self._settings = self._manager.settings

            # Refresh all pages (注意：预处理页面已移除)
            self._tabs.removeTab(self._tabs.indexOf(self._detection_page))
            self._tabs.removeTab(self._tabs.indexOf(self._display_page) - 1)
            self._tabs.removeTab(self._tabs.indexOf(self._report_page) - 2)
            self._tabs.removeTab(self._tabs.indexOf(self._performance_page) - 3)

            self._detection_page = DetectionSettingsPage(self._settings.detection)
            self._display_page = DisplaySettingsPage(self._settings.display)
            self._report_page = ReportSettingsPage(self._settings.report)
            self._performance_page = PerformanceSettingsPage(self._settings.performance)

            self._tabs.insertTab(0, self._detection_page, "检测")
            self._tabs.insertTab(1, self._display_page, "显示")
            self._tabs.insertTab(2, self._report_page, "报告")
            self._tabs.insertTab(3, self._performance_page, "性能")

            QMessageBox.information(self, "完成", "设置已恢复为默认值")


if __name__ == "__main__":
    # Test dialog
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    dialog = SettingsDialog()
    dialog.exec()
