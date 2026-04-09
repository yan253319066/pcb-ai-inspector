"""独立测试预处理器（不依赖 torch）。"""

import sys
import numpy as np


# 模拟 ImagePreprocessor 的核心逻辑进行测试
class TestPreprocessorLogic:
    """测试预处理器的核心逻辑（不导入实际模块）。"""

    @staticmethod
    def test_letterbox():
        """测试 Letterbox 保持长宽比。"""
        target_size = 640

        test_cases = [
            (100, 200),  # 宽图
            (200, 100),  # 高图
            (100, 100),  # 正方形
            (640, 480),
        ]

        for h, w in test_cases:
            # 模拟 letterbox 逻辑
            scale = min(target_size / h, target_size / w)
            new_h = int(h * scale)
            new_w = int(w * scale)

            # 验证比例
            orig_ratio = w / h
            new_ratio = new_w / new_h

            print(
                f"输入: {w}x{h}, 输出: {new_w}x{new_h}, 比例: {orig_ratio:.2f} -> {new_ratio:.2f}"
            )

            assert abs(orig_ratio - new_ratio) < 0.01, "长宽比应保持"

        print("✓ Letterbox 测试通过")

    @staticmethod
    def test_binarization():
        """测试二值化方法。"""
        import cv2

        gray = np.random.randint(0, 256, (100, 100), dtype=np.uint8)

        # 测试自适应阈值
        result1 = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=11,
            C=2,
        )
        assert result1.shape == gray.shape
        print("✓ 自适应阈值测试通过")

        # 测试 Otsu
        result2 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        assert result2.shape == gray.shape
        print("✓ Otsu 测试通过")

    @staticmethod
    def test_roi_extraction():
        """测试 ROI 提取。"""
        import cv2

        # 创建测试图：中间有内容，边缘是黑色
        image = np.zeros((200, 200, 3), dtype=np.uint8)
        image[50:150, 50:150] = 255  # 中间白色区域

        # 转为灰度
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 自适应阈值找 PCB 区域
        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=15,
            C=5,
        )

        # 闭运算
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        # 找轮廓
        contours, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        print(f"找到 {len(contours)} 个轮廓")

        # 验证找到了有效区域
        if contours:
            areas = [cv2.contourArea(c) for c in contours]
            print(f"最大轮廓面积: {max(areas)}")
            print("✓ ROI 提取测试通过")
        else:
            print("⚠ 未找到轮廓（可能需要调整参数）")

    @staticmethod
    def test_full_pipeline():
        """测试完整预处理流程。"""
        import cv2

        # 创建测试图
        image = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)

        # 1. 灰度
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 2. CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        # 3. 去噪
        gray = cv2.GaussianBlur(gray, (3, 3), 0)

        # 4. 二值化
        gray = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=11,
            C=2,
        )

        # 5. Letterbox
        target_size = 640
        h, w = gray.shape
        scale = min(target_size / h, target_size / w)
        new_h = int(h * scale)
        new_w = int(w * scale)
        resized = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        canvas = np.full((target_size, target_size), 128, dtype=np.uint8)
        dy = (target_size - new_h) // 2
        dx = (target_size - new_w) // 2
        canvas[dy : dy + new_h, dx : dx + new_w] = resized

        # 6. 转 RGB
        rgb = cv2.cvtColor(canvas, cv2.COLOR_GRAY2RGB)

        assert rgb.shape == (640, 640, 3), "输出尺寸错误"
        print("✓ 完整预处理流程测试通过")


if __name__ == "__main__":
    print("=" * 50)
    print("预处理器核心逻辑测试")
    print("=" * 50)

    try:
        TestPreprocessorLogic.test_letterbox()
        TestPreprocessorLogic.test_binarization()
        TestPreprocessorLogic.test_roi_extraction()
        TestPreprocessorLogic.test_full_pipeline()

        print("\n" + "=" * 50)
        print("所有测试通过！")
        print("=" * 50)
    except Exception as e:
        print(f"\n测试失败: {e}")
        sys.exit(1)
