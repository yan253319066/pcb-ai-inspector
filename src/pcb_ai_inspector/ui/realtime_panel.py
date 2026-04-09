"""
PCB AI Inspector 实时检测面板模块。

提供实时检测界面的完整面板组件，包括：
- 相机预览
- 实时检测结果
- Pass/Fail 大字显示（工业场景）
- 声光报警
- 统计看板
- 相机设置和控制
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from loguru import logger

import numpy as np
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox,
    QCheckBox,
    QLineEdit,
    QMessageBox,
    QFileDialog,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
)

from .defect_list import DefectListWidget, StatisticsWidget
from .defect_overlay import DetectionResult
from .statistics_panel import StatisticsManager
from ..utils.alarm_controller import AlarmController
from ..utils.shift_manager import ShiftManager, DEFAULT_SHIFTS

if TYPE_CHECKING:
    from ..models.detector import YOLODetector
    from ..models.detector import DetectionResult as ModelDetectionResult
    from .detection_result_handler import DetectionResultHandler


class RealtimeDetectionPanel(QWidget):
    """
    实时检测面板组件。

    包含相机预览、实时检测、控制按钮的完整界面。

    Signals:
        capture_requested: 请求捕获当前帧 (frame: np.ndarray)
        save_requested: 请求保存当前帧 (frame: np.ndarray)
        detection_completed: 检测完成 (detections: list)
    """

    # 信号定义
    capture_requested = pyqtSignal(object)  # np.ndarray
    save_requested = pyqtSignal(object)  # np.ndarray
    detection_completed = pyqtSignal(list)  # list[DetectionResult]

    def __init__(
        self,
        detector: Optional["YOLODetector"] = None,
        result_handler: Optional["DetectionResultHandler"] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """初始化实时检测面板。"""
        super().__init__(parent)

        self._detector = detector
        self._result_handler = result_handler

        # 相机相关
        self._realtime_camera = None
        self._realtime_previewing = False
        self._realtime_timer: Optional[QTimer] = None

        # 当前帧和检测结果
        self._current_frame: Optional[np.ndarray] = None
        self._current_detections: list[DetectionResult] = []
        self._detection_history: list[list[DetectionResult]] = []
        self._detection_times: list[str] = []
        self._prev_detections: list[DetectionResult] = []

        # 统计管理器和报警控制器
        self._stats_manager = StatisticsManager()
        self._alarm = AlarmController()

        # 班次管理器
        self._shift_manager = ShiftManager()

        # Pass/Fail 状态
        self._last_result = ""  # "PASS" / "FAIL"
        self._detection_count = 0
        self._processing_time_ms = 0.0

        # 初始化UI
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置用户界面。"""
        # 主布局
        layout = QVBoxLayout(self)

        # 顶部工具栏
        toolbar_layout = QHBoxLayout()

        # 工位选择器
        station_group = QWidget()
        station_layout = QHBoxLayout(station_group)
        station_layout.setContentsMargins(0, 0, 0, 0)
        station_layout.addWidget(QLabel("工位:"))

        self._station_combo = QComboBox()
        self._station_combo.setEditable(True)
        self._station_combo.addItems(["A1", "A2", "A3", "B1", "B2"])
        # 延迟导入以避免循环依赖
        from ..core.settings import get_settings_manager

        self._station_combo.setCurrentText(
            get_settings_manager().settings.industrial.station_name
        )
        self._station_combo.currentTextChanged.connect(self._on_station_changed)
        station_layout.addWidget(self._station_combo)

        toolbar_layout.addWidget(station_group)

        # 班次选择器
        shift_group = QWidget()
        shift_layout = QHBoxLayout(shift_group)
        shift_layout.setContentsMargins(0, 0, 0, 0)
        shift_layout.addWidget(QLabel("班次:"))

        self._shift_combo = QComboBox()
        self._shift_combo.addItems(["日班", "夜班"])
        self._shift_combo.currentTextChanged.connect(self._on_shift_changed)
        shift_layout.addWidget(self._shift_combo)

        toolbar_layout.addWidget(shift_group)

        toolbar_layout.addStretch()

        # 报表和历史按钮
        self._report_btn = QPushButton("📊 报表")
        self._report_btn.clicked.connect(self._on_report_clicked)
        toolbar_layout.addWidget(self._report_btn)

        self._history_btn = QPushButton("📜 历史")
        self._history_btn.clicked.connect(self._on_history_clicked)
        toolbar_layout.addWidget(self._history_btn)

        layout.addLayout(toolbar_layout)

        # Pass/Fail 大字显示区域
        self._result_display = QLabel("等待检测")
        self._result_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result_display.setMinimumHeight(120)
        self._result_display.setStyleSheet(
            "background-color: #E5E7EB; color: #6B7280; "
            "font-size: 72px; font-weight: bold; border-radius: 8px;"
        )
        layout.addWidget(self._result_display)

        # 检测详情（缺陷数、置信度、耗时）
        detail_layout = QHBoxLayout()
        self._defect_count_label = QLabel("缺陷数: 0")
        self._defect_count_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        detail_layout.addWidget(self._defect_count_label)

        self._confidence_label = QLabel("置信度: --")
        self._confidence_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        detail_layout.addWidget(self._confidence_label)

        self._time_label = QLabel("耗时: --")
        self._time_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        detail_layout.addWidget(self._time_label)

        layout.addLayout(detail_layout)

        # 统计看板
        stats_group = QGroupBox("今日统计")
        stats_layout = QHBoxLayout(stats_group)

        self._today_total_label = QLabel("总计: 0")
        self._today_total_label.setStyleSheet("font-size: 14px;")
        stats_layout.addWidget(self._today_total_label)

        self._today_pass_label = QLabel("良品: 0")
        self._today_pass_label.setStyleSheet("font-size: 14px; color: #22C55E;")
        stats_layout.addWidget(self._today_pass_label)

        self._today_fail_label = QLabel("不良品: 0")
        self._today_fail_label.setStyleSheet("font-size: 14px; color: #EF4444;")
        stats_layout.addWidget(self._today_fail_label)

        self._today_rate_label = QLabel("良率: 100%")
        self._today_rate_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        stats_layout.addWidget(self._today_rate_label)

        layout.addWidget(stats_group)

        # 预览区域
        preview_layout = QHBoxLayout()

        # 左侧：相机预览
        preview_group = QGroupBox("相机预览")
        preview_group_layout = QVBoxLayout(preview_group)

        self._preview_label = QLabel()
        self._preview_label.setMinimumSize(640, 480)
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setStyleSheet("background-color: #1a1a1a;")
        self._preview_label.setText("点击'开始预览'连接摄像头")
        preview_group_layout.addWidget(self._preview_label)

        preview_layout.addWidget(preview_group, 2)

        # 右侧：检测结果列表和缺陷列表
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 检测结果列表
        results_group = QGroupBox("检测结果")
        results_layout = QVBoxLayout(results_group)

        self._results_table = QTableWidget()
        self._results_table.setColumnCount(5)
        self._results_table.setHorizontalHeaderLabels(["时间", "文件名", "缺陷数", "置信度", "状态"])
        self._results_table.setAlternatingRowColors(True)
        self._results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._results_table.horizontalHeader().setStretchLastSection(True)
        self._results_table.itemSelectionChanged.connect(self._on_result_selected)
        results_layout.addWidget(self._results_table)

        right_layout.addWidget(results_group)

        # 缺陷列表
        defect_group = QGroupBox("缺陷列表")
        defect_layout = QVBoxLayout(defect_group)

        self._defect_list = DefectListWidget()
        defect_layout.addWidget(self._defect_list)

        right_layout.addWidget(defect_group)

        preview_layout.addWidget(right_widget, 1)

        layout.addLayout(preview_layout)

        # 控制区域
        control_layout = QHBoxLayout()

        # 相机设置
        cam_settings_group = QGroupBox("相机设置")
        cam_settings_layout = QHBoxLayout(cam_settings_group)

        # 相机类型
        self._camera_type_combo = QComboBox()
        self._camera_type_combo.addItems(["USB 摄像头", "GigE 工业相机"])
        cam_settings_layout.addWidget(QLabel("类型:"))
        cam_settings_layout.addWidget(self._camera_type_combo)

        # 相机ID
        self._camera_id_input = QLineEdit("0")
        self._camera_id_input.setPlaceholderText("USB: 0,1,... / GigE: IP")
        self._camera_id_input.setMaximumWidth(120)
        cam_settings_layout.addWidget(QLabel("ID:"))
        cam_settings_layout.addWidget(self._camera_id_input)

        # 置信度
        self._confidence_spin = QDoubleSpinBox()
        self._confidence_spin.setRange(0.0, 1.0)
        self._confidence_spin.setSingleStep(0.05)
        from ..core.settings import get_settings_manager

        self._confidence_spin.setValue(
            get_settings_manager().settings.detection.confidence_threshold
        )
        self._confidence_spin.setMaximumWidth(80)
        cam_settings_layout.addWidget(QLabel("置信度:"))
        cam_settings_layout.addWidget(self._confidence_spin)
        # 置信度变化时自动保存
        self._confidence_spin.valueChanged.connect(self._on_confidence_changed)

        self._fps_spin = QDoubleSpinBox()
        self._fps_spin.setRange(1, 60)
        self._fps_spin.setValue(2)
        self._fps_spin.setSingleStep(1.0)
        self._fps_spin.setToolTip("相机预览帧率")
        cam_settings_layout.addWidget(QLabel("显示帧率:"))
        cam_settings_layout.addWidget(self._fps_spin)

        cam_settings_layout.addStretch()
        self._frame_count = 0

        control_layout.addWidget(cam_settings_group)

        # 按钮
        self._start_btn = QPushButton("▶ 开始预览")
        self._start_btn.setMinimumWidth(100)
        self._start_btn.clicked.connect(self._on_start_clicked)
        control_layout.addWidget(self._start_btn)

        self._scan_btn = QPushButton("🔍 扫描相机")
        self._scan_btn.clicked.connect(self._on_scan_clicked)
        control_layout.addWidget(self._scan_btn)

        self._capture_btn = QPushButton("📸 拍照检测")
        self._capture_btn.setEnabled(False)
        self._capture_btn.clicked.connect(self._on_capture_clicked)
        control_layout.addWidget(self._capture_btn)

        self._save_btn = QPushButton("💾 保存")
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._on_save_clicked)
        control_layout.addWidget(self._save_btn)

        layout.addLayout(control_layout)

        # 状态标签
        self._status_label = QLabel("未连接")
        self._status_label.setStyleSheet("padding: 4px;")
        layout.addWidget(self._status_label)

    def _on_start_clicked(self) -> None:
        """处理开始/停止按钮点击。"""
        if self._realtime_previewing:
            self._stop_preview()
        else:
            self._start_preview()

    def _on_confidence_changed(self, value: float) -> None:
        """置信度变化时自动保存到设置。"""
        from ..core.settings import get_settings_manager

        settings_mgr = get_settings_manager()
        settings_mgr.set("detection.confidence_threshold", value)

    def _start_preview(self) -> None:
        """启动实时预览。"""
        # 清空检测结果列表
        self._detection_history = []
        self._detection_times = []
        self._results_table.setRowCount(0)
        self._prev_gray = None
        self._is_trigger_active = False

        # 延迟导入避免循环依赖
        from ..utils.industrial_camera import (
            create_camera,
            CameraConfig,
            TriggerMode,
        )
        from ..core.settings import get_settings_manager

        # 获取设置
        settings = get_settings_manager().settings.camera

        # 相机配置
        camera_type = "usb" if self._camera_type_combo.currentIndex() == 0 else "gige"
        camera_id = self._camera_id_input.text() or "0"

        camera_config = CameraConfig(
            camera_type=camera_type,
            camera_id=camera_id,
            resolution=(settings.resolution_width, settings.resolution_height),
            exposure=settings.exposure_us,
            gain=settings.gain,
            trigger_mode=TriggerMode.CONTINUOUS,
            timeout_ms=settings.timeout_ms,
        )

        try:
            self._realtime_camera = create_camera(camera_config)

            if not self._realtime_camera.connect():
                QMessageBox.warning(self, "错误", f"无法连接相机 {camera_id}")
                return

            if not self._realtime_camera.start_streaming():
                QMessageBox.warning(self, "错误", "无法启动采集")
                self._realtime_camera.disconnect()
                return

            self._realtime_previewing = True
            self._start_btn.setText("⏹ 停止预览")
            self._capture_btn.setEnabled(True)
            self._save_btn.setEnabled(True)

            device_info = self._realtime_camera.get_device_info()
            if device_info:
                self._status_label.setText(f"已连接: {device_info.device_name}")
            else:
                self._status_label.setText("预览中...")

            # 启动定时器
            self._realtime_timer = QTimer()
            self._realtime_timer.timeout.connect(self._update_frame)
            fps_limit = self._fps_spin.value()
            interval = int(1000 / fps_limit) if fps_limit > 0 else 30
            self._realtime_timer.start(interval)
            logger.info(f"相机预览帧率: {fps_limit} FPS (刷新间隔 {interval}ms)")

        except Exception as e:
            QMessageBox.warning(self, "错误", f"连接失败: {e}")

    def _stop_preview(self) -> None:
        """停止实时预览。"""
        self._realtime_previewing = False

        if self._realtime_timer is not None:
            self._realtime_timer.stop()
            self._realtime_timer = None

        if self._realtime_camera is not None:
            self._realtime_camera.stop_streaming()
            self._realtime_camera.disconnect()
            self._realtime_camera = None

        self._start_btn.setText("▶ 开始预览")
        self._capture_btn.setEnabled(False)
        self._save_btn.setEnabled(False)
        self._status_label.setText("未连接")
        self._preview_label.setText("点击'开始预览'连接摄像头")

    def _update_frame(self) -> None:
        """更新实时帧。"""
        if not self._realtime_previewing:
            return

        if self._realtime_camera is None:
            return

        frame = self._realtime_camera.get_frame()
        if frame is None:
            return

        self._current_frame = frame
        self._frame_count += 1

        # 只显示画面，不自动检测（手动触发模式）
        self._status_label.setText("预览中... 点击'拍照检测'按钮执行检测")

        # 显示
        self._display_frame(frame)

    def _display_frame(self, frame: np.ndarray) -> None:
        """显示帧。"""
        import cv2

        if not self._current_detections:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            scaled = pixmap.scaled(
                self._preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._preview_label.setPixmap(scaled)
            return

        # 有检测结果时，使用 PIL 绘制中文
        from PIL import Image, ImageDraw, ImageFont

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb)
        draw = ImageDraw.Draw(pil_image)

        try:
            font = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 14)
        except Exception:
            font = ImageFont.load_default()

        for det in self._current_detections:
            x1, y1, x2, y2 = det.bbox
            color = (0, 255, 0)
            draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=2)
            text = f"{det.defect_type.display_name} {det.confidence:.0%}"
            draw.text((x1, y1 - 10), text, font=font, fill=color)

        # 转回 BGR 再显示
        display = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        # 转为 QPixmap
        rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)

        scaled = pixmap.scaled(
            self._preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._preview_label.setPixmap(scaled)

    def _run_detection(self, frame: np.ndarray) -> None:
        """运行实时检测。"""
        if self._detector is None:
            logger.info("detector 未设置")
            return

        # 延迟导入
        import cv2

        start_time = time.time()

        confidence = self._confidence_spin.value()
        original_conf = self._detector.confidence_threshold
        self._detector.confidence_threshold = confidence

        result = self._detector.detect(frame)

        self._detector.confidence_threshold = original_conf

        # 计算耗时
        elapsed_ms = (time.time() - start_time) * 1000
        self._processing_time_ms = elapsed_ms

        # 转换为UI结果
        if self._result_handler:
            self._current_detections = self._result_handler.convert_to_ui_result(
                result.detections
            )
        else:
            # 如果没有 result_handler，直接使用原始结果
            self._current_detections = []
            for det in result.detections:
                self._current_detections.append(
                    DetectionResult(
                        bbox=det.bbox,
                        confidence=det.confidence,
                        defect_type=det.defect_type,
                        class_id=det.class_id,
                    )
                )

        # 去重：与上一帧对比，过滤位置接近且类型相同的
        self._deduplicate_detections()

        # Pass/Fail 判定
        count = len(self._current_detections)
        self._detection_count = count

        # 检查并自动切换班次
        self._check_shift_change()

        # 获取关键缺陷列表
        from ..core.settings import get_settings_manager

        settings = get_settings_manager().settings

        critical_types = settings.industrial.critical_defects
        has_critical = any(
            det.defect_type.value in critical_types for det in self._current_detections
        )

        is_pass = count <= settings.industrial.pass_threshold and not (
            settings.industrial.fail_on_critical and has_critical
        )

        # 更新 Pass/Fail 显示
        self._update_result_display(is_pass, count)

        # 更新统计
        if is_pass:
            self._stats_manager.record_pass()
            self._alarm.trigger_pass()
        else:
            defect_types = [det.defect_type.value for det in self._current_detections]
            self._stats_manager.record_fail(defect_types)
            # 触发报警
            if count >= settings.industrial.alarm_on_defect_count:
                self._alarm.trigger_alarm()

            # 自动保存缺陷图像
            if (
                settings.industrial.save_original_images
                or settings.industrial.save_marked_images
            ):
                self._save_defect_images(frame, self._current_detections)

        # 更新统计看板
        self._update_statistics_display()

        # 更新检测结果列表（只有缺陷且与上一帧不同时才添加）
        def list_diff(a: list, b: list) -> bool:
            if len(a) != len(b):
                return True
            for x, y in zip(a, b):
                if x.bbox != y.bbox or x.defect_type != y.defect_type:
                    return True
            return False

        if self._current_detections and list_diff(self._current_detections, self._prev_detections[:]):
            self._detection_history.append(self._current_detections[:])
            self._detection_times.append(datetime.now().strftime("%H:%M:%S"))

            if len(self._detection_history) > 10:
                self._detection_history.pop(0)
                self._detection_times.pop(0)

            # 更新检测结果表格（不保存到本地，等设置保存）
            self._results_table.setRowCount(len(self._detection_history))
            for i, (dets, tm) in enumerate(zip(self._detection_history, self._detection_times)):
                self._results_table.setItem(
                    i, 0, QTableWidgetItem(tm)
                )
                self._results_table.setItem(
                    i, 1, QTableWidgetItem("")
                )
                self._results_table.setItem(
                    i, 2, QTableWidgetItem(f"{len(dets)}")
                )
                max_conf = max((d.confidence for d in dets), default=0.0)
                self._results_table.setItem(
                    i, 3, QTableWidgetItem(f"{max_conf:.0%}")
                )
                self._results_table.setItem(
                    i, 4, QTableWidgetItem("FAIL")
                )
            logger.info(f"检测到缺陷: {len(self._current_detections)} 个")

        # 保存当前检测结果用于下一帧去重
        self._prev_detections = self._current_detections[:]

        # 保存到历史记录（包含生产线、工位、班次、结果）
        self._save_to_history(frame, is_pass, elapsed_ms)

        # 更新状态
        self._status_label.setText(
            f"检测到 {count} 个缺陷 | 耗时: {elapsed_ms:.0f}ms"
            if count > 0
            else f"未检测到缺陷 | 耗时: {elapsed_ms:.0f}ms"
        )

        # 发送信号
        self.detection_completed.emit(self._current_detections)

    def _update_result_display(self, is_pass: bool, count: int) -> None:
        """更新 Pass/Fail 大字显示。"""
        if is_pass:
            self._result_display.setText("●●● PASS ●●●")
            self._result_display.setStyleSheet(
                "background-color: #22C55E; color: #FFFFFF; "
                "font-size: 72px; font-weight: bold; border-radius: 8px;"
            )
            self._last_result = "PASS"
        else:
            self._result_display.setText("●●● FAIL ●●●")
            self._result_display.setStyleSheet(
                "background-color: #EF4444; color: #FFFFFF; "
                "font-size: 72px; font-weight: bold; border-radius: 8px;"
            )
            self._last_result = "FAIL"

        # 更新详情
        self._defect_count_label.setText(f"缺陷数: {count}")

        # 置信度
        if self._current_detections:
            max_conf = max(det.confidence for det in self._current_detections)
            self._confidence_label.setText(f"置信度: {max_conf:.0%}")
        else:
            self._confidence_label.setText("置信度: --")

        # 耗时
        self._time_label.setText(f"耗时: {self._processing_time_ms:.0f}ms")

    def _update_statistics_display(self) -> None:
        """更新统计看板显示。"""
        stats = self._stats_manager.get_today_stats()
        self._today_total_label.setText(f"总计: {stats.total_count}")
        self._today_pass_label.setText(f"良品: {stats.pass_count}")
        self._today_fail_label.setText(f"不良品: {stats.fail_count}")
        self._today_rate_label.setText(f"良率: {stats.pass_rate:.1f}%")

    def _save_defect_images(
        self, frame: np.ndarray, detections: list[DetectionResult]
    ) -> None:
        """自动保存缺陷图像到本地文件夹。"""
        import cv2
        from pathlib import Path
        from ..core.settings import get_settings_manager

        settings = get_settings_manager().settings
        data_dir = Path.home() / "PCB-AI-Data" / "defects"
        data_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"defect_{timestamp}"

        # 保存原始图像
        if settings.industrial.save_original_images:
            orig_path = data_dir / f"{base_name}_original.png"
            cv2.imwrite(str(orig_path), frame)

        # 保存标注图像
        if settings.industrial.save_marked_images:
            marked = frame.copy()
            for det in detections:
                x1, y1, x2, y2 = det.bbox
                color = (0, 0, 255)  # 红色
                cv2.rectangle(marked, (x1, y1), (x2, y2), color, 2)
                text = f"{det.defect_type.display_name} {det.confidence:.0%}"
                cv2.putText(
                    marked, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2
                )
            marked_path = data_dir / f"{base_name}_marked.png"
            cv2.imwrite(str(marked_path), marked)

    def _save_to_history(
        self, frame: np.ndarray, is_pass: bool, processing_time_ms: float
    ) -> None:
        """保存检测记录到历史数据库。"""
        import cv2
        from pathlib import Path
        from ..core.history import get_history_manager
        from ..core.settings import get_settings_manager

        # 获取设置
        settings = get_settings_manager().settings

        # 保存原始图像和标注图像
        original_image_path = ""
        marked_image_path = ""

        # 根据设置决定是否保存图像
        save_original = settings.industrial.save_original_images
        save_marked = settings.industrial.save_marked_images

        if save_original or save_marked:
            data_dir = Path.home() / "PCB-AI-Data" / "detections"
            data_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"realtime_{timestamp}"

            # 保存原始图像
            if save_original:
                original_image_path = str(data_dir / f"{base_filename}_original.png")
                cv2.imwrite(original_image_path, frame)

            # 保存标注图像
            if save_marked:
                display = frame.copy()
                for det in self._current_detections:
                    x1, y1, x2, y2 = det.bbox
                    color = (0, 0, 255)
                    cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
                # 使用PIL绘制中文
                from PIL import Image, ImageDraw, ImageFont

                pil_img = Image.fromarray(display)
                draw = ImageDraw.Draw(pil_img)
                try:
                    font = ImageFont.truetype("msyh.ttc", 15)
                except Exception:
                    font = ImageFont.load_default()
                for det in self._current_detections:
                    x1, y1, x2, y2 = det.bbox
                    text = f"{det.defect_type.display_name} {det.confidence:.0%}"
                    draw.text((x1, max(0, y1 - 20)), text, fill=color, font=font)
                display = np.array(pil_img)
                marked_image_path = str(data_dir / f"{base_filename}_marked.png")
                cv2.imwrite(marked_image_path, display)

        # 保存记录
        history_mgr = get_history_manager()
        history_mgr.add_detection(
            image_path=original_image_path,  # 保存原始图像路径
            defects=self._current_detections,
            confidence_threshold=self._confidence_spin.value(),
            processing_time_ms=processing_time_ms,
            device="实时检测",
            marked_image_path=marked_image_path,
            production_line=settings.industrial.production_line,
            station_name=self._station_combo.currentText(),
            shift_config=self._shift_combo.currentText(),
            result="PASS" if is_pass else "FAIL",
        )

    def _on_report_clicked(self) -> None:
        """报表按钮点击 - 显示班次/日报表选项。"""
        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self)
        menu.addAction("📊 班次报表", self._export_shift_report)
        menu.addAction("📅 日报表", self._export_daily_report)
        menu.exec(self._report_btn.mapToGlobal(self._report_btn.rect().bottomLeft()))

    def _export_shift_report(self) -> None:
        """导出班次报表。"""
        from ..reports.report_generator import ReportGenerator
        from ..core.settings import get_settings_manager, ReportSettings
        from ..core.history import HistoryManager

        settings_mgr = get_settings_manager()
        shift = self._shift_manager.current_shift

        if shift is None:
            QMessageBox.warning(self, "报表", "无班次数据")
            return

        # 从历史记录获取班次数据
        history_mgr = HistoryManager()
        records = history_mgr.query_by_shift(shift.name)

        if not records:
            QMessageBox.information(self, "报表", f"班次 [{shift.name}] 暂无检测记录")
            return

        # 生成报表
        try:
            generator = ReportGenerator(ReportSettings())
            output_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存班次报表",
                f"班次报表_{shift.name}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                "Excel Files (*.xlsx)",
            )

            if output_path:
                generator.generate_shift_report(
                    records=records,
                    shift_name=shift.name,
                    output_path=output_path,
                )
                QMessageBox.information(
                    self, "报表", f"班次报表已保存至:\n{output_path}"
                )
        except Exception as e:
            QMessageBox.warning(self, "报表", f"生成报表失败: {e}")

    def _export_daily_report(self) -> None:
        """导出日报表。"""
        from ..reports.report_generator import ReportGenerator
        from ..core.settings import get_settings_manager, ReportSettings
        from ..core.history import HistoryManager

        today = datetime.now().strftime("%Y-%m-%d")

        # 从历史记录获取今日数据
        history_mgr = HistoryManager()
        records = history_mgr.query_by_date(today)

        if not records:
            QMessageBox.information(self, "报表", f"日期 [{today}] 暂无检测记录")
            return

        # 生成报表
        try:
            generator = ReportGenerator(ReportSettings())
            output_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存日报表",
                f"日报表_{today}.xlsx",
                "Excel Files (*.xlsx)",
            )

            if output_path:
                generator.generate_daily_report(
                    records=records,
                    date=today,
                    output_path=output_path,
                )
                QMessageBox.information(self, "报表", f"日报表已保存至:\n{output_path}")
        except Exception as e:
            QMessageBox.warning(self, "报表", f"生成报表失败: {e}")

    def _on_history_clicked(self) -> None:
        """历史按钮点击 - 显示历史记录对话框。"""
        from .history_dialog import HistoryDialog

        dialog = HistoryDialog(self)
        dialog.exec()

    def _deduplicate_detections(self) -> None:
        """去重：与上一帧对比，过滤位置接近且类型相同的检测框。"""
        if not self._prev_detections or not self._current_detections:
            return

        threshold = 50  # 像素距离阈值
        new_detections = []

        for curr in self._current_detections:
            is_duplicate = False
            curr_center = (
                (curr.bbox[0] + curr.bbox[2]) / 2,
                (curr.bbox[1] + curr.bbox[3]) / 2,
            )

            for prev in self._prev_detections:
                if curr.defect_type != prev.defect_type:
                    continue

                prev_center = (
                    (prev.bbox[0] + prev.bbox[2]) / 2,
                    (prev.bbox[1] + prev.bbox[3]) / 2,
                )

                distance = (
                    (curr_center[0] - prev_center[0]) ** 2
                    + (curr_center[1] - prev_center[1]) ** 2
                ) ** 0.5

                if distance < threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                new_detections.append(curr)

        self._current_detections = new_detections

    def _check_shift_change(self) -> None:
        """检查并自动切换班次。"""
        new_shift = self._shift_manager.check_and_switch_shift()
        if new_shift:
            # 更新班次显示
            self._shift_combo.setCurrentText(new_shift.name)
            # 重置统计
            self._stats_manager.set_shift(
                new_shift.name, new_shift.start_time, new_shift.end_time
            )
            self._stats_manager.reset_shift()

    def _on_station_changed(self, text: str) -> None:
        """工位选择改变。"""
        from ..core.settings import get_settings_manager

        get_settings_manager().settings.industrial.station_name = text

    def _on_shift_changed(self, text: str) -> None:
        """班次选择改变。"""
        from ..core.settings import get_settings_manager

        get_settings_manager().settings.industrial.shift_config = text
        # 同步班次管理器
        self._shift_manager.set_shift_by_name(text)

    def _on_capture_clicked(self) -> None:
        """手动捕获并检测。"""
        if self._current_frame is None:
            return

        self._run_detection(self._current_frame)
        self._display_frame(self._current_frame)
        self.capture_requested.emit(self._current_frame)

    def _on_save_clicked(self) -> None:
        """保存当前帧。"""
        if self._current_frame is None:
            return

        from datetime import datetime
        import cv2

        filename = f"pcb_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path, _ = QFileDialog.getSaveFileName(
            self, "保存图片", filename, "PNG Files (*.png);;All Files (*)"
        )

        if path:
            cv2.imwrite(path, self._current_frame)
            QMessageBox.information(self, "保存成功", f"图片已保存到: {path}")
            self.save_requested.emit(self._current_frame)

    def _on_result_selected(self) -> None:
        """处理检测结果选择。"""
        row = self._results_table.currentRow()
        if 0 <= row < len(self._detection_history):
            detections = self._detection_history[row]
            self._defect_list.set_detections(detections)

    def _on_scan_clicked(self) -> None:
        """扫描可用相机。"""
        from ..utils.industrial_camera import discover_cameras

        self._status_label.setText("扫描中...")
        try:
            devices = discover_cameras()
            if devices:
                self._camera_id_input.setText(devices[0].device_id)
                self._status_label.setText(
                    f"找到 {len(devices)} 个相机: {devices[0].device_name}"
                )
            else:
                self._status_label.setText("未找到可用相机")
        except Exception as e:
            self._status_label.setText(f"扫描失败: {e}")

    def _on_load_clicked(self) -> None:
        """加载图片进行检测。"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图像",
            "",
            "图像文件 (*.jpg *.jpeg *.png *.bmp *.tiff);;所有文件 (*.*)",
        )

        if not file_path:
            return

        from PIL import Image

        # 加载图像
        img = Image.open(file_path)
        frame = np.array(img.convert("RGB"))

        # 确保有 3 通道
        if len(frame.shape) == 2:
            frame = np.stack([frame] * 3, axis=-1)

        self._current_frame = frame
        self._capture_btn.setEnabled(True)
        self._save_btn.setEnabled(True)

        # 显示图像
        self._display_frame(frame)
        self._status_label.setText(f"已加载: {Path(file_path).name}")

    # ==================== 公开方法 ====================

    def set_detector(self, detector: Optional["YOLODetector"]) -> None:
        """设置检测器。"""
        self._detector = detector

    def set_result_handler(self, handler: Optional["DetectionResultHandler"]) -> None:
        """设置结果处理器。"""
        self._result_handler = handler

    def get_current_frame(self) -> Optional[np.ndarray]:
        """获取当前预览帧。"""
        return self._current_frame

    def get_current_detections(self) -> list[DetectionResult]:
        """获取当前检测结果。"""
        return self._current_detections

    def stop(self) -> None:
        """停止相机（如果正在运行）。"""
        if self._realtime_previewing:
            self._stop_preview()

    def is_previewing(self) -> bool:
        """检查是否正在预览。"""
        return self._realtime_previewing
