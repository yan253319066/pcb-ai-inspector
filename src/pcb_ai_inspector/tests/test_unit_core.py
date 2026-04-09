"""
单元测试：核心推理函数、路径处理、报告生成

测试目标：
- YOLODetector 核心推理函数
- 路径处理函数
- 报告生成函数
- 图像预处理函数
"""

import tempfile
from pathlib import Path

from pcb_ai_inspector.core.settings import DEFAULT_MODEL_PATH
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from pcb_ai_inspector.core.defect_types import DefectType
from pcb_ai_inspector.models.detector import (
    BinarizationMethod,
    DetectionResult,
    ImageDetectionResult,
    ImagePreprocessor,
    LightingPreset,
    YOLODetector,
    create_detector,
)
from pcb_ai_inspector.reports.report_generator import ReportGenerator


# ==================== 核心推理函数测试 ====================


class TestYOLODetector:
    """YOLO 检测器核心推理函数测试"""

    def test_detector_init_default(self):
        """测试检测器默认初始化"""
        detector = YOLODetector()
        assert detector.confidence_threshold > 0
        assert detector.device is not None
        assert detector.model is None

    def test_detector_init_with_params(self):
        """测试带参数的初始化"""
        detector = YOLODetector(
            model_path="dummy.pt",
            confidence_threshold=0.5,
            enable_preprocessing=True,
        )
        assert detector.confidence_threshold == 0.5
        assert detector.enable_preprocessing is True

    def test_set_confidence_threshold(self):
        """测试置信度阈值设置"""
        detector = YOLODetector()

        # 测试有效值
        detector.set_confidence_threshold(0.7)
        assert detector.confidence_threshold == 0.7

        # 测试边界值 - 应该被限制在 0-1 之间
        detector.set_confidence_threshold(-0.5)
        assert detector.confidence_threshold == 0.0

        detector.set_confidence_threshold(1.5)
        assert detector.confidence_threshold == 1.0

    # @pytest.mark.skip(reason: "模型下载测试，跳过")
    # def test_detector_with_mock_model(self):
    #     """使用 Mock 模型测试检测器"""
    #     detector = YOLODetector()

    #     # Mock YOLO 模型
    #     mock_result = MagicMock()
    #     mock_result.boxes = None

    #     with patch("pcb_ai_inspector.models.detector.YOLO") as mock_yolo:
    #         mock_yolo.return_value = MagicMock()
    #         detector.load_model()

    #         assert detector.model is not None

    # @pytest.mark.skip(reason: "模型下载测试，跳过")
    # def test_detect_without_model_loaded(self):
    #     """测试未加载模型时的检测行为"""
    #     detector = YOLODetector()
    #     detector.model = None  # 确保模型未加载

    #     # 应该抛出异常（模型加载相关错误）
    #     with pytest.raises((RuntimeError, Exception)):
    #         detector.detect(np.zeros((100, 100, 3), dtype=np.uint8))


class TestDetectionResult:
    """检测结果数据类测试"""

    def test_detection_result_creation(self):
        """测试检测结果创建"""
        result = DetectionResult(
            defect_type=DefectType.SHORT,
            confidence=0.95,
            bbox=(10, 20, 100, 200),
            label="短路 - 95%",
        )

        assert result.defect_type == DefectType.SHORT
        assert result.confidence == 0.95
        assert result.bbox == (10, 20, 100, 200)
        assert result.label == "短路 - 95%"

    def test_image_detection_result_creation(self):
        """测试图像检测结果创建"""
        result = ImageDetectionResult(
            image_path=Path("test.jpg"),
            width=640,
            height=480,
            detections=[],
            has_defects=False,
            defect_count=0,
            device_used="cpu",
        )

        assert result.image_path == Path("test.jpg")
        assert result.width == 640
        assert result.height == 480
        assert result.has_defects is False
        assert result.defect_count == 0


# ==================== 路径处理函数测试 ====================


class TestPathHandling:
    """路径处理函数测试"""

    def test_model_path_resolve(self):
        """测试模型路径解析"""
        # 测试默认模型路径
        model_path = Path(DEFAULT_MODEL_PATH)
        assert isinstance(model_path, Path)
        assert hasattr(model_path, "exists")

    def test_image_path_validation(self):
        """测试图像路径验证"""
        valid_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"]

        for ext in valid_extensions:
            path = Path(f"test_image{ext}")
            assert path.suffix in valid_extensions or path.suffix.upper() in [
                e.upper() for e in valid_extensions
            ]

    def test_output_path_generation(self):
        """测试输出路径生成"""
        # 从输入路径生成输出路径
        input_path = Path("/data/images/test.jpg")

        # 生成 PDF 报告路径
        pdf_path = input_path.with_suffix(".pdf")
        assert pdf_path == Path("/data/images/test.pdf")

        # 生成 Excel 报告路径
        excel_path = input_path.with_suffix(".xlsx")
        assert excel_path == Path("/data/images/test.xlsx")


# ==================== 报告生成函数测试 ====================


class TestReportGenerator:
    """报告生成器测试"""

    def test_report_generator_init(self):
        """测试报告生成器初始化"""
        from pcb_ai_inspector.core.settings import ReportSettings

        settings = ReportSettings()
        generator = ReportGenerator(settings)

        assert generator._settings is not None
        assert generator._title == "PCB缺陷检测报告"

    def test_report_generator_default_settings(self):
        """测试默认设置"""
        generator = ReportGenerator()

        assert generator._settings is not None
        assert generator._settings.include_image is True


# ==================== 图像预处理函数测试 ====================


class TestImagePreprocessor:
    """图像预处理器测试"""

    def test_preprocessor_init_default(self):
        """测试默认预处理器初始化"""
        preprocessor = ImagePreprocessor()

        assert preprocessor.target_size == 640
        assert preprocessor.enable_denoise is True
        assert preprocessor.binarization_method == BinarizationMethod.ADAPTIVE_GAUSSIAN

    def test_preprocessor_with_lighting_preset(self):
        """测试光照预设预处理器"""
        preprocessor = ImagePreprocessor(
            lighting_preset=LightingPreset.UNIFORM,
        )

        assert preprocessor.enable_denoise is True
        assert preprocessor.binarization_method == BinarizationMethod.OTSU

    def test_preprocessor_custom_params(self):
        """测试自定义参数预处理器"""
        preprocessor = ImagePreprocessor(
            target_size=320,
            binarization_method=BinarizationMethod.OTSU_GAUSSIAN,
            adaptive_block_size=15,
            adaptive_c=5,
        )

        assert preprocessor.target_size == 320
        assert preprocessor.binarization_method == BinarizationMethod.OTSU_GAUSSIAN
        assert preprocessor.adaptive_block_size == 15
        assert preprocessor.adaptive_block_size % 2 == 1  # 必须是奇数

    def test_preprocess_grayscale_input(self):
        """测试灰度图输入预处理"""
        preprocessor = ImagePreprocessor()

        # 创建灰度图
        gray_image = np.zeros((100, 100), dtype=np.uint8)

        result = preprocessor.preprocess(gray_image)

        # 应该返回 RGB 图像
        assert result.shape == (640, 640, 3)
        assert result.dtype == np.uint8

    def test_preprocess_rgba_input(self):
        """测试 RGBA 输入预处理"""
        preprocessor = ImagePreprocessor()

        # 创建 RGBA 图像
        rgba_image = np.zeros((100, 100, 4), dtype=np.uint8)

        result = preprocessor.preprocess(rgba_image)

        # 应该返回 RGB 图像
        assert result.shape == (640, 640, 3)

    def test_preprocess_bgr_input(self):
        """测试 BGR 输入预处理"""
        preprocessor = ImagePreprocessor()

        # 创建 BGR 图像
        bgr_image = np.zeros((100, 100, 3), dtype=np.uint8)

        result = preprocessor.preprocess(bgr_image)

        # 应该返回 RGB 图像
        assert result.shape == (640, 640, 3)

    def test_letterbox_preserves_aspect_ratio(self):
        """测试 Letterbox 保持宽高比"""
        preprocessor = ImagePreprocessor(target_size=640)

        # 创建不同尺寸的图像
        for width, height in [(800, 600), (600, 800), (1920, 1080)]:
            image = np.zeros((height, width), dtype=np.uint8)
            result = preprocessor._letterbox(image)

            assert result.shape == (640, 640)

            # 验证填充的像素值
            assert result[0, 0] == 128  # 灰色填充
            assert result[639, 639] == 128

    def test_roi_extraction_disabled(self):
        """测试禁用 ROI 提取"""
        preprocessor = ImagePreprocessor(enable_roi=False)

        # 创建简单图像
        image = np.zeros((100, 100, 3), dtype=np.uint8)

        # 应该直接返回原图
        result = preprocessor.preprocess(image)
        assert result.shape == (640, 640, 3)

    def test_binarize_methods(self):
        """测试各种二值化方法"""
        gray = np.random.randint(0, 255, (100, 100), dtype=np.uint8)

        # 测试每种方法
        methods = [
            BinarizationMethod.ADAPTIVE_GAUSSIAN,
            BinarizationMethod.ADAPTIVE_MEAN,
            BinarizationMethod.OTSU,
            BinarizationMethod.OTSU_GAUSSIAN,
            BinarizationMethod.FIXED,
        ]

        for method in methods:
            preprocessor = ImagePreprocessor(binarization_method=method)
            result = preprocessor._binarize(gray)
            assert result.shape == gray.shape
            assert result.dtype == np.uint8


class TestCreateDetector:
    """检测器工厂函数测试"""

    # @pytest.mark.skip(reason: "模型下载测试，跳过")
    # def test_create_detector_default(self):
    #     """测试默认创建检测器"""
    #     detector = create_detector()

    #     assert detector is not None
    #     assert isinstance(detector, YOLODetector)

    # @pytest.mark.skip(reason: "模型下载测试，跳过")
    # def test_create_detector_with_custom_confidence(self):
    #     """测试自定义置信度创建检测器"""
    #     detector = create_detector(confidence=0.8)

    #     assert detector.confidence_threshold == 0.8

    # @pytest.mark.skip(reason: "模型下载测试，跳过")
    # def test_create_detector_with_preprocessing_settings(self):
    #     """测试带预处理设置创建检测器"""
    #     settings = {
    #         "enable_preprocessing": True,
    #         "lighting_preset": "uniform",
    #         "binarization_method": "otsu",
    #         "enable_denoise": True,
    #         "denoise_kernel": 3,
    #     }

    #     detector = create_detector(preprocessing_settings=settings)

    #     assert detector.preprocessor is not None
    #     assert detector.enable_preprocessing is True


# ==================== fixtures ====================


@pytest.fixture
def sample_image():
    """生成示例图像"""
    return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)


@pytest.fixture
def sample_gray_image():
    """生成示例灰度图像"""
    return np.random.randint(0, 255, (480, 640), dtype=np.uint8)


@pytest.fixture
def temp_image_path(sample_image):
    """创建临时图像文件"""
    import cv2

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.jpg"
        cv2.imwrite(str(path), sample_image)
        yield path


@pytest.fixture
def mock_detection_results():
    """生成模拟检测结果"""
    return [
        DetectionResult(
            defect_type=DefectType.SHORT,
            confidence=0.95,
            bbox=(10, 20, 100, 200),
            label="短路 - 95%",
        ),
        DetectionResult(
            defect_type=DefectType.OPEN_CIRCUIT,
            confidence=0.87,
            bbox=(200, 300, 250, 350),
            label="开路 - 87%",
        ),
    ]
