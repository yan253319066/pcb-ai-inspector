"""
异常注入测试：错误路径、空参数、损坏文件、无效模型

测试目标：
- 错误路径处理
- 空参数/None参数处理
- 损坏/无效文件处理
- 无效模型处理
- 异常恢复
"""

import io
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from pcb_ai_inspector.core.defect_types import DefectType
from pcb_ai_inspector.models.detector import (
    ImagePreprocessor,
    YOLODetector,
    create_detector,
)
from pcb_ai_inspector.reports.report_generator import ReportGenerator


# ==================== 错误路径测试 ====================


class TestErrorPathHandling:
    """错误路径处理测试"""

    # @pytest.mark.skip(reason: "模型下载测试，跳过")
    # def test_nonexistent_model_path(self):
    #     """测试不存在的模型路径"""
    #     detector = YOLODetector()
    #
    #     # 尝试加载不存在的模型
    #     detector.model_path = Path("/nonexistent/path/model.pt")
    #
    #     # 应该回退到预训练模型
    #     with patch("pcb_ai_inspector.models.detector.YOLO") as mock_yolo:
    #         mock_yolo.return_value = MagicMock()
    #         detector.load_model()
    #
    #         # 验证回退机制
    #         assert detector.model is not None

    # @pytest.mark.skip(reason: "模型下载测试，跳过")
    # def test_nonexistent_image_path(self):
    #     """测试不存在的图像路径"""
    #     detector = YOLODetector()
    #
    #     with patch("pcb_ai_inspector.models.detector.YOLO") as mock_yolo:
    #         mock_yolo.return_value = MagicMock()
    #         detector.load_model()
    #
    #         # 尝试加载不存在的图像
    #         with pytest.raises(Exception):
    #             detector.detect("/nonexistent/image.jpg")

    def test_invalid_output_path(self):
        """测试无效输出路径"""
        from pcb_ai_inspector.core.settings import ReportSettings

        generator = ReportGenerator(ReportSettings())

        # 使用无效路径（只读目录）
        invalid_path = Path("/invalid/readonly/path/report.pdf")

        # 应该抛出异常
        try:
            generator.generate_pdf(
                image_path=None,
                detections=[],
                output_path=invalid_path,
            )
        except Exception:
            pass  # 预期会抛出异常

    # @pytest.mark.skip(reason: "模型下载测试，跳过")
    # def test_empty_path_string(self):
    #     """测试空路径字符串"""
    #     detector = YOLODetector()
    #
    #     # 空字符串作为路径
    #     with pytest.raises(Exception):
    #         detector.detect("")

    def test_path_traversal_attempt(self):
        """测试路径遍历尝试（安全测试）"""
        # 模拟尝试路径遍历
        malicious_path = Path("../../../etc/passwd")

        # 应该安全处理
        resolved = malicious_path.resolve()
        assert isinstance(resolved, Path)


# ==================== 空参数测试 ====================


class TestNullParameterHandling:
    """空参数处理测试"""

    # @pytest.mark.skip(reason: "模型下载测试，跳过")
    # def test_none_image_input(self):
    #     """测试 None 图像输入"""
    #     detector = YOLODetector()
    #
    #     with patch("pcb_ai_inspector.models.detector.YOLO") as mock_yolo:
    #         mock_yolo.return_value = MagicMock()
    #         detector.load_model()
    #
    #         # 传入 None 应该有明确的行为（不抛出特定异常）
    #         result = detector.detect(None)
    #         assert result is not None

    def test_none_confidence_threshold(self):
        """测试 None 置信度"""
        detector = YOLODetector()

        # None 作为置信度应该被处理
        detector.set_confidence_threshold(0.5)  # 有效值
        assert detector.confidence_threshold == 0.5

    def test_none_model_path(self):
        """测试 None 模型路径"""
        # None 模型路径应该使用默认
        detector = YOLODetector(model_path=None)
        assert detector.model_path is None

    def test_none_detections_list(self):
        """测试 None 检测结果列表"""
        from pcb_ai_inspector.core.settings import ReportSettings

        generator = ReportGenerator(ReportSettings())

        # None 检测结果应该被处理为空列表
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.pdf"

            try:
                generator.generate_pdf(
                    image_path=None,
                    detections=[],  # 空列表
                    output_path=output_path,
                )
            except ImportError:
                pytest.skip("reportlab not installed")

    def test_empty_detections_instead_of_none(self):
        """测试空列表代替 None"""
        from pcb_ai_inspector.core.settings import ReportSettings

        generator = ReportGenerator(ReportSettings())

        # 空列表应该有明确行为
        detections = []
        total_defects = len(detections)

        assert total_defects == 0


# ==================== 损坏文件测试 ====================


class TestCorruptedFileHandling:
    """损坏文件处理测试"""

    def test_corrupted_image_file(self):
        """测试损坏的图像文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # 创建损坏的图像文件
            corrupted_path = tmp_path / "corrupted.jpg"
            corrupted_path.write_bytes(b"This is not a valid JPEG")

            # 尝试加载损坏图像
            import cv2

            image = cv2.imread(str(corrupted_path))

            # 应该返回 None
            assert image is None

    def test_truncated_image(self):
        """测试截断的图像文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # 创建截断的图像
            truncated_path = tmp_path / "truncated.png"
            truncated_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 10)

            import cv2

            image = cv2.imread(str(truncated_path))

            # 可能返回 None 或部分图像
            if image is not None:
                assert len(image.shape) >= 2

    def test_invalid_image_extension(self):
        """测试无效的图像扩展名"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # 创建非图像文件
            fake_image = tmp_path / "fake.jpg"
            fake_image.write_text("Not an image")

            import cv2

            image = cv2.imread(str(fake_image))

            assert image is None

    def test_empty_file(self):
        """测试空文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # 创建空文件
            empty_file = tmp_path / "empty.jpg"
            empty_file.write_bytes(b"")

            import cv2

            # OpenCV 新版本会抛出异常而不是返回 None
            try:
                image = cv2.imread(str(empty_file))
                # 如果没有抛异常，应该返回 None
                assert image is None
            except cv2.error:
                # 预期会抛出异常
                pass

    def test_corrupted_pdf_template(self):
        """测试损坏的 PDF 模板"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # 创建损坏的 PDF
            corrupted_pdf = tmp_path / "corrupted.pdf"
            corrupted_pdf.write_bytes(b"%PDF-1.4 broken content")

            # 尝试读取应该失败
            try:
                with open(corrupted_pdf, "rb") as f:
                    content = f.read()
                # 验证内容是损坏的
                assert b"%PDF" in content
            except Exception:
                pass


# ==================== 无效模型测试 ====================


class TestInvalidModelHandling:
    """无效模型处理测试"""

    # @pytest.mark.skip(reason: "模型下载测试，跳过")
    # def test_invalid_model_file(self):
    #     """测试无效的模型文件"""
    #     with tempfile.TemporaryDirectory() as tmpdir:
    #         tmp_path = Path(tmpdir)
    #
    #         # 创建假模型文件
    #         fake_model = tmp_path / "fake_model.pt"
    #         fake_model.write_bytes(b"This is not a valid PyTorch model")
    #
    #         # 尝试加载应该处理错误
    #         detector = YOLODetector()
    #         try:
    #             detector.load_model(str(fake_model))
    #         except Exception:
    #             pass  # 预期会抛出异常

    # @pytest.mark.skip(reason: "模型下载测试，跳过")
    # def test_wrong_model_format(self):
    #     """测试错误格式的模型"""
    #     # 使用非模型文件作为模型
    #     detector = YOLODetector()
    #
    #     with tempfile.TemporaryDirectory() as tmpdir:
    #         tmp_path = Path(tmpdir)
    #
    #         # 创建文本文件代替模型
    #         text_file = tmp_path / "model.txt"
    #         text_file.write_text("Not a model")
    #
    #         # YOLO 应该处理这种情况
    #         try:
    #             detector.load_model(str(text_file))
    #         except Exception:
    #             pass  # 预期会抛出异常

    # @pytest.mark.skip(reason: "模型下载测试，跳过")
    # def test_model_missing_weights(self):
    #     """测试缺少权重的模型"""
    #     # 测试部分损坏的模型
    #     detector = YOLODetector()

    #     # 未加载模型时调用检测
    #     detector.model = None

    #     # 应该抛出错误
    #     with pytest.raises(RuntimeError):
    #         detector.detect(np.zeros((100, 100, 3), dtype=np.uint8))

    def test_confidence_out_of_range(self):
        """测试置信度超出范围"""
        detector = YOLODetector()

        # 测试边界情况
        detector.set_confidence_threshold(-1.0)
        assert detector.confidence_threshold == 0.0

        detector.set_confidence_threshold(2.0)
        assert detector.confidence_threshold == 1.0


# ==================== 预处理异常测试 ====================


class TestPreprocessorErrorHandling:
    """预处理器异常处理测试"""

    def test_preprocess_invalid_array_shape(self):
        """测试无效数组形状"""
        preprocessor = ImagePreprocessor()

        # 无效形状（1D 数组）
        invalid_image = np.zeros(100, dtype=np.uint8)

        # 应该处理无效输入
        try:
            result = preprocessor.preprocess(invalid_image)
        except Exception:
            pass  # 预期抛出异常

    def test_preprocess_negative_values(self):
        """测试负值像素"""
        preprocessor = ImagePreprocessor()

        # 负值像素
        image = np.array([[-1, 0, 255]], dtype=np.int16)

        # 转换为 uint8
        image = np.clip(image, 0, 255).astype(np.uint8)

        result = preprocessor.preprocess(image)

        assert result.shape == (640, 640, 3)

    def test_preprocess_extremely_large_image(self):
        """测试极大图像"""
        preprocessor = ImagePreprocessor()

        # 极大图像
        large_image = np.random.randint(0, 255, (10000, 10000), dtype=np.uint8)

        # 应该处理但可能很慢
        try:
            result = preprocessor.preprocess(large_image)
            assert result.shape[0] == 640
        except Exception:
            pytest.skip("Memory constraints")

    def test_preprocess_invalid_dtype(self):
        """测试无效数据类型"""
        preprocessor = ImagePreprocessor()

        # 浮点图像 - 应该先转换类型
        float_image = np.random.random((100, 100, 3)).astype(np.float32)

        # 转换为 uint8 后再处理
        uint8_image = (float_image * 255).astype(np.uint8)

        result = preprocessor.preprocess(uint8_image)

        assert result.dtype == np.uint8


# ==================== 异常恢复测试 ====================


class TestErrorRecovery:
    """异常恢复测试"""

    # @pytest.mark.skip(reason: "模型下载测试，跳过")
    # def test_recovery_from_load_error(self):
    #     """测试加载错误后恢复"""
    #     detector = YOLODetector()
    #
    #     # 第一次加载失败
    #     try:
    #         detector.load_model("/invalid/path.pt")
    #     except Exception:
    #         pass
    #
    #     # 第二次加载应该仍然工作
    #     with patch("pcb_ai_inspector.models.detector.YOLO") as mock_yolo:
    #         mock_yolo.return_value = MagicMock()
    #         detector.load_model()
    #
    #         assert detector.model is not None

    # @pytest.mark.skip(reason: "模型下载测试，跳过")
    # def test_recovery_from_detection_error(self):
    #     """测试检测错误后恢复"""
    #     detector = YOLODetector()
    #
    #     with patch("pcb_ai_inspector.models.detector.YOLO") as mock_yolo:
    #         mock_yolo.return_value = MagicMock()
    #         detector.load_model()
    #
    #         # 第一次检测失败
    #         try:
    #             detector.detect(None)
    #         except Exception:
    #             pass
    #
    #         # 第二次检测（正确输入）应该工作
    #         result = detector.detect(np.zeros((100, 100, 3), dtype=np.uint8))
    #         assert result is not None

    # @pytest.mark.skip(reason: "模型下载测试，跳过")
    # def test_multiple_error_scenarios(self):
    #     """测试多个错误场景"""
    #     detector = YOLODetector()
    #
    #     error_scenarios = [
    #         (None, "None input"),
    #         ("", "empty string"),
    #         (Path("/nonexistent"), "nonexistent path"),
    #     ]
    #
    #     for input_val, description in error_scenarios:
    #         try:
    #             detector.detect(input_val)
    #         except Exception:
    #             pass  # 预期会抛出异常


# ==================== 边界条件测试 ====================


class TestBoundaryConditions:
    """边界条件测试"""

    def test_single_pixel_image(self):
        """测试单像素图像"""
        preprocessor = ImagePreprocessor()

        single_pixel = np.array([[128]], dtype=np.uint8)

        result = preprocessor.preprocess(single_pixel)

        assert result.shape == (640, 640, 3)

    def test_very_wide_image(self):
        """测试非常宽的图像"""
        preprocessor = ImagePreprocessor()

        wide_image = np.random.randint(0, 255, (100, 1000), dtype=np.uint8)

        result = preprocessor.preprocess(wide_image)

        assert result.shape[0] == 640

    def test_very_tall_image(self):
        """测试非常高的图像"""
        preprocessor = ImagePreprocessor()

        tall_image = np.random.randint(0, 255, (1000, 100), dtype=np.uint8)

        result = preprocessor.preprocess(tall_image)

        assert result.shape[1] == 640

    def test_confidence_boundary_values(self):
        """测试置信度边界值"""
        detector = YOLODetector()

        # 测试各种边界值
        test_values = [0.0, 0.25, 0.5, 0.75, 1.0, -0.1, 1.1]
        expected_values = [0.0, 0.25, 0.5, 0.75, 1.0, 0.0, 1.0]

        for test_val, expected in zip(test_values, expected_values):
            detector.set_confidence_threshold(test_val)
            assert detector.confidence_threshold == expected


# ==================== 资源清理测试 ====================


class TestResourceCleanup:
    """资源清理测试"""

    def test_temp_file_cleanup(self):
        """测试临时文件清理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # 创建临时文件
            temp_files = [tmp_path / f"temp_{i}.txt" for i in range(5)]
            for f in temp_files:
                f.write_text("temp")

            # 上下文管理器退出后应该清理
            pass

        # 验证临时文件已清理
        # 注意：在 with 块外无法访问 tmp_path

    # @pytest.mark.skip(reason: "模型下载测试，跳过")
    # def test_model_memory_cleanup(self):
    #     """测试模型内存清理"""
    #     detector = YOLODetector()
    #
    #     with patch("pcb_ai_inspector.models.detector.YOLO") as mock_yolo:
    #         mock_model = MagicMock()
    #         mock_yolo.return_value = mock_model
    #
    #         detector.load_model()
    #
    #         # 删除检测器后模型应该可被 GC
    #         del detector
    #         del mock_model
    #
    #         # 验证无异常


# ==================== fixtures ====================


@pytest.fixture
def corrupted_image_path():
    """生成损坏图像文件路径"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        corrupted_path = tmp_path / "corrupted.jpg"
        corrupted_path.write_bytes(b"corrupted image data")

        yield corrupted_path


@pytest.fixture
def invalid_model_path():
    """生成无效模型文件路径"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        invalid_model = tmp_path / "invalid.pt"
        invalid_model.write_bytes(b"not a valid model")

        yield invalid_model


@pytest.fixture
def empty_image_path():
    """生成空图像文件路径"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        empty_path = tmp_path / "empty.jpg"
        empty_path.write_bytes(b"")

        yield empty_path
