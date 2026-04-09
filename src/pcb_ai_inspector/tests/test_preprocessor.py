"""测试预处理器功能。"""

import numpy as np
import pytest
from pcb_ai_inspector.models.detector import (
    BinarizationMethod,
    ImagePreprocessor,
    LightingPreset,
)


class TestImagePreprocessor:
    """测试 ImagePreprocessor 类。"""

    def test_default_initialization(self):
        """测试默认初始化。"""
        preprocessor = ImagePreprocessor()
        assert preprocessor.target_size == 640
        assert preprocessor.enable_denoise is True
        assert preprocessor.enable_clahe is True
        assert preprocessor.enable_roi is True

    def test_lighting_preset_uniform(self):
        """测试均匀光照预设。"""
        preprocessor = ImagePreprocessor(lighting_preset=LightingPreset.UNIFORM)
        assert preprocessor.binarization_method == BinarizationMethod.OTSU
        assert preprocessor.enable_clahe is False

    def test_lighting_preset_uneven(self):
        """测试光照不均预设。"""
        preprocessor = ImagePreprocessor(lighting_preset=LightingPreset.UNEVEN)
        assert preprocessor.binarization_method == BinarizationMethod.ADAPTIVE_GAUSSIAN
        assert preprocessor.enable_clahe is True

    def test_lighting_preset_low_light(self):
        """测试弱光预设。"""
        preprocessor = ImagePreprocessor(lighting_preset=LightingPreset.LOW_LIGHT)
        assert preprocessor.enable_clahe is True
        assert preprocessor.clahe_clip_limit == 3.0

    def test_custom_parameters(self):
        """测试自定义参数。"""
        preprocessor = ImagePreprocessor(
            target_size=320,
            binarization_method=BinarizationMethod.FIXED,
            fixed_threshold=100,
            enable_roi=False,
        )
        assert preprocessor.target_size == 320
        assert preprocessor.fixed_threshold == 100
        assert preprocessor.enable_roi is False

    def test_preprocess_grayscale(self):
        """测试灰度图预处理。"""
        preprocessor = ImagePreprocessor(enable_roi=False, enable_clahe=False)
        # 创建测试灰度图 (100x100)
        gray = np.random.randint(0, 256, (100, 100), dtype=np.uint8)

        result = preprocessor.preprocess(gray)

        # 输出应该是 640x640 RGB
        assert result.shape == (640, 640, 3)

    def test_preprocess_color(self):
        """测试彩色图预处理。"""
        preprocessor = ImagePreprocessor(enable_roi=False, enable_clahe=False)
        # 创建测试彩色图 (100x100x3)
        color = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

        result = preprocessor.preprocess(color)

        # 输出应该是 640x640 RGB
        assert result.shape == (640, 640, 3)

    def test_preprocess_with_roi(self):
        """测试 ROI 提取。"""
        preprocessor = ImagePreprocessor(enable_roi=True, enable_clahe=False)
        # 创建测试图：中间有内容，边缘是黑色
        image = np.zeros((200, 200, 3), dtype=np.uint8)
        image[50:150, 50:150] = 255  # 中间白色区域

        result = preprocessor.preprocess(image)

        assert result.shape == (640, 640, 3)

    def test_letterbox_preserves_aspect_ratio(self):
        """测试 Letterbox 保持长宽比。"""
        preprocessor = ImagePreprocessor(enable_roi=False, enable_clahe=False)

        # 测试不同长宽比的图像
        test_cases = [
            (100, 200),  # 宽图
            (200, 100),  # 高图
            (100, 100),  # 正方形
            (640, 480),
        ]

        for h, w in test_cases:
            gray = np.random.randint(0, 256, (h, w), dtype=np.uint8)
            result = preprocessor.preprocess(gray)
            assert result.shape == (640, 640, 3)

    def test_binarization_methods(self):
        """测试所有二值化方法。"""
        gray = np.random.randint(0, 256, (100, 100), dtype=np.uint8)

        methods = [
            BinarizationMethod.ADAPTIVE_GAUSSIAN,
            BinarizationMethod.ADAPTIVE_MEAN,
            BinarizationMethod.OTSU,
            BinarizationMethod.OTSU_GAUSSIAN,
            BinarizationMethod.FIXED,
        ]

        for method in methods:
            preprocessor = ImagePreprocessor(
                binarization_method=method,
                enable_roi=False,
                enable_clahe=False,
            )
            result = preprocessor.preprocess(gray.copy())
            assert result.shape == (640, 640, 3)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
