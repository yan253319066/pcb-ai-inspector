"""
PCB AI Inspector 设置管理模块。

提供：
- 应用程序设置存储和检索
- 默认值
- 设置验证
- 热重载支持
- 工业场景完整配置
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

DEFAULT_MODEL_PATH = "models/best.pt"


# ==================== 枚举定义 ====================


class WindowSizePreset(Enum):
    """窗口尺寸预设。"""

    STANDARD = "standard"  # 标准 1280x720
    LARGE = "large"  # 大屏 1920x1080
    COMPACT = "compact"  # 紧凑 1024x600
    CUSTOM = "custom"  # 自定义


class ImageFormat(Enum):
    """支持的图像格式。"""

    PNG = "png"
    JPEG = "jpeg"
    BMP = "bmp"
    TIFF = "tiff"


class ReportFormat(Enum):
    """报告输出格式。"""

    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"


class TriggerMode(Enum):
    """相机触发模式。"""

    CONTINUOUS = "continuous"  # 连续采集
    EXTERNAL = "external"  # 外部触发
    SOFTWARE = "software"  # 软件触发


class CameraType(Enum):
    """相机类型。"""

    USB = "usb"
    GIGE = "gige"  # GigE 工业相机


class LightingCondition(Enum):
    """光照条件预设。"""

    UNIFORM = "uniform"  # 均匀光照
    UNEVEN = "uneven"  # 光照不均
    LOW_LIGHT = "low_light"  # 弱光环境
    UNKNOWN = "unknown"  # 自动检测


class BinarizationMethod(Enum):
    """二值化方法。"""

    ADAPTIVE_GAUSSIAN = "adaptive_gaussian"
    ADAPTIVE_MEAN = "adaptive_mean"
    OTSU = "otsu"
    OTSU_GAUSSIAN = "otsu_gaussian"
    FIXED = "fixed"


# ==================== 配置数据类 ====================


@dataclass
class UIWindowSettings:
    """UI 窗口设置。"""

    # 窗口标题
    window_title: str = "PCB AI Inspector - 缺陷检测系统"
    # 最小窗口尺寸
    min_width: int = 1280
    min_height: int = 720
    # 窗口预设
    size_preset: str = WindowSizePreset.STANDARD.value
    # 窗口是否可调整大小
    resizable: bool = True
    # 窗口是否最大化
    start_maximized: bool = False


@dataclass
class UILayoutSettings:
    """UI 布局设置。"""

    # 面板比例
    image_panel_ratio: float = 0.7  # 图像区域占比
    control_panel_ratio: float = 0.3  # 控制区域占比
    # 分割器方向
    splitter_orientation: str = "vertical"
    # 是否显示工具栏
    show_toolbar: bool = True
    # 是否显示状态栏
    show_statusbar: bool = True
    # 是否显示菜单栏
    show_menubar: bool = True
    # 主题
    theme: str = "light"
    # 语言
    language: str = "zh-CN"

    # 对话框默认尺寸
    camera_dialog_width: int = 900
    camera_dialog_height: int = 700
    camera_preview_min_width: int = 640
    camera_preview_min_height: int = 480
    history_dialog_width: int = 800
    history_dialog_height: int = 500
    report_preview_width: int = 800
    report_preview_height: int = 600


@dataclass
class ImageViewerSettings:
    """图像查看器设置。"""

    # 默认缩放
    default_zoom: int = 100
    min_zoom: int = 10
    max_zoom: int = 500
    zoom_step: int = 10
    # 缩放模式
    zoom_mode: str = "fit"  # fit/actual/free
    # 默认显示原始图还是结果图
    default_view: str = "original"  # original/result


@dataclass
class DetectionSettings:
    """检测相关设置。"""

    # 置信度阈值
    confidence_threshold: float = 0.25
    # IOU 阈值
    iou_threshold: float = 0.45
    # 最大检测数
    max_detections: int = 100
    # 自动保存结果
    auto_save_results: bool = True
    # 保存标注图像
    save_detected_images: bool = True
    # 后处理过滤
    enable_filtering: bool = True
    # 小尺寸过滤阈值（像素）
    min_defect_size: int = 10
    # 大尺寸过滤阈值（像素）
    max_defect_size: int = 5000
    # 重叠过滤
    enable_nms: bool = True


@dataclass
class DisplaySettings:
    """显示相关设置。"""

    # 边界框
    show_boxes: bool = True
    box_thickness: int = 2
    box_color_by_type: bool = True  # 按类型显示不同颜色
    # 标签
    show_labels: bool = True
    show_confidence: bool = True
    # 字体
    font_scale: float = 0.5
    font_family: str = "SimHei, Arial"
    # 缩放
    default_zoom: int = 100
    # 高亮选中
    highlight_selected: bool = True
    selected_color: str = "#FFFF00"


@dataclass
class ReportSettings:
    """报告生成设置。"""

    # 默认格式
    default_format: str = ReportFormat.PDF.value
    # 包含内容
    include_statistics: bool = True
    include_image: bool = True
    include_charts: bool = True
    # 公司信息
    company_name: str = ""
    company_logo: str = ""
    company_address: str = ""
    company_contact: str = ""
    # 报告标题
    report_title: str = "PCB缺陷检测报告"
    # 报告模板
    template: str = "default"
    # 图像质量
    image_quality: int = 90
    image_max_width: int = 1600
    image_max_height: int = 1200


@dataclass
class PerformanceSettings:
    """性能相关设置。"""

    # GPU 设置
    use_gpu_if_available: bool = True
    gpu_device_id: int = 0
    # 批处理
    batch_size: int = 8
    num_workers: int = 4
    # 缓存
    enable_caching: bool = True
    cache_size_mb: int = 512
    # 内存管理
    max_memory_mb: int = 4096
    # 推理优化
    use_fp16: bool = True  # 半精度推理
    use_tensorrt: bool = False


@dataclass
class PreprocessingSettings:
    """图像预处理设置（用于相机实拍图）。"""

    # 开关（默认关闭 - 预处理会破坏灰度图像细节，降低检测精度）
    enable_preprocessing: bool = False
    # 光照预设
    lighting_preset: str = LightingCondition.UNKNOWN.value
    # 去噪
    enable_denoise: bool = True
    denoise_kernel: int = 3
    # 二值化
    binarization_method: str = BinarizationMethod.ADAPTIVE_GAUSSIAN.value
    adaptive_block_size: int = 11
    adaptive_c: int = 2
    fixed_threshold: int = 127
    # CLAHE 对比度增强
    enable_clahe: bool = True
    clahe_clip_limit: float = 2.0
    clahe_tile_size: int = 8
    # ROI 提取
    enable_roi: bool = True
    roi_margin: int = 10
    roi_min_area_ratio: float = 0.1
    # 形态学操作
    enable_morphology: bool = False
    morph_kernel_size: int = 3
    morph_iterations: int = 1


@dataclass
class CameraSettings:
    """相机设置（工业相机配置）。"""

    # 相机类型
    camera_type: str = CameraType.USB.value
    # 相机 ID
    camera_id: str = "0"
    # 分辨率
    resolution_width: int = 1920
    resolution_height: int = 1080
    # 曝光和增益
    exposure_us: float = 10000.0
    gain: float = 0.0
    # 触发模式
    trigger_mode: str = TriggerMode.CONTINUOUS.value
    # 触发源
    trigger_source: int = 0
    # 超时时间
    timeout_ms: int = 5000
    # 帧率限制
    fps_limit: int = 0
    # 自动曝光
    auto_exposure: bool = False
    auto_gain: bool = False
    # 白平衡
    auto_white_balance: bool = False
    # 触发延时 (毫秒)
    trigger_delay_ms: int = 0
    # 缓冲区大小
    buffer_count: int = 5


@dataclass
class ModelSettings:
    """模型相关设置。"""

    # 模型路径
    model_path: str = DEFAULT_MODEL_PATH
    # 模型类型
    model_type: str = "yolov11"
    # 模型变体
    model_variant: str = "s"  # n/s/m/l/x
    # 输入尺寸
    input_size: int = 640
    # 类别映射
    class_mapping: str = ""  # JSON 格式的类别映射


@dataclass
class IndustrialSettings:
    """工业场景专用设置。"""

    # 生产线配置
    production_line: str = "default"
    station_name: str = "default"
    shift_config: str = "day"  # day/night/custom
    # 质量控制
    pass_threshold: int = 0  # 缺陷数 ≤ 此值为 Pass
    fail_on_critical: bool = True
    # 缺陷分类
    defect_severity_enabled: bool = True
    critical_defects: list[str] = field(
        default_factory=lambda: ["short", "open_circuit"]
    )
    major_defects: list[str] = field(default_factory=lambda: ["missing_hole", "spur"])
    minor_defects: list[str] = field(
        default_factory=lambda: ["mouse_bite", "spurious_copper"]
    )
    # 数据追溯
    enable_traceability: bool = True
    save_original_images: bool = False
    save_marked_images: bool = True  # 保存标注图像
    # 报警设置
    enable_alarm: bool = True
    alarm_on_defect_count: int = 1  # 1 表示发现缺陷就报警
    alarm_sound: str = ""
    alarm_delay_ms: int = 500  # 报警延迟（毫秒）


@dataclass
class ApplicationSettings:
    """完整的应用程序设置。"""

    # UI 设置
    ui_window: UIWindowSettings = field(default_factory=UIWindowSettings)
    ui_layout: UILayoutSettings = field(default_factory=UILayoutSettings)
    ui_viewer: ImageViewerSettings = field(default_factory=ImageViewerSettings)
    # 功能设置
    detection: DetectionSettings = field(default_factory=DetectionSettings)
    display: DisplaySettings = field(default_factory=DisplaySettings)
    report: ReportSettings = field(default_factory=ReportSettings)
    performance: PerformanceSettings = field(default_factory=PerformanceSettings)
    preprocessing: PreprocessingSettings = field(default_factory=PreprocessingSettings)
    camera: CameraSettings = field(default_factory=CameraSettings)
    model: ModelSettings = field(default_factory=ModelSettings)
    # 工业场景
    industrial: IndustrialSettings = field(default_factory=IndustrialSettings)
    # 常规设置
    language: str = "zh-CN"
    theme: str = "light"
    auto_check_updates: bool = True
    recent_files_limit: int = 10
    # 调试模式
    debug_mode: bool = False
    log_level: str = "INFO"


class SettingsManager:
    """管理应用程序设置。"""

    DEFAULT_SETTINGS = ApplicationSettings()

    # 默认窗口尺寸预设
    WINDOW_SIZE_PRESETS = {
        WindowSizePreset.STANDARD: (1280, 720),
        WindowSizePreset.LARGE: (1920, 1080),
        WindowSizePreset.COMPACT: (1024, 600),
    }

    def __init__(self, settings_path: Optional[Path] = None) -> None:
        """初始化设置管理器。

        Args:
            settings_path: 设置 JSON 文件路径
        """
        if settings_path is None:
            config_dir = Path.home() / ".pcb-ai-inspector"
            config_dir.mkdir(parents=True, exist_ok=True)
            settings_path = config_dir / "settings.json"

        self._settings_path = settings_path
        self._settings: ApplicationSettings = self._load_settings()

    def _load_settings(self) -> ApplicationSettings:
        """从文件加载设置。

        Returns:
            ApplicationSettings 实例
        """
        if self._settings_path.exists():
            try:
                data = json.loads(self._settings_path.read_text(encoding="utf-8"))
                return self._parse_settings(data)
            except Exception:
                pass

        # 返回默认值
        return ApplicationSettings()

    def _parse_settings(self, data: dict) -> ApplicationSettings:
        """从字典解析设置。

        Args:
            data: 设置字典

        Returns:
            ApplicationSettings 实例
        """
        # UI 窗口设置
        ui_window_data = data.get("ui_window", {})
        ui_window = UIWindowSettings(
            window_title=ui_window_data.get(
                "window_title", "PCB AI Inspector - 缺陷检测系统"
            ),
            min_width=ui_window_data.get("min_width", 1280),
            min_height=ui_window_data.get("min_height", 720),
            size_preset=ui_window_data.get(
                "size_preset", WindowSizePreset.STANDARD.value
            ),
            resizable=ui_window_data.get("resizable", True),
            start_maximized=ui_window_data.get("start_maximized", False),
        )

        # UI 布局设置
        ui_layout_data = data.get("ui_layout", {})
        ui_layout = UILayoutSettings(
            image_panel_ratio=ui_layout_data.get("image_panel_ratio", 0.7),
            control_panel_ratio=ui_layout_data.get("control_panel_ratio", 0.3),
            splitter_orientation=ui_layout_data.get("splitter_orientation", "vertical"),
            show_toolbar=ui_layout_data.get("show_toolbar", True),
            show_statusbar=ui_layout_data.get("show_statusbar", True),
            show_menubar=ui_layout_data.get("show_menubar", True),
            theme=ui_layout_data.get("theme", "light"),
            language=ui_layout_data.get("language", "zh-CN"),
            camera_dialog_width=ui_layout_data.get("camera_dialog_width", 900),
            camera_dialog_height=ui_layout_data.get("camera_dialog_height", 700),
            camera_preview_min_width=ui_layout_data.get(
                "camera_preview_min_width", 640
            ),
            camera_preview_min_height=ui_layout_data.get(
                "camera_preview_min_height", 480
            ),
            history_dialog_width=ui_layout_data.get("history_dialog_width", 800),
            history_dialog_height=ui_layout_data.get("history_dialog_height", 500),
            report_preview_width=ui_layout_data.get("report_preview_width", 800),
            report_preview_height=ui_layout_data.get("report_preview_height", 600),
        )

        # 图像查看器设置
        ui_viewer_data = data.get("ui_viewer", {})
        ui_viewer = ImageViewerSettings(
            default_zoom=ui_viewer_data.get("default_zoom", 100),
            min_zoom=ui_viewer_data.get("min_zoom", 10),
            max_zoom=ui_viewer_data.get("max_zoom", 500),
            zoom_step=ui_viewer_data.get("zoom_step", 10),
            zoom_mode=ui_viewer_data.get("zoom_mode", "fit"),
            default_view=ui_viewer_data.get("default_view", "original"),
        )

        # 检测设置
        detection_data = data.get("detection", {})
        detection = DetectionSettings(
            confidence_threshold=detection_data.get("confidence_threshold", 0.25),
            iou_threshold=detection_data.get("iou_threshold", 0.45),
            max_detections=detection_data.get("max_detections", 100),
            auto_save_results=detection_data.get("auto_save_results", True),
            save_detected_images=detection_data.get("save_detected_images", True),
            enable_filtering=detection_data.get("enable_filtering", True),
            min_defect_size=detection_data.get("min_defect_size", 10),
            max_defect_size=detection_data.get("max_defect_size", 5000),
            enable_nms=detection_data.get("enable_nms", True),
        )

        # 显示设置
        display_data = data.get("display", {})
        display = DisplaySettings(
            show_boxes=display_data.get("show_boxes", True),
            box_thickness=display_data.get("box_thickness", 2),
            box_color_by_type=display_data.get("box_color_by_type", True),
            show_labels=display_data.get("show_labels", True),
            show_confidence=display_data.get("show_confidence", True),
            font_scale=display_data.get("font_scale", 0.5),
            font_family=display_data.get("font_family", "SimHei, Arial"),
            default_zoom=display_data.get("default_zoom", 100),
            highlight_selected=display_data.get("highlight_selected", True),
            selected_color=display_data.get("selected_color", "#FFFF00"),
        )

        # 报告设置
        report_data = data.get("report", {})
        report = ReportSettings(
            default_format=report_data.get("default_format", ReportFormat.PDF.value),
            include_statistics=report_data.get("include_statistics", True),
            include_image=report_data.get("include_image", True),
            include_charts=report_data.get("include_charts", True),
            company_name=report_data.get("company_name", ""),
            company_logo=report_data.get("company_logo", ""),
            company_address=report_data.get("company_address", ""),
            company_contact=report_data.get("company_contact", ""),
            report_title=report_data.get("report_title", "PCB缺陷检测报告"),
            template=report_data.get("template", "default"),
            image_quality=report_data.get("image_quality", 90),
            image_max_width=report_data.get("image_max_width", 1600),
            image_max_height=report_data.get("image_max_height", 1200),
        )

        # 性能设置
        performance_data = data.get("performance", {})
        performance = PerformanceSettings(
            use_gpu_if_available=performance_data.get("use_gpu_if_available", True),
            gpu_device_id=performance_data.get("gpu_device_id", 0),
            batch_size=performance_data.get("batch_size", 8),
            num_workers=performance_data.get("num_workers", 4),
            enable_caching=performance_data.get("enable_caching", True),
            cache_size_mb=performance_data.get("cache_size_mb", 512),
            max_memory_mb=performance_data.get("max_memory_mb", 4096),
            use_fp16=performance_data.get("use_fp16", True),
            use_tensorrt=performance_data.get("use_tensorrt", False),
        )

        # 预处理设置
        preprocessing_data = data.get("preprocessing", {})
        preprocessing = PreprocessingSettings(
            enable_preprocessing=preprocessing_data.get("enable_preprocessing", False),
            lighting_preset=preprocessing_data.get(
                "lighting_preset", LightingCondition.UNKNOWN.value
            ),
            enable_denoise=preprocessing_data.get("enable_denoise", True),
            denoise_kernel=preprocessing_data.get("denoise_kernel", 3),
            binarization_method=preprocessing_data.get(
                "binarization_method", BinarizationMethod.ADAPTIVE_GAUSSIAN.value
            ),
            adaptive_block_size=preprocessing_data.get("adaptive_block_size", 11),
            adaptive_c=preprocessing_data.get("adaptive_c", 2),
            fixed_threshold=preprocessing_data.get("fixed_threshold", 127),
            enable_clahe=preprocessing_data.get("enable_clahe", True),
            clahe_clip_limit=preprocessing_data.get("clahe_clip_limit", 2.0),
            clahe_tile_size=preprocessing_data.get("clahe_tile_size", 8),
            enable_roi=preprocessing_data.get("enable_roi", True),
            roi_margin=preprocessing_data.get("roi_margin", 10),
            roi_min_area_ratio=preprocessing_data.get("roi_min_area_ratio", 0.1),
            enable_morphology=preprocessing_data.get("enable_morphology", False),
            morph_kernel_size=preprocessing_data.get("morph_kernel_size", 3),
            morph_iterations=preprocessing_data.get("morph_iterations", 1),
        )

        # 相机设置
        camera_data = data.get("camera", {})
        camera = CameraSettings(
            camera_type=camera_data.get("camera_type", CameraType.USB.value),
            camera_id=camera_data.get("camera_id", "0"),
            resolution_width=camera_data.get("resolution_width", 1920),
            resolution_height=camera_data.get("resolution_height", 1080),
            exposure_us=camera_data.get("exposure_us", 10000.0),
            gain=camera_data.get("gain", 0.0),
            trigger_mode=camera_data.get("trigger_mode", TriggerMode.CONTINUOUS.value),
            trigger_source=camera_data.get("trigger_source", 0),
            timeout_ms=camera_data.get("timeout_ms", 5000),
            fps_limit=camera_data.get("fps_limit", 0),
            auto_exposure=camera_data.get("auto_exposure", False),
            auto_gain=camera_data.get("auto_gain", False),
            auto_white_balance=camera_data.get("auto_white_balance", False),
            trigger_delay_ms=camera_data.get("trigger_delay_ms", 0),
            buffer_count=camera_data.get("buffer_count", 5),
        )

        # 模型设置
        model_data = data.get("model", {})
        model = ModelSettings(
            model_path=model_data.get("model_path", ""),
            model_type=model_data.get("model_type", "yolov11"),
            model_variant=model_data.get("model_variant", "s"),
            input_size=model_data.get("input_size", 640),
            class_mapping=model_data.get("class_mapping", ""),
        )

        # 工业场景设置
        industrial_data = data.get("industrial", {})
        industrial = IndustrialSettings(
            production_line=industrial_data.get("production_line", "default"),
            station_name=industrial_data.get("station_name", "default"),
            shift_config=industrial_data.get("shift_config", "day"),
            pass_threshold=industrial_data.get("pass_threshold", 0),
            fail_on_critical=industrial_data.get("fail_on_critical", True),
            defect_severity_enabled=industrial_data.get(
                "defect_severity_enabled", True
            ),
            critical_defects=industrial_data.get(
                "critical_defects", ["short", "open_circuit"]
            ),
            major_defects=industrial_data.get(
                "major_defects", ["missing_hole", "spur"]
            ),
            minor_defects=industrial_data.get(
                "minor_defects", ["mouse_bite", "spurious_copper"]
            ),
            enable_traceability=industrial_data.get("enable_traceability", True),
            save_original_images=industrial_data.get("save_original_images", False),
            enable_alarm=industrial_data.get("enable_alarm", False),
            alarm_on_defect_count=industrial_data.get("alarm_on_defect_count", 0),
            alarm_sound=industrial_data.get("alarm_sound", ""),
        )

        return ApplicationSettings(
            ui_window=ui_window,
            ui_layout=ui_layout,
            ui_viewer=ui_viewer,
            detection=detection,
            display=display,
            report=report,
            performance=performance,
            preprocessing=preprocessing,
            camera=camera,
            model=model,
            industrial=industrial,
            language=data.get("language", "zh-CN"),
            theme=data.get("theme", "light"),
            auto_check_updates=data.get("auto_check_updates", True),
            recent_files_limit=data.get("recent_files_limit", 10),
            debug_mode=data.get("debug_mode", False),
            log_level=data.get("log_level", "INFO"),
        )

    def _settings_to_dict(self) -> dict:
        """将设置转换为字典。

        Returns:
            字典形式的设置
        """
        return {
            "ui_window": {
                "window_title": self._settings.ui_window.window_title,
                "min_width": self._settings.ui_window.min_width,
                "min_height": self._settings.ui_window.min_height,
                "size_preset": self._settings.ui_window.size_preset,
                "resizable": self._settings.ui_window.resizable,
                "start_maximized": self._settings.ui_window.start_maximized,
            },
            "ui_layout": {
                "image_panel_ratio": self._settings.ui_layout.image_panel_ratio,
                "control_panel_ratio": self._settings.ui_layout.control_panel_ratio,
                "splitter_orientation": self._settings.ui_layout.splitter_orientation,
                "show_toolbar": self._settings.ui_layout.show_toolbar,
                "show_statusbar": self._settings.ui_layout.show_statusbar,
                "show_menubar": self._settings.ui_layout.show_menubar,
                "theme": self._settings.ui_layout.theme,
                "language": self._settings.ui_layout.language,
                "camera_dialog_width": self._settings.ui_layout.camera_dialog_width,
                "camera_dialog_height": self._settings.ui_layout.camera_dialog_height,
                "camera_preview_min_width": self._settings.ui_layout.camera_preview_min_width,
                "camera_preview_min_height": self._settings.ui_layout.camera_preview_min_height,
                "history_dialog_width": self._settings.ui_layout.history_dialog_width,
                "history_dialog_height": self._settings.ui_layout.history_dialog_height,
                "report_preview_width": self._settings.ui_layout.report_preview_width,
                "report_preview_height": self._settings.ui_layout.report_preview_height,
            },
            "ui_viewer": {
                "default_zoom": self._settings.ui_viewer.default_zoom,
                "min_zoom": self._settings.ui_viewer.min_zoom,
                "max_zoom": self._settings.ui_viewer.max_zoom,
                "zoom_step": self._settings.ui_viewer.zoom_step,
                "zoom_mode": self._settings.ui_viewer.zoom_mode,
                "default_view": self._settings.ui_viewer.default_view,
            },
            "detection": {
                "confidence_threshold": self._settings.detection.confidence_threshold,
                "iou_threshold": self._settings.detection.iou_threshold,
                "max_detections": self._settings.detection.max_detections,
                "auto_save_results": self._settings.detection.auto_save_results,
                "save_detected_images": self._settings.detection.save_detected_images,
                "enable_filtering": self._settings.detection.enable_filtering,
                "min_defect_size": self._settings.detection.min_defect_size,
                "max_defect_size": self._settings.detection.max_defect_size,
                "enable_nms": self._settings.detection.enable_nms,
            },
            "display": {
                "show_boxes": self._settings.display.show_boxes,
                "box_thickness": self._settings.display.box_thickness,
                "box_color_by_type": self._settings.display.box_color_by_type,
                "show_labels": self._settings.display.show_labels,
                "show_confidence": self._settings.display.show_confidence,
                "font_scale": self._settings.display.font_scale,
                "font_family": self._settings.display.font_family,
                "default_zoom": self._settings.display.default_zoom,
                "highlight_selected": self._settings.display.highlight_selected,
                "selected_color": self._settings.display.selected_color,
            },
            "report": {
                "default_format": self._settings.report.default_format,
                "include_statistics": self._settings.report.include_statistics,
                "include_image": self._settings.report.include_image,
                "include_charts": self._settings.report.include_charts,
                "company_name": self._settings.report.company_name,
                "company_logo": self._settings.report.company_logo,
                "company_address": self._settings.report.company_address,
                "company_contact": self._settings.report.company_contact,
                "report_title": self._settings.report.report_title,
                "template": self._settings.report.template,
                "image_quality": self._settings.report.image_quality,
                "image_max_width": self._settings.report.image_max_width,
                "image_max_height": self._settings.report.image_max_height,
            },
            "performance": {
                "use_gpu_if_available": self._settings.performance.use_gpu_if_available,
                "gpu_device_id": self._settings.performance.gpu_device_id,
                "batch_size": self._settings.performance.batch_size,
                "num_workers": self._settings.performance.num_workers,
                "enable_caching": self._settings.performance.enable_caching,
                "cache_size_mb": self._settings.performance.cache_size_mb,
                "max_memory_mb": self._settings.performance.max_memory_mb,
                "use_fp16": self._settings.performance.use_fp16,
                "use_tensorrt": self._settings.performance.use_tensorrt,
            },
            "preprocessing": {
                "enable_preprocessing": self._settings.preprocessing.enable_preprocessing,
                "lighting_preset": self._settings.preprocessing.lighting_preset,
                "enable_denoise": self._settings.preprocessing.enable_denoise,
                "denoise_kernel": self._settings.preprocessing.denoise_kernel,
                "binarization_method": self._settings.preprocessing.binarization_method,
                "adaptive_block_size": self._settings.preprocessing.adaptive_block_size,
                "adaptive_c": self._settings.preprocessing.adaptive_c,
                "fixed_threshold": self._settings.preprocessing.fixed_threshold,
                "enable_clahe": self._settings.preprocessing.enable_clahe,
                "clahe_clip_limit": self._settings.preprocessing.clahe_clip_limit,
                "clahe_tile_size": self._settings.preprocessing.clahe_tile_size,
                "enable_roi": self._settings.preprocessing.enable_roi,
                "roi_margin": self._settings.preprocessing.roi_margin,
                "roi_min_area_ratio": self._settings.preprocessing.roi_min_area_ratio,
                "enable_morphology": self._settings.preprocessing.enable_morphology,
                "morph_kernel_size": self._settings.preprocessing.morph_kernel_size,
                "morph_iterations": self._settings.preprocessing.morph_iterations,
            },
            "camera": {
                "camera_type": self._settings.camera.camera_type,
                "camera_id": self._settings.camera.camera_id,
                "resolution_width": self._settings.camera.resolution_width,
                "resolution_height": self._settings.camera.resolution_height,
                "exposure_us": self._settings.camera.exposure_us,
                "gain": self._settings.camera.gain,
                "trigger_mode": self._settings.camera.trigger_mode,
                "trigger_source": self._settings.camera.trigger_source,
                "timeout_ms": self._settings.camera.timeout_ms,
                "fps_limit": self._settings.camera.fps_limit,
                "auto_exposure": self._settings.camera.auto_exposure,
                "auto_gain": self._settings.camera.auto_gain,
                "auto_white_balance": self._settings.camera.auto_white_balance,
                "trigger_delay_ms": self._settings.camera.trigger_delay_ms,
                "buffer_count": self._settings.camera.buffer_count,
            },
            "model": {
                "model_path": self._settings.model.model_path,
                "model_type": self._settings.model.model_type,
                "model_variant": self._settings.model.model_variant,
                "input_size": self._settings.model.input_size,
                "class_mapping": self._settings.model.class_mapping,
            },
            "industrial": {
                "production_line": self._settings.industrial.production_line,
                "station_name": self._settings.industrial.station_name,
                "shift_config": self._settings.industrial.shift_config,
                "pass_threshold": self._settings.industrial.pass_threshold,
                "fail_on_critical": self._settings.industrial.fail_on_critical,
                "defect_severity_enabled": self._settings.industrial.defect_severity_enabled,
                "critical_defects": self._settings.industrial.critical_defects,
                "major_defects": self._settings.industrial.major_defects,
                "minor_defects": self._settings.industrial.minor_defects,
                "enable_traceability": self._settings.industrial.enable_traceability,
                "save_original_images": self._settings.industrial.save_original_images,
                "enable_alarm": self._settings.industrial.enable_alarm,
                "alarm_on_defect_count": self._settings.industrial.alarm_on_defect_count,
                "alarm_sound": self._settings.industrial.alarm_sound,
            },
            "language": self._settings.language,
            "theme": self._settings.theme,
            "auto_check_updates": self._settings.auto_check_updates,
            "recent_files_limit": self._settings.recent_files_limit,
            "debug_mode": self._settings.debug_mode,
            "log_level": self._settings.log_level,
        }

    def save(self) -> None:
        """保存设置到文件。"""
        data = self._settings_to_dict()
        self._settings_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def reload(self) -> None:
        """从文件重新加载设置。"""
        self._settings = self._load_settings()

    def reset_to_defaults(self) -> None:
        """将所有设置重置为默认值。"""
        self._settings = ApplicationSettings()
        self.save()

    @property
    def settings(self) -> ApplicationSettings:
        """获取当前设置。

        Returns:
            ApplicationSettings 实例
        """
        return self._settings

    def get(self, key: str, default: Any = None) -> Any:
        """通过键路径获取设置值。

        Args:
            key: 点分隔的键路径（例如 "detection.confidence_threshold"）
            default: 未找到键时返回的默认值

        Returns:
            设置值
        """
        parts = key.split(".")
        value = self._settings

        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict):
                value = value.get(part, default)
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """通过键路径设置设置值。

        Args:
            key: 点分隔的键路径（例如 "detection.confidence_threshold"）
            value: 新值
        """
        parts = key.split(".")

        # 导航到父级
        parent = self._settings
        for part in parts[:-1]:
            if hasattr(parent, part):
                parent = getattr(parent, part)
            elif isinstance(parent, dict):
                parent = parent.get(part)
            else:
                return

        # 设置值
        final_key = parts[-1]
        if hasattr(parent, final_key):
            setattr(parent, final_key, value)
            # 自动保存到文件
            self.save()

    def update(self, updates: dict) -> None:
        """一次更新多个设置。

        Args:
            updates: 键值对字典
        """
        for key, value in updates.items():
            self.set(key, value)

    def validate(self) -> list[str]:
        """验证设置。

        Returns:
            验证错误消息列表
        """
        errors = []

        # 检查检测设置
        if not 0 <= self._settings.detection.confidence_threshold <= 1:
            errors.append("置信度阈值必须在 0 到 1 之间")

        if not 0 <= self._settings.detection.iou_threshold <= 1:
            errors.append("IOU 阈值必须在 0 到 1 之间")

        if self._settings.detection.max_detections < 1:
            errors.append("最大检测数至少为 1")

        # 检查显示设置
        if self._settings.display.box_thickness < 1:
            errors.append("边界框厚度至少为 1")

        if self._settings.display.font_scale <= 0:
            errors.append("字体比例必须为正数")

        if not 10 <= self._settings.display.default_zoom <= 500:
            errors.append("默认缩放必须在 10 到 500 之间")

        # 检查性能设置
        if self._settings.performance.batch_size < 1:
            errors.append("批处理大小至少为 1")

        if self._settings.performance.num_workers < 1:
            errors.append("工作线程数至少为 1")

        if self._settings.performance.cache_size_mb < 0:
            errors.append("缓存大小必须为非负数")

        # 检查预处理设置
        valid_lighting = [lc.value for lc in LightingCondition]
        if self._settings.preprocessing.lighting_preset not in valid_lighting:
            errors.append(f"光照预设必须是 {valid_lighting} 之一")

        valid_binarization = [bm.value for bm in BinarizationMethod]
        if self._settings.preprocessing.binarization_method not in valid_binarization:
            errors.append(f"二值化方法必须是 {valid_binarization} 之一")

        if (
            self._settings.preprocessing.denoise_kernel < 1
            or self._settings.preprocessing.denoise_kernel % 2 == 0
        ):
            errors.append("去噪核大小必须是正奇数")

        if (
            self._settings.preprocessing.adaptive_block_size < 3
            or self._settings.preprocessing.adaptive_block_size % 2 == 0
        ):
            errors.append("自适应块大小必须是正奇数")

        if not 0 <= self._settings.preprocessing.adaptive_c <= 10:
            errors.append("自适应阈值常数必须在 0 到 10 之间")

        if not 0 <= self._settings.preprocessing.fixed_threshold <= 255:
            errors.append("固定阈值必须在 0 到 255 之间")

        if not 0.1 <= self._settings.preprocessing.clahe_clip_limit <= 5.0:
            errors.append("CLAHE 对比度限制必须在 0.1 到 5.0 之间")

        if self._settings.preprocessing.roi_margin < 0:
            errors.append("ROI 边缘不能为负数")

        if not 0.01 <= self._settings.preprocessing.roi_min_area_ratio <= 0.5:
            errors.append("ROI 最小面积占比必须在 0.01 到 0.5 之间")

        # 检查工业设置
        if not 0 <= self._settings.industrial.pass_threshold <= 10:
            errors.append("通过阈值必须在 0 到 10 之间")

        return errors

    def get_window_size(self) -> tuple[int, int]:
        """获取窗口尺寸。

        Returns:
            (宽度, 高度) 元组
        """
        preset = WindowSizePreset(self._settings.ui_window.size_preset)
        if preset in self.WINDOW_SIZE_PRESETS:
            return self.WINDOW_SIZE_PRESETS[preset]
        return (self._settings.ui_window.min_width, self._settings.ui_window.min_height)


# 单例实例
_settings_manager: Optional[SettingsManager] = None


def get_settings_manager(force_reload: bool = False) -> SettingsManager:
    """获取全局设置管理器实例。

    Args:
        force_reload: 是否强制重新加载设置

    Returns:
        SettingsManager 单例
    """
    global _settings_manager
    if _settings_manager is None or force_reload:
        _settings_manager = SettingsManager()
    return _settings_manager


# 兼容旧代码 - 别名
DetectionSettings_OLD = DetectionSettings
DisplaySettings_OLD = DisplaySettings
ReportSettings_OLD = ReportSettings
PerformanceSettings_OLD = PerformanceSettings
PreprocessingSettings_OLD = PreprocessingSettings
CameraSettings_OLD = CameraSettings


if __name__ == "__main__":
    # 测试设置
    print("=" * 50)
    print("设置管理器测试")
    print("=" * 50)

    # 创建管理器
    manager = SettingsManager(Path("test_settings.json"))

    # 测试获取设置
    print(f"\n置信度阈值: {manager.get('detection.confidence_threshold')}")
    print(f"显示边界框: {manager.get('display.show_boxes')}")
    print(f"窗口标题: {manager.get('ui_window.window_title')}")

    # 测试设置值
    manager.set("detection.confidence_threshold", 0.7)
    print(f"更新后的置信度阈值: {manager.get('detection.confidence_threshold')}")

    # 测试验证
    manager.set("detection.confidence_threshold", 1.5)  # 无效
    errors = manager.validate()
    print(f"验证错误: {errors}")

    # 获取窗口尺寸
    window_size = manager.get_window_size()
    print(f"窗口尺寸: {window_size}")

    # 重置并保存
    manager.reset_to_defaults()
    manager.save()

    # 删除测试文件
    Path("test_settings.json").unlink(missing_ok=True)
    print("\n测试完成！")
