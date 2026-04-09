"""
PCB AI Inspector 主应用程序窗口。

提供 PCB 缺陷检测的完整 UI，包括：
- 图像导入和预览（原始图 + 带标记图双面板）
- 使用 YOLO11 进行缺陷检测
- 结果可视化和列表
- 批量处理支持（表格展示检测结果）
- PDF/Excel 报告生成
- 完整的工业场景配置支持

注意: 大部分UI逻辑已拆分到以下模块：
- ManualDetectionPanel: 手动检测面板
- RealtimeDetectionPanel: 实时检测面板
- BatchDetectionHandler: 批量检测处理器
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from loguru import logger
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QIcon
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QStatusBar,
    QToolBar,
    QApplication,
    QMenuBar,
    QMenu,
    QFileDialog,
    QMessageBox,
    QTabWidget,
    QProgressBar,
    QPushButton,
)

from ..core.defect_types import MODEL_CLASS_MAPPING, DefectType
from ..core.history import HistoryManager, get_history_manager
from ..core.settings import DEFAULT_MODEL_PATH, DEFAULT_MODEL_PATH_RESOLVED, get_settings_manager
from ..models.detector import YOLODetector
from ..utils.device import get_device_info
from .defect_overlay import DetectionResult
from .manual_panel import ManualDetectionPanel
from .realtime_panel import RealtimeDetectionPanel
from .batch_handler import BatchDetectionHandler
from .detection_pipeline import DetectionPipeline, DetectionMode
from .detection_result_handler import DetectionResultHandler
from .settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    """
    Main application window for PCB AI Inspector.

    Layout:
        - Menu bar (File, Edit, View, Detection, Help)
        - Toolbar (common actions)
        - Central widget:
            - Tab 1: Manual Detection Panel
            - Tab 2: Realtime Detection Panel
        - Status bar (progress, status messages)
    """

    # 状态消息信号
    status_message = pyqtSignal(str)

    def __init__(self) -> None:
        """初始化主窗口。"""
        super().__init__()

        # 获取设置
        settings = get_settings_manager().settings

        # 使用配置设置窗口属性
        self.setWindowTitle(settings.ui_window.window_title)
        # 设置窗口 logo
        self._set_window_logo()
        self.setMinimumSize(settings.ui_window.min_width, settings.ui_window.min_height)

        # 如果设置启动最大化
        if settings.ui_window.start_maximized:
            self.showMaximized()

        # 如果窗口不可调整大小
        if not settings.ui_window.resizable:
            self.setFixedSize(self.minimumSize())

        # 设备信息
        self._device_info = get_device_info()
        device_name = self._device_info.device_name or "CPU"
        logger.info(f"设备: {device_name}")

        # 核心组件
        self._detector: Optional[YOLODetector] = None
        self._pipeline: Optional[DetectionPipeline] = None
        self._result_handler: DetectionResultHandler = DetectionResultHandler()
        self._history_manager: HistoryManager = get_history_manager()
        self._batch_handler: Optional[BatchDetectionHandler] = None

        # 当前图像和检测结果
        self._current_image: Optional[dict] = None
        self._current_detections: list[DetectionResult] = []

        # UI 状态
        self._is_detecting = False

        # 设置 UI
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_connections()

        # 加载模型
        self._load_model()

        # 初始化结果处理器
        self._result_handler.set_class_mapping(MODEL_CLASS_MAPPING)

        # 初始状态
        self._status_bar.showMessage("就绪")

    def _setup_ui(self) -> None:
        """设置用户界面。"""
        settings = get_settings_manager().settings

        # 中央小部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)

        # 创建页签窗口
        self._tab_widget = QTabWidget()
        main_layout.addWidget(self._tab_widget)

        # 页签1：手动检测
        self._manual_panel = ManualDetectionPanel(
            detector=None,  # 将在 _load_model 后设置
            result_handler=self._result_handler,
        )
        self._tab_widget.addTab(self._manual_panel, "📂 手动检测")

        # 页签2：实时检测
        self._realtime_panel = RealtimeDetectionPanel(
            detector=None,
            result_handler=self._result_handler,
        )
        self._tab_widget.addTab(self._realtime_panel, "📷 实时检测")

        # 状态栏
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        # 显示/隐藏状态栏
        if not settings.ui_layout.show_statusbar:
            self._status_bar.setVisible(False)

        # 状态栏中的进度条
        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximumWidth(200)
        self._progress_bar.setVisible(False)
        self._status_bar.addPermanentWidget(self._progress_bar)

    def _set_window_logo(self) -> None:
        """设置窗口 logo。"""
        from pathlib import Path

        # logo 路径：项目根目录下的 resources/logo.png
        base_dir = Path(__file__).parent.parent.parent.parent
        logo_path = base_dir / "resources" / "logo.png"

        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))

    def _setup_menu(self) -> None:
        """设置菜单栏 - 空菜单栏，所有功能在UI按钮上"""
        pass

    def _setup_toolbar(self) -> None:
        """设置工具栏。"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # 设置按钮
        self._settings_btn = QPushButton("⚙ 设置")
        self._settings_btn.clicked.connect(self._on_settings)
        toolbar.addWidget(self._settings_btn)

        # 关于按钮
        self._about_btn = QPushButton("ℹ 关于")
        self._about_btn.clicked.connect(self._on_about)
        toolbar.addWidget(self._about_btn)

        toolbar.addSeparator()

        # 取消按钮（默认隐藏）
        self._cancel_btn = QPushButton("⏹ 取消")
        self._cancel_btn.clicked.connect(self._on_cancel_detection)
        self._cancel_btn.setVisible(False)
        toolbar.addWidget(self._cancel_btn)

    def _setup_connections(self) -> None:
        """设置信号连接。"""
        # 手动面板信号
        self._manual_panel.detect_requested.connect(self._on_detect_clicked)
        self._manual_panel.cancel_requested.connect(self._on_cancel_detection)
        self._manual_panel.image_selected.connect(self._on_image_selected)
        self._manual_panel.open_file_requested.connect(self._on_open_image)
        self._manual_panel.open_folder_requested.connect(self._on_open_folder)
        self._manual_panel.files_dropped.connect(self._on_files_dropped)
        self._manual_panel.report_requested.connect(self._on_save_report)
        self._manual_panel.history_requested.connect(self._on_show_history)

        # 实时面板信号
        self._realtime_panel.detection_completed.connect(
            self._on_realtime_detection_completed
        )

    def _load_model(self) -> None:
        """加载 YOLO 模型。"""
        try:
            self._status_bar.showMessage("正在加载模型...")
            QApplication.processEvents()

            # 获取模型路径
            model_path = self._get_model_path()

            if model_path and model_path.exists():
                # 从设置中读取预处理配置
                settings_manager = get_settings_manager(force_reload=True)
                enable_preprocessing = (
                    settings_manager.settings.preprocessing.enable_preprocessing
                )

                self._detector = YOLODetector(
                    str(model_path),
                    enable_preprocessing=enable_preprocessing,
                )

                # 创建 pipeline
                self._pipeline = DetectionPipeline(model_path)
                self._pipeline.load_model()

                # 创建批量处理器
                self._batch_handler = BatchDetectionHandler(
                    pipeline=self._pipeline,
                    result_handler=self._result_handler,
                )
                self._connect_batch_handler_signals()

                # 更新面板的检测器引用
                self._manual_panel.set_detector(self._detector)
                self._realtime_panel.set_detector(self._detector)

                logger.info(f"模型已加载: {model_path}")
                device_name = self._device_info.device_name or "CPU"
                self._status_bar.showMessage(f"模型已加载 ({device_name})")
            else:
                logger.warning("未找到模型。检测功能将被禁用。")
                self._status_bar.showMessage("警告: 未找到模型文件，请先训练模型")

        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            self._status_bar.showMessage(f"模型加载失败: {e}")
            QMessageBox.warning(
                self,
                "模型加载失败",
                f"无法加载模型: {e}\n\n请确保已训练模型并放置在正确位置。",
            )

    def _connect_batch_handler_signals(self) -> None:
        """连接批量处理器的信号。"""
        if self._batch_handler is None:
            return

        self._batch_handler.signals.progress_updated.connect(self._on_batch_progress)
        self._batch_handler.signals.task_completed.connect(
            self._on_batch_task_completed
        )
        self._batch_handler.signals.task_failed.connect(self._on_batch_task_failed)
        self._batch_handler.signals.batch_completed.connect(self._on_batch_completed)
        self._batch_handler.signals.batch_cancelled.connect(self._on_batch_cancelled)

    def _get_model_path(self) -> Optional[Path]:
        """获取模型路径，检查默认路径。"""
        model_path = Path(DEFAULT_MODEL_PATH_RESOLVED)
        if model_path.exists():
            logger.info(f"找到模型: {model_path}")
            return model_path

        logger.warning(f"未找到模型: {model_path}")
        return None

    # ==================== 事件处理 ====================

    def _on_open_image(self) -> None:
        """处理打开图像操作。"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "打开图像",
            "",
            "图像文件 (*.jpg *.jpeg *.png *.bmp *.tiff *.tif);;所有文件 (*.*)",
        )

        if file_path:
            self._load_image(Path(file_path))

    def _on_open_folder(self) -> None:
        """处理打开文件夹操作。"""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "选择文件夹",
            "",
            QFileDialog.Option.ShowDirsOnly,
        )

        if folder_path:
            if self._pipeline is None:
                QMessageBox.warning(self, "模型未加载", "请先训练模型")
                return

            image_paths = self._pipeline.scan_directory(Path(folder_path))

            if not image_paths:
                QMessageBox.information(
                    self, "无图像", "所选文件夹中未找到支持的图像文件"
                )
                return

            # 加载第一张图像用于预览
            self._load_image(image_paths[0])

            # 询问是否进行批量检测
            reply = QMessageBox.question(
                self,
                "批量检测",
                f"文件夹中有 {len(image_paths)} 个图像文件。\n\n是否进行批量检测?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self._start_batch_detection(image_paths)

    def _on_files_dropped(self, file_paths: list[str]) -> None:
        """处理拖拽文件事件。

        Args:
            file_paths: 拖拽的文件路径列表
        """
        if not file_paths:
            return

        # 加载第一张图像用于预览
        self._load_image(Path(file_paths[0]))

    def _load_image(self, image_path: Path) -> None:
        """从路径加载图像。"""
        try:
            image = cv2.imread(str(image_path))
            if image is None:
                raise ValueError(f"加载图像失败: {image_path}")

            self._current_image = {"path": image_path, "image": image}
            self._current_detections.clear()

            # 加载到手动面板
            self._manual_panel.load_image(image_path, image)

            # 更新状态
            self._status_bar.showMessage(f"已加载: {image_path.name}")
            logger.info(f"已加载图像: {image_path}")

        except Exception as e:
            logger.error(f"加载图像失败: {e}")
            QMessageBox.critical(self, "加载失败", f"无法加载图像:\n{e}")

    def _on_image_selected(
        self, image_path: str, detections: list, marked_image: object
    ) -> None:
        """处理图像选择。"""
        pass  # 可用于更新其他UI状态

    def _on_detect_clicked(self) -> None:
        """处理检测按钮点击。"""
        if self._current_image is None:
            QMessageBox.information(self, "提示", "请先打开图像")
            return

        if self._is_detecting:
            return

        if self._detector is None:
            QMessageBox.warning(self, "模型未加载", "请先训练模型")
            return

        self._start_detection()

    def _start_detection(self) -> None:
        """开始检测过程。"""
        # 清除上一次的检测数据
        self._current_detections.clear()
        self._manual_panel.clear_results()

        self._is_detecting = True
        self._manual_panel._detect_btn.setEnabled(False)
        self._cancel_btn.setVisible(True)
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)
        self._status_bar.showMessage("正在检测...")

        start_time = time.time()

        try:
            if self._current_image is None:
                raise ValueError("未加载图像")

            image = self._current_image["image"]
            image_path = self._current_image["path"]
            confidence = self._manual_panel.get_confidence()

            # 设置检测器的置信度阈值
            if self._detector is None:
                raise ValueError("检测器未加载")
            self._detector.set_confidence_threshold(confidence)

            # 运行检测
            result = self._detector.detect(image)

            # 计算处理时间
            processing_time_ms = (time.time() - start_time) * 1000

            # 使用结果处理器转换检测结果
            self._current_detections = self._result_handler.convert_to_ui_result(
                result.detections
            )

            # 生成带标记的图像
            marked_image = None
            if self._current_image and self._current_image["image"] is not None:
                marked_image = self._current_image["image"]

                # 显示在手动面板
                self._manual_panel.display_detections(
                    image_path, self._current_detections, marked_image
                )

            # 保存到历史记录
            self._save_to_history(processing_time_ms)

            # 更新状态
            defect_count = len(self._current_detections)
            self._status_bar.showMessage(f"检测完成: 发现 {defect_count} 个缺陷")

            logger.info(f"检测完成: 发现 {defect_count} 个缺陷")

            # 打印 YOLO 格式的标注（方便验证）
            if result.detections:
                logger.info("YOLO 格式标注:")
                for det in result.detections:
                    x1, y1, x2, y2 = det.bbox
                    cx = (x1 + x2) / 2 / result.width
                    cy = (y1 + y2) / 2 / result.height
                    w = (x2 - x1) / result.width
                    h = (y2 - y1) / result.height
                    class_id = list(MODEL_CLASS_MAPPING.keys())[
                        list(MODEL_CLASS_MAPPING.values()).index(det.defect_type)
                    ]
                    logger.info(
                        f"  {class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"
                    )

        except Exception as e:
            logger.error(f"检测失败: {e}")
            self._status_bar.showMessage(f"检测失败: {e}")
            QMessageBox.critical(self, "检测失败", f"检测过程出错:\n{e}")

        finally:
            self._is_detecting = False
            self._manual_panel._detect_btn.setEnabled(True)
            self._cancel_btn.setVisible(False)
            self._progress_bar.setVisible(False)

    def _on_cancel_detection(self) -> None:
        """处理取消检测。"""
        if self._batch_handler and self._batch_handler.is_running():
            self._batch_handler.cancel()
        if self._pipeline:
            self._pipeline.cancel()
        self._status_bar.showMessage("已取消")

    def _start_batch_detection(self, image_paths: list[Path]) -> None:
        """开始批量检测。"""
        if self._pipeline is None or self._batch_handler is None:
            return

        self._is_detecting = True
        self._manual_panel._detect_btn.setEnabled(False)
        self._cancel_btn.setVisible(True)
        self._progress_bar.setVisible(True)
        self._progress_bar.setMaximum(len(image_paths))
        self._status_bar.showMessage("正在批量检测...")

        # 清空之前的结果
        self._manual_panel.clear_results()

        # 启动批量检测
        self._batch_handler.start_batch(
            image_paths,
            confidence=self._manual_panel.get_confidence(),
        )

    def _on_batch_progress(self, current: int, total: int, image_name: str) -> None:
        """处理批量进度更新。"""
        self._progress_bar.setValue(current)
        self._status_bar.showMessage(f"正在检测: {image_name} ({current}/{total})")

    def _on_batch_task_completed(
        self,
        image_name: str,
        detections: list,
        original_image: object,
        marked_image: object,
    ) -> None:
        """处理批量任务完成。"""
        self._manual_panel.add_result_to_table(image_name, detections)

    def _on_batch_task_failed(self, image_name: str, error_message: str) -> None:
        """处理批量任务失败。"""
        # 添加失败行到表格
        pass  # 批量处理器已处理

    def _on_batch_completed(self, result) -> None:
        """处理批量检测完成。"""
        self._is_detecting = False
        self._manual_panel._detect_btn.setEnabled(True)
        self._cancel_btn.setVisible(False)
        self._progress_bar.setVisible(False)

        # 更新手动面板的结果
        if self._batch_handler:
            self._manual_panel.set_results(self._batch_handler.get_all_results())

        # 显示摘要
        summary = (
            f"批量检测完成\n\n"
            f"总图像数: {result.total_images}\n"
            f"成功: {result.successful}\n"
            f"失败: {result.failed}\n"
            f"总缺陷数: {result.total_defects}\n"
            f"用时: {result.processing_time_seconds:.1f}秒"
        )

        self._status_bar.showMessage(
            f"批量检测完成: {result.successful}/{result.total_images} 成功"
        )
        QMessageBox.information(self, "检测完成", summary)

        # 启用批量导出按钮
        if self._batch_handler and self._batch_handler.get_all_results():
            self._save_all_reports_action.setEnabled(True)

    def _on_batch_cancelled(self) -> None:
        """处理批量检测取消。"""
        self._is_detecting = False
        self._manual_panel._detect_btn.setEnabled(True)
        self._cancel_btn.setVisible(False)
        self._progress_bar.setVisible(False)
        self._status_bar.showMessage("批量检测已取消")

    def _on_clear_results(self) -> None:
        """清空检测结果。"""
        self._current_detections.clear()
        self._manual_panel.clear_results()
        self._status_bar.showMessage("已清除结果")

    def _on_realtime_detection_completed(self, detections: list) -> None:
        """处理实时检测完成。"""
        pass  # 实时面板已处理UI更新

    def _save_to_history(self, processing_time_ms: float) -> None:
        """将检测结果保存到历史记录。"""
        if self._current_image is None:
            return

        try:
            from datetime import datetime
            from pathlib import Path
            import cv2
            from ..core.settings import get_settings_manager

            settings = get_settings_manager().settings

            # 保存原始图像和标注图像
            original_image_path = ""
            marked_image_path = ""

            save_original = settings.industrial.save_original_images
            save_marked = settings.industrial.save_marked_images

            if save_original or save_marked:
                data_dir = Path.home() / "PCB-AI-Data" / "detections"
                data_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_filename = f"manual_{timestamp}"

                img = self._current_image.get("image")
                if img is not None:
                    # 保存原始图像
                    if save_original:
                        original_image_path = str(
                            data_dir / f"{base_filename}_original.png"
                        )
                        cv2.imwrite(original_image_path, img)

                    # 保存标注图像
                    if save_marked:
                        display = img.copy()
                        for det in self._current_detections:
                            x1, y1, x2, y2 = det.bbox
                            color = (0, 0, 255)
                            cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
                            # 使用PIL绘制中文
                            from PIL import Image, ImageDraw, ImageFont

                            pil_img = Image.fromarray(display)
                            draw = ImageDraw.Draw(pil_img)
                            # 使用系统默认中文字体
                            try:
                                font = ImageFont.truetype("msyh.ttc", 15)
                            except Exception:
                                font = ImageFont.load_default()
                            text = (
                                f"{det.defect_type.display_name} {det.confidence:.0%}"
                            )
                            draw.text(
                                (x1, max(0, y1 - 20)), text, fill=color, font=font
                            )
                            display = np.array(pil_img)
                        marked_image_path = str(
                            data_dir / f"{base_filename}_marked.png"
                        )
                        cv2.imwrite(marked_image_path, display)

            # 手动检测不强制要求生产线/工位/班次（用于质检/复核场景）
            # 结果字段仍需记录
            self._history_manager.add_detection(
                image_path=original_image_path or str(self._current_image["path"]),
                defects=self._current_detections,
                confidence_threshold=self._manual_panel.get_confidence(),
                processing_time_ms=processing_time_ms,
                device=self._device_info.device_name or "CPU",
                marked_image_path=marked_image_path,
                result="FAIL" if self._current_detections else "PASS",
            )
            logger.debug("检测结果已保存到历史记录")
        except Exception as e:
            logger.warning(f"保存到历史记录失败: {e}")

    def _on_save_report(self) -> None:
        """处理保存报告操作。"""
        if not self._current_detections:
            QMessageBox.information(self, "提示", "没有可保存的检测结果")
            return

        try:
            from .report_preview_dialog import ReportPreviewDialog

            image_path = self._current_image["path"] if self._current_image else None
            dialog = ReportPreviewDialog(
                detections=self._current_detections,
                image_path=image_path,
                parent=self,
            )
            dialog.exec()

        except ImportError:
            QMessageBox.information(
                self,
                "功能开发中",
                "报告生成功能正在开发中。",
            )
        except Exception as e:
            logger.error(f"保存报告失败: {e}")
            QMessageBox.critical(self, "保存失败", f"无法保存报告:\n{e}")

    def _on_save_batch_report(self) -> None:
        """处理批量导出所有报告操作。"""
        if self._batch_handler is None or not self._batch_handler.get_all_results():
            QMessageBox.information(self, "提示", "没有可保存的检测结果")
            return

        try:
            from .report_preview_dialog import BatchReportPreviewDialog

            dialog = BatchReportPreviewDialog(
                results=self._batch_handler.get_all_results(),
                parent=self,
            )
            dialog.exec()

        except ImportError:
            QMessageBox.information(
                self,
                "功能开发中",
                "报告生成功能正在开发中。",
            )
        except Exception as e:
            logger.error(f"保存批量报告失败: {e}")
            QMessageBox.critical(self, "保存失败", f"无法保存批量报告:\n{e}")

    def _on_settings(self) -> None:
        """处理设置操作。"""
        dialog = SettingsDialog(self)
        dialog.exec()
        logger.info("设置对话框已关闭")

        # 设置更改后重新加载模型
        if self._detector is not None:
            self._load_model()
            logger.info("模型已重新加载，新设置已生效")

    def _on_show_history(self) -> None:
        """处理历史记录操作。"""
        try:
            from .history_dialog import HistoryDialog

            dialog = HistoryDialog(self)
            dialog.exec()
            logger.info("历史记录对话框已关闭")
        except ImportError:
            history_manager = get_history_manager()
            stats = history_manager.get_statistics()
            QMessageBox.information(
                self,
                "检测历史",
                f"总检测次数: {stats.total_detections}\n"
                f"总缺陷数: {stats.total_defects}\n"
                f"平均每图缺陷数: {stats.average_defects_per_image:.1f}",
            )

    def _on_about(self) -> None:
        """处理关于操作。"""
        from pathlib import Path

        # 查找 logo - 项目根目录下的 resources/logo.png
        base_dir = Path(__file__).parent.parent.parent.parent
        logo_path = (
            base_dir / "resources" / "logo.png"
            if (base_dir / "resources" / "logo.png").exists()
            else None
        )

        # 构建关于文本
        about_text = (
            "<h3>PCB AI Inspector</h3>"
            "<p>版本 1.0.0</p>"
            "<p>基于 YOLO11 的 PCB 缺陷检测系统</p>"
            "<p>支持检测 10 种缺陷类型:</p>"
            "<ul>"
            f"<li>短路 (Short Circuit)</li>"
            f"<li>开路 (Open Circuit)</li>"
            f"<li>缺孔 (Missing Hole)</li>"
            f"<li>毛刺 (Spur)</li>"
            f"<li>鼠咬 (Mouse Bite)</li>"
            f"<li>多铜 (Spurious Copper)</li>"
            f"<li>孔 breakout (Hole Breakout)</li>"
            f"<li>导体划痕 (Conductor Scratch)</li>"
            f"<li>异物 (Foreign Object)</li>"
            f"<li>针孔 (Pin Hole)</li>"
            "</ul>"
            f"<p>设备: {self._device_info.device_name or 'CPU'}</p>"
        )

        # 如果有 logo，创建自定义对话框
        if logo_path:
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel
            from PyQt6.QtGui import QPixmap
            from PyQt6.QtCore import Qt

            dialog = QDialog(self)
            dialog.setWindowTitle("关于")
            dialog.setMinimumSize(400, 300)
            layout = QVBoxLayout(dialog)

            # Logo
            logo_label = QLabel()
            pixmap = QPixmap(str(logo_path))
            # 缩放 logo 到合适大小
            scaled_pixmap = pixmap.scaled(
                120,
                120,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(logo_label)

            # 文本
            text_label = QLabel(about_text)
            text_label.setTextFormat(Qt.TextFormat.RichText)
            text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(text_label)

            # 关闭按钮
            close_btn = QPushButton("确定")
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)

            dialog.exec()
        else:
            QMessageBox.about(self, "关于", about_text)

    def closeEvent(self, event) -> None:
        """处理窗口关闭事件。"""
        # 取消任何正在进行的检测
        if self._is_detecting:
            if self._batch_handler and self._batch_handler.is_running():
                self._batch_handler.cancel()
            if self._pipeline:
                self._pipeline.cancel()

        # 停止实时预览
        if self._realtime_panel.is_previewing():
            self._realtime_panel.stop()

        # 接受关闭
        event.accept()
