"""
PCB 检验的缺陷类型定义。

本模块包含 PCB 缺陷类型的枚举及其在需求文档中规定的量化定义。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DefectType(Enum):
    """PCB 缺陷类型及标准化标识符。"""

    OPEN_CIRCUIT = "open_circuit"
    """开路：导线或走线断裂。"""

    SHORT_CIRCUIT = "short_circuit"
    """短路：相邻导体之间的异常连接。"""

    MOUSE_BITE = "mousebite"
    """鼠咬：导体边缘的缺口。"""

    SPUR = "spur"
    """毛刺：导体边缘的额外尖锐突起。"""

    PIN_HOLE = "pin_hole"
    """针孔：微小的孔洞缺陷。"""

    SPURIOUS_COPPER = "spurious_copper"
    """多铜：设计中不存在的铜。"""

    HOLE_BREAKOUT = "hole_breakout"
    """孔 breakout：孔周围铜皮延伸。"""

    CONDUCTOR_SCRATCH = "conductor_scratch"
    """导体划痕：导体表面的划痕。"""

    FOREIGN_OBJECT = "foreign_object"
    """异物：PCB 上的外来物体。"""

    MISSING_HOLE = "missing_hole"
    """缺孔：预期孔位缺失。"""

    @property
    def display_name(self) -> str:
        """获取用于 UI 显示的名称。"""
        names = {
            "open_circuit": "开路",
            "short_circuit": "短路",
            "mousebite": "鼠咬",
            "spur": "毛刺",
            "pin_hole": "针孔",
            "spurious_copper": "多铜",
            "hole_breakout": "孔 breakout",
            "conductor_scratch": "导体划痕",
            "foreign_object": "异物",
            "missing_hole": "缺孔",
        }
        return names[self.value]

    @classmethod
    def all_types(cls) -> list["DefectType"]:
        """获取所有缺陷类型的列表。"""
        return list(cls)


# YOLO 模型类别 ID 到 DefectType 的映射
# 此映射应与训练模型的类别顺序一致
MODEL_CLASS_MAPPING: dict[int, DefectType] = {
    0: DefectType.OPEN_CIRCUIT,
    1: DefectType.SHORT_CIRCUIT,
    2: DefectType.MOUSE_BITE,
    3: DefectType.SPUR,
    4: DefectType.PIN_HOLE,
    5: DefectType.SPURIOUS_COPPER,
    6: DefectType.HOLE_BREAKOUT,
    7: DefectType.CONDUCTOR_SCRATCH,
    8: DefectType.FOREIGN_OBJECT,
    9: DefectType.MISSING_HOLE,
}


# 缺陷类型的颜色方案（RGB 值）- 用于图片标签和边界框
DEFECT_COLORS: dict[DefectType, tuple[int, int, int]] = {
    DefectType.OPEN_CIRCUIT: (255, 165, 0),  # 橙色
    DefectType.SHORT_CIRCUIT: (255, 0, 0),  # 红色
    DefectType.MOUSE_BITE: (255, 0, 255),  # 洋红色
    DefectType.SPUR: (0, 255, 0),  # 绿色
    DefectType.PIN_HOLE: (255, 255, 0),  # 黄色
    DefectType.SPURIOUS_COPPER: (138, 43, 226),  # 蓝紫色
    DefectType.HOLE_BREAKOUT: (0, 255, 255),  # 青色
    DefectType.CONDUCTOR_SCRATCH: (255, 128, 0),  # 橙黄色
    DefectType.FOREIGN_OBJECT: (128, 0, 128),  # 紫色
    DefectType.MISSING_HOLE: (0, 128, 255),  # 浅蓝色
}


# 缺陷类型的浅色背景方案（RGB 值）- 用于缺陷列表
DEFECT_COLORS_LIGHT: dict[DefectType, tuple[int, int, int]] = {
    DefectType.OPEN_CIRCUIT: (255, 230, 200),  # 浅橙色
    DefectType.SHORT_CIRCUIT: (255, 200, 200),  # 浅红色
    DefectType.MOUSE_BITE: (255, 200, 255),  # 浅洋红色
    DefectType.SPUR: (200, 255, 200),  # 浅绿色
    DefectType.PIN_HOLE: (255, 255, 200),  # 浅黄色
    DefectType.SPURIOUS_COPPER: (230, 200, 255),  # 浅紫色
    DefectType.HOLE_BREAKOUT: (200, 255, 255),  # 浅青色
    DefectType.CONDUCTOR_SCRATCH: (255, 220, 200),  # 浅橙黄色
    DefectType.FOREIGN_OBJECT: (220, 200, 255),  # 浅紫色
    DefectType.MISSING_HOLE: (200, 220, 255),  # 浅蓝色
}


# 缺陷类型的中文标签
DEFECT_LABELS: dict[DefectType, str] = {
    DefectType.OPEN_CIRCUIT: "开路",
    DefectType.SHORT_CIRCUIT: "短路",
    DefectType.MOUSE_BITE: "鼠咬",
    DefectType.SPUR: "毛刺",
    DefectType.PIN_HOLE: "针孔",
    DefectType.SPURIOUS_COPPER: "多铜",
    DefectType.HOLE_BREAKOUT: "孔 breakout",
    DefectType.CONDUCTOR_SCRATCH: "导体划痕",
    DefectType.FOREIGN_OBJECT: "异物",
    DefectType.MISSING_HOLE: "缺孔",
}


@dataclass
class DefectDefinition:
    """缺陷类型的量化定义。"""

    defect_type: DefectType
    threshold_mm: float
    min_size_px: tuple[int, int]
    description: str

    # 性能目标（mAP@50）
    map50_target: float

    # 中文描述
    zh_description: str


# 按需求文档规定的缺陷量化定义
DEFECT_DEFINITIONS: dict[DefectType, DefectDefinition] = {
    DefectType.SHORT_CIRCUIT: DefectDefinition(
        defect_type=DefectType.SHORT_CIRCUIT,
        threshold_mm=0.2,
        min_size_px=(32, 32),
        description="相邻导体处于最小间距阈值内",
        map50_target=0.88,
        zh_description="两条或多条相邻导线/焊盘之间距离 < 0.2mm",
    ),
    DefectType.OPEN_CIRCUIT: DefectDefinition(
        defect_type=DefectType.OPEN_CIRCUIT,
        threshold_mm=0.0,
        min_size_px=(24, 24),
        description="导体断裂，长度 >= 最小走线宽度",
        map50_target=0.85,
        zh_description="导线或焊盘存在断裂，断裂长度 >= 最小线宽",
    ),
    DefectType.MISSING_HOLE: DefectDefinition(
        defect_type=DefectType.MISSING_HOLE,
        threshold_mm=0.3,
        min_size_px=(16, 16),
        description="预期孔位缺失，排除 < 0.3mm 的微小孔",
        map50_target=0.90,
        zh_description="设计应有孔的位置缺失，排除 < 0.3mm 的微小孔",
    ),
    DefectType.SPUR: DefectDefinition(
        defect_type=DefectType.SPUR,
        threshold_mm=0.1,
        min_size_px=(48, 16),
        description="边缘突起宽度 0.1-2mm，长度 >= 宽度的 2 倍",
        map50_target=0.82,
        zh_description="导线边缘突出部分，宽度 0.1-2mm，长度 >= 宽度的 2 倍",
    ),
    DefectType.MOUSE_BITE: DefectDefinition(
        defect_type=DefectType.MOUSE_BITE,
        threshold_mm=0.2,
        min_size_px=(40, 40),
        description="边缘缺口宽度 0.2-1mm，深度 >= 最小走线宽度的 30%",
        map50_target=0.80,
        zh_description="导线或铜皮边缘存在缺口，缺口宽度 0.2-1mm",
    ),
    DefectType.SPURIOUS_COPPER: DefectDefinition(
        defect_type=DefectType.SPURIOUS_COPPER,
        threshold_mm=1.0,
        min_size_px=(48, 48),
        description="设计中不存在的铜区域，面积 > 1mm²，与走线距离 > 0.15mm",
        map50_target=0.87,
        zh_description="设计图上不存在的铜皮区域，面积 > 1mm²",
    ),
    DefectType.PIN_HOLE: DefectDefinition(
        defect_type=DefectType.PIN_HOLE,
        threshold_mm=0.0,
        min_size_px=(8, 8),
        description="微小的孔洞缺陷",
        map50_target=0.75,
        zh_description="PCB 上微小的孔洞缺陷",
    ),
    DefectType.HOLE_BREAKOUT: DefectDefinition(
        defect_type=DefectType.HOLE_BREAKOUT,
        threshold_mm=0.0,
        min_size_px=(16, 16),
        description="孔周围铜皮延伸超出边界",
        map50_target=0.80,
        zh_description="金属化孔周围铜皮延伸超出设计边界",
    ),
    DefectType.CONDUCTOR_SCRATCH: DefectDefinition(
        defect_type=DefectType.CONDUCTOR_SCRATCH,
        threshold_mm=0.0,
        min_size_px=(32, 8),
        description="导体表面的划痕或凹痕",
        map50_target=0.78,
        zh_description="导体表面因划伤造成的缺陷",
    ),
    DefectType.FOREIGN_OBJECT: DefectDefinition(
        defect_type=DefectType.FOREIGN_OBJECT,
        threshold_mm=0.0,
        min_size_px=(16, 16),
        description="PCB 上的外来物体或污染物",
        map50_target=0.85,
        zh_description="PCB 上存在的异物（如锡渣、灰尘等）",
    ),
}


def get_defect_info(defect_type: DefectType) -> DefectDefinition:
    """获取缺陷类型的量化定义。"""
    return DEFECT_DEFINITIONS[defect_type]
