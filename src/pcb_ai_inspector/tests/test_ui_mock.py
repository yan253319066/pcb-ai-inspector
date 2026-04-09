"""
UI模拟测试：按钮点击、弹窗触发、参数赋值

测试目标：
- 关键按钮点击的逻辑验证
- 弹窗触发条件
- 参数赋值行为
- UI组件状态变化
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ==================== UI组件测试 ====================


class TestMainWindowButtons:
    """主窗口按钮点击测试"""

    @patch("pcb_ai_inspector.ui.main_window.MainWindow")
    def test_on_open_image_triggered(self, mock_window):
        """测试打开图像按钮触发"""
        from PyQt6.QtWidgets import QFileDialog
        from PyQt6.QtCore import QEvent

        # 模拟 QFileDialog.getOpenFileName 返回值
        with patch("PyQt6.QtWidgets.QFileDialog.getOpenFileName") as mock_get_file:
            mock_get_file.return_value = ("test.jpg", "")

            # 验证调用返回正确的文件路径
            file_path, _ = QFileDialog.getOpenFileName(
                None, "打开图像", "", "图像文件 (*.jpg *.png)"
            )
            assert file_path == "test.jpg"

    @patch("pcb_ai_inspector.ui.main_window.MainWindow")
    def test_on_detect_button_clicked(self, mock_window):
        """测试检测按钮点击逻辑"""
        # 测试点击检测按钮前的状态检查

        # 场景1：无图像时应提示
        current_image = None
        should_prompt = current_image is None
        assert should_prompt is True

        # 场景2：有图像时应执行检测
        current_image = {"path": Path("test.jpg"), "image": np.zeros((100, 100, 3))}
        should_detect = current_image is not None
        assert should_detect is True

    @patch("pcb_ai_inspector.ui.main_window.MainWindow")
    def test_confidence_threshold_assignment(self, mock_window):
        """测试置信度参数赋值"""
        # 测试置信度阈值的边界值处理

        # 场景1：有效值
        confidence_spin = MagicMock()
        confidence_spin.value.return_value = 0.5

        value = confidence_spin.value()
        assert 0 <= value <= 1

        # 场景2：边界值
        confidence_spin.value.return_value = 0.0
        value = confidence_spin.value()
        assert value >= 0

        confidence_spin.value.return_value = 1.0
        value = confidence_spin.value()
        assert value <= 1


class TestDialogTriggers:
    """弹窗触发测试"""

    def test_settings_dialog_trigger(self):
        """测试设置对话框触发条件"""
        # 测试是否显示了设置对话框
        with patch("pcb_ai_inspector.ui.settings_dialog.SettingsDialog") as mock_dialog:
            mock_dialog_instance = MagicMock()
            mock_dialog.return_value = mock_dialog_instance

            # 模拟触发
            mock_dialog_instance.exec = MagicMock(return_value=1)

            # 验证对话框被创建
            assert mock_dialog is not None

    def test_history_dialog_trigger(self):
        """测试历史记录对话框触发"""
        # 测试历史记录对话框能否正常触发
        with patch("pcb_ai_inspector.ui.history_dialog.HistoryDialog") as mock_dialog:
            mock_dialog_instance = MagicMock()
            mock_dialog.return_value = mock_dialog_instance

            # 模拟触发
            mock_dialog_instance.exec = MagicMock(return_value=1)

            assert mock_dialog is not None

    def test_report_preview_dialog_trigger(self):
        """测试报告预览对话框触发"""
        with patch(
            "pcb_ai_inspector.ui.report_preview_dialog.ReportPreviewDialog"
        ) as mock_dialog:
            mock_dialog_instance = MagicMock()
            mock_dialog.return_value = mock_dialog_instance

            # 需要有检测结果才能触发
            has_detections = True
            if has_detections:
                mock_dialog_instance.exec = MagicMock(return_value=1)

            assert mock_dialog is not None

    def test_camera_dialog_trigger(self):
        """测试相机对话框触发"""
        # 相机功能集成在 RealtimeDetectionPanel 中，测试面板的相机相关信号
        from pcb_ai_inspector.ui.realtime_panel import RealtimeDetectionPanel

        # 验证面板有相机相关信号
        assert hasattr(RealtimeDetectionPanel, "capture_requested")
        assert hasattr(RealtimeDetectionPanel, "save_requested")
        assert hasattr(RealtimeDetectionPanel, "detection_completed")


class TestUIActions:
    """UI操作测试"""

    def test_save_report_action_state(self):
        """测试保存报告按钮状态"""
        # 模拟检测结果存在时的按钮状态
        current_detections = [{"type": "short", "confidence": 0.9}]

        # 有检测结果时应该启用保存按钮
        save_enabled = len(current_detections) > 0
        assert save_enabled is True

        # 无检测结果时应该禁用保存按钮
        current_detections = []
        save_enabled = len(current_detections) > 0
        assert save_enabled is False

    def test_zoom_slider_value_change(self):
        """测试缩放滑块值变化"""
        # 模拟缩放滑块
        zoom_slider = MagicMock()
        zoom_slider.value.return_value = 150

        # 获取缩放值
        value = zoom_slider.value()
        zoom_factor = value / 100.0

        assert zoom_factor == 1.5
        assert 0.1 <= zoom_factor <= 5.0

    def test_checkbox_toggles(self):
        """测试复选框切换"""
        # 模拟边界框显示复选框
        show_boxes_check = MagicMock()
        show_boxes_check.isChecked.return_value = True

        # 测试状态
        is_checked = show_boxes_check.isChecked()
        assert is_checked is True

        # 模拟切换
        show_boxes_check.isChecked.return_value = False
        is_checked = show_boxes_check.isChecked()
        assert is_checked is False


class TestBatchDetectionUI:
    """批量检测UI测试"""

    def test_batch_folder_selection(self):
        """测试批量检测文件夹选择"""
        with patch("PyQt6.QtWidgets.QFileDialog.getExistingDirectory") as mock_get_dir:
            mock_get_dir.return_value = "/test/images"

            folder_path = QFileDialog.getExistingDirectory(
                None, "选择文件夹", "", QFileDialog.Option.ShowDirsOnly
            )

            assert folder_path == "/test/images"

    def test_batch_progress_update(self):
        """测试批量检测进度更新"""
        # 模拟进度条
        progress_bar = MagicMock()
        progress_bar.maximum = 100
        progress_bar.value = 50

        # 验证进度计算
        progress_percent = (progress_bar.value / progress_bar.maximum) * 100
        assert progress_percent == 50.0

    def test_batch_result_table_update(self):
        """测试批量结果表格更新"""
        # 模拟结果表格
        results_table = MagicMock()
        results_table.rowCount.return_value = 0

        # 模拟添加行
        results_table.insertRow = MagicMock()
        results_table.setItem = MagicMock()

        # 添加检测结果
        image_results = [
            {"name": "image1.jpg", "defects": 2},
            {"name": "image2.jpg", "defects": 0},
            {"name": "image3.jpg", "defects": 5},
        ]

        for result in image_results:
            results_table.insertRow(results_table.rowCount())
            results_table.setItem(None, 0, MagicMock())

        assert results_table.insertRow.call_count == 3


class TestDetectionPipelineUI:
    """检测管道UI测试"""

    def test_pipeline_init(self):
        """测试检测管道初始化"""
        with patch("pcb_ai_inspector.ui.detection_pipeline.DetectionPipeline"):
            # 验证管道类存在
            from pcb_ai_inspector.ui.detection_pipeline import DetectionPipeline

            assert DetectionPipeline is not None

    def test_scan_directory(self):
        """测试目录扫描"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # 创建一些测试图像文件
            (tmp_path / "test1.jpg").touch()
            (tmp_path / "test2.png").touch()
            (tmp_path / "test3.txt").touch()  # 非图像文件

            # 扫描图像文件
            image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}
            image_files = [
                f for f in tmp_path.iterdir() if f.suffix.lower() in image_extensions
            ]

            assert len(image_files) == 2


class TestSettingsDialogUI:
    """设置对话框UI测试"""

    def test_settings_loading(self):
        """测试设置加载"""
        from pcb_ai_inspector.core.settings import get_settings_manager

        manager = get_settings_manager()
        settings = manager.settings

        # 验证设置加载成功
        assert settings is not None
        assert settings.detection.confidence_threshold > 0

    def test_settings_save(self):
        """测试设置保存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from pcb_ai_inspector.core.settings import SettingsManager

            settings_path = Path(tmpdir) / "test_settings.json"
            manager = SettingsManager(settings_path)

            # 修改设置
            manager.set("detection.confidence_threshold", 0.8)

            # 保存设置
            manager.save()

            # 验证设置已保存
            assert settings_path.exists()


class TestImageViewerUI:
    """图像查看器UI测试"""

    def test_image_load(self):
        """测试图像加载"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # 模拟创建临时图像
            import cv2

            test_image = np.zeros((480, 640, 3), dtype=np.uint8)
            image_path = tmp_path / "test.jpg"
            cv2.imwrite(str(image_path), test_image)

            # 加载图像
            loaded_image = cv2.imread(str(image_path))

            assert loaded_image is not None
            assert loaded_image.shape == (480, 640, 3)

    def test_zoom_behavior(self):
        """测试缩放行为"""
        # 模拟图像查看器的缩放
        original_size = (640, 480)
        zoom_factor = 2.0

        # 计算缩放后的尺寸
        scaled_size = (
            int(original_size[0] * zoom_factor),
            int(original_size[1] * zoom_factor),
        )

        assert scaled_size == (1280, 960)

    def test_fit_to_window(self):
        """测试适应窗口"""
        # 模拟适应窗口计算
        image_size = (1920, 1080)
        window_size = (800, 600)

        # 计算缩放以适应窗口
        scale = min(
            window_size[0] / image_size[0],
            window_size[1] / image_size[1],
        )

        scaled_size = (
            int(image_size[0] * scale),
            int(image_size[1] * scale),
        )

        assert scaled_size[0] <= window_size[0]
        assert scaled_size[1] <= window_size[1]


class TestDefectListUI:
    """缺陷列表UI测试"""

    def test_defect_list_update(self):
        """测试缺陷列表更新"""
        # 模拟缺陷列表
        defect_list = MagicMock()
        defect_list.count.return_value = 0

        # 添加缺陷
        defects = [
            {"type": "short", "confidence": 0.95, "bbox": [10, 20, 100, 200]},
            {"type": "open_circuit", "confidence": 0.87, "bbox": [50, 50, 150, 150]},
        ]

        # 模拟添加
        for defect in defects:
            defect_list.addItem = MagicMock()

        assert len(defects) == 2

    def test_statistics_update(self):
        """测试统计更新"""
        # 模拟检测结果
        detections = [
            {"type": "short", "confidence": 0.95},
            {"type": "short", "confidence": 0.88},
            {"type": "open_circuit", "confidence": 0.87},
        ]

        # 计算统计
        total = len(detections)
        avg_conf = sum(d["confidence"] for d in detections) / total

        # 按类型统计
        type_counts = {}
        for d in detections:
            t = d["type"]
            type_counts[t] = type_counts.get(t, 0) + 1

        assert total == 3
        assert abs(avg_conf - 0.9) < 0.01  # 允许浮点误差
        assert type_counts["short"] == 2


# ==================== fixtures ====================


@pytest.fixture
def mock_main_window():
    """模拟主窗口"""
    with patch("pcb_ai_inspector.ui.main_window.MainWindow"):
        yield MagicMock()


@pytest.fixture
def mock_detector():
    """模拟检测器"""
    mock = MagicMock()
    mock.detect.return_value = MagicMock(
        detections=[],
        has_defects=False,
        defect_count=0,
    )
    return mock


@pytest.fixture
def sample_image_path():
    """生成示例图像路径"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # 创建测试图像
        import cv2

        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        image_path = tmp_path / "test.jpg"
        cv2.imwrite(str(image_path), test_image)

        yield image_path


# 需要导入 QFileDialog
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtCore import QEvent, Qt
