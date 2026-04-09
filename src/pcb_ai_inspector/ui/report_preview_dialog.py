"""
报告预览对话框模块。

提供报告预览功能，在导出前显示报告内容。
窗口属性从配置读取。
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QComboBox,
    QWidget,
    QFileDialog,
    QMessageBox,
)

from ..reports.report_generator import ReportGenerator
from ..core.settings import ReportSettings, get_settings_manager
from .defect_overlay import DetectionResult


class ReportPreviewDialog(QDialog):
    """报告预览对话框。"""

    def __init__(
        self,
        detections: list[DetectionResult],
        image_path: Optional[Path] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """初始化报告预览对话框。

        Args:
            detections: 检测结果列表
            image_path: 图像路径
            parent: 父窗口
        """
        super().__init__(parent)
        self._detections = detections
        self._image_path = image_path
        self._settings_manager = get_settings_manager()
        self._report_settings = self._settings_manager.settings.report

        # 从设置获取对话框尺寸
        ui_settings = self._settings_manager.settings.ui_layout
        self.setWindowTitle("报告预览")
        self.setMinimumSize(
            ui_settings.report_preview_width, ui_settings.report_preview_height
        )
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置用户界面。"""
        main_layout = QVBoxLayout(self)

        # 格式选择
        format_layout = QHBoxLayout()
        format_label = QLabel("报告格式:")
        self._format_combo = QComboBox()
        self._format_combo.addItems(["PDF", "Excel"])
        self._format_combo.currentTextChanged.connect(self._on_format_changed)
        format_layout.addWidget(format_label)
        format_layout.addWidget(self._format_combo)
        format_layout.addStretch()
        main_layout.addLayout(format_layout)

        # 预览区域
        preview_group = QWidget()
        preview_layout = QVBoxLayout(preview_group)
        preview_label = QLabel("预览内容:")
        self._preview_text = QTextEdit()
        self._preview_text.setReadOnly(True)
        preview_layout.addWidget(preview_label)
        preview_layout.addWidget(self._preview_text)
        main_layout.addWidget(preview_group)

        # 按钮区域
        button_layout = QHBoxLayout()
        self._export_button = QPushButton("导出")
        self._export_button.clicked.connect(self._on_export)
        self._cancel_button = QPushButton("取消")
        self._cancel_button.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(self._export_button)
        button_layout.addWidget(self._cancel_button)
        main_layout.addLayout(button_layout)

        # 初始预览
        self._update_preview()

    def _on_format_changed(self, format_name: str) -> None:
        """处理格式选择变化。"""
        self._update_preview()

    def _update_preview(self) -> None:
        """更新预览内容。"""
        format_name = self._format_combo.currentText()
        preview_text = self._generate_preview(format_name)
        self._preview_text.setPlainText(preview_text)

    def _generate_preview(self, format_name: str) -> str:
        """生成预览文本。"""
        preview_lines = []
        preview_lines.append("报告预览")
        preview_lines.append("=" * 50)

        # 基本信息
        preview_lines.append("\n基本信息:")
        preview_lines.append(f"  报告格式: {format_name}")
        preview_lines.append(
            f"  图像文件: {self._image_path.name if self._image_path else 'N/A'}"
        )
        preview_lines.append(f"  缺陷数量: {len(self._detections)}")

        # 统计信息
        if self._detections:
            preview_lines.append("\n统计信息:")
            avg_conf = sum(d.confidence for d in self._detections) / len(
                self._detections
            )
            max_conf = max(d.confidence for d in self._detections)
            min_conf = min(d.confidence for d in self._detections)
            preview_lines.append(f"  平均置信度: {avg_conf:.1%}")
            preview_lines.append(f"  最高置信度: {max_conf:.1%}")
            preview_lines.append(f"  最低置信度: {min_conf:.1%}")

            # 按类型统计
            type_counts = {}
            for det in self._detections:
                label = det.defect_type.value
                if label not in type_counts:
                    type_counts[label] = 0
                type_counts[label] += 1

            preview_lines.append("\n缺陷类型分布:")
            for label, count in type_counts.items():
                percentage = (count / len(self._detections)) * 100
                preview_lines.append(f"  {label}: {count} ({percentage:.1%})")

        # 缺陷详情预览
        if self._detections:
            preview_lines.append("\n缺陷详情预览 (前5个):")
            for i, det in enumerate(self._detections[:5], 1):
                preview_lines.append(
                    f"  {i}. 类型: {det.defect_type.value}, 置信度: {det.confidence:.1%}, 位置: ({det.x1:.0f}, {det.y1:.0f}) - ({det.x2:.0f}, {det.y2:.0f})"
                )

            if len(self._detections) > 5:
                preview_lines.append(
                    f"  ... 还有 {len(self._detections) - 5} 个缺陷未显示"
                )

        return "\n".join(preview_lines)

    def _on_export(self) -> None:
        """处理导出按钮点击。"""
        format_name = self._format_combo.currentText()
        suffix = ".pdf" if format_name == "PDF" else ".xlsx"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            f"保存{format_name}报告",
            "",
            f"{format_name}文件 (*{suffix});;所有文件 (*.*)",
        )

        if not file_path:
            return

        file_path = Path(file_path)

        try:
            generator = ReportGenerator(settings=self._report_settings)
            if format_name == "PDF":
                generator.generate_pdf(
                    image_path=self._image_path,
                    detections=self._detections,
                    output_path=file_path,
                )
            else:
                generator.generate_excel(
                    detections=self._detections,
                    output_path=file_path,
                    image_path=self._image_path,
                )

            QMessageBox.information(self, "导出成功", f"报告已成功导出到:\n{file_path}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出报告时出错:\n{e}")


class BatchReportPreviewDialog(QDialog):
    """批量报告预览对话框。"""

    def __init__(
        self,
        results: dict[str, dict],
        parent: Optional[QWidget] = None,
    ) -> None:
        """初始化批量报告预览对话框。

        Args:
            results: 批量检测结果字典
            parent: 父窗口
        """
        super().__init__(parent)
        self._results = results
        self._settings_manager = get_settings_manager()
        self._report_settings = self._settings_manager.settings.report

        # 从设置获取对话框尺寸
        ui_settings = self._settings_manager.settings.ui_layout
        self.setWindowTitle("批量报告预览")
        self.setMinimumSize(
            ui_settings.report_preview_width, ui_settings.report_preview_height
        )
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置用户界面。"""
        main_layout = QVBoxLayout(self)

        # 格式选择
        format_layout = QHBoxLayout()
        format_label = QLabel("报告格式:")
        self._format_combo = QComboBox()
        self._format_combo.addItems(["PDF", "Excel"])
        self._format_combo.currentTextChanged.connect(self._on_format_changed)
        format_layout.addWidget(format_label)
        format_layout.addWidget(self._format_combo)
        format_layout.addStretch()
        main_layout.addLayout(format_layout)

        # 预览区域
        preview_group = QWidget()
        preview_layout = QVBoxLayout(preview_group)
        preview_label = QLabel("预览内容:")
        self._preview_text = QTextEdit()
        self._preview_text.setReadOnly(True)
        preview_layout.addWidget(preview_label)
        preview_layout.addWidget(self._preview_text)
        main_layout.addWidget(preview_group)

        # 按钮区域
        button_layout = QHBoxLayout()
        self._export_button = QPushButton("导出")
        self._export_button.clicked.connect(self._on_export)
        self._cancel_button = QPushButton("取消")
        self._cancel_button.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(self._export_button)
        button_layout.addWidget(self._cancel_button)
        main_layout.addLayout(button_layout)

        # 初始预览
        self._update_preview()

    def _on_format_changed(self, format_name: str) -> None:
        """处理格式选择变化。"""
        self._update_preview()

    def _update_preview(self) -> None:
        """更新预览内容。"""
        format_name = self._format_combo.currentText()
        preview_text = self._generate_preview(format_name)
        self._preview_text.setPlainText(preview_text)

    def _generate_preview(self, format_name: str) -> str:
        """生成预览文本。"""
        preview_lines = []
        preview_lines.append("批量报告预览")
        preview_lines.append("=" * 50)

        # 基本信息
        preview_lines.append("\n基本信息:")
        preview_lines.append(f"  报告格式: {format_name}")
        preview_lines.append(f"  检测图像数: {len(self._results)}")

        # 统计信息
        total_defects = 0
        total_confidence = 0
        defect_count = 0
        type_counts = {}

        for result in self._results.values():
            detections = result.get("detections", [])
            total_defects += len(detections)
            for det in detections:
                total_confidence += det.confidence
                defect_count += 1
                label = det.defect_type.value
                if label not in type_counts:
                    type_counts[label] = 0
                type_counts[label] += 1

        preview_lines.append("\n统计信息:")
        preview_lines.append(f"  总缺陷数: {total_defects}")
        preview_lines.append(
            f"  平均每图缺陷数: {total_defects / len(self._results):.2f}"
        )

        if defect_count > 0:
            avg_conf = total_confidence / defect_count
            preview_lines.append(f"  平均置信度: {avg_conf:.1%}")

        # 按类型统计
        preview_lines.append("\n缺陷类型分布:")
        for label, count in type_counts.items():
            percentage = (count / total_defects) * 100 if total_defects > 0 else 0
            preview_lines.append(f"  {label}: {count} ({percentage:.1%})")

        # 图像预览
        preview_lines.append("\n图像预览:")
        for i, (image_path_str, result) in enumerate(
            list(self._results.items())[:5], 1
        ):
            image_path = Path(image_path_str)
            detections = result.get("detections", [])
            preview_lines.append(f"  {i}. {image_path.name}: {len(detections)} 个缺陷")

        if len(self._results) > 5:
            preview_lines.append(f"  ... 还有 {len(self._results) - 5} 个图像未显示")

        return "\n".join(preview_lines)

    def _on_export(self) -> None:
        """处理导出按钮点击。"""
        format_name = self._format_combo.currentText()
        suffix = ".pdf" if format_name == "PDF" else ".xlsx"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            f"保存批量{format_name}报告",
            "",
            f"{format_name}文件 (*{suffix});;所有文件 (*.*)",
        )

        if not file_path:
            return

        file_path = Path(file_path)

        try:
            generator = ReportGenerator(settings=self._report_settings)
            if format_name == "PDF":
                generator.generate_batch_pdf(
                    results=self._results,
                    output_path=file_path,
                )
            else:
                generator.generate_batch_excel(
                    results=self._results,
                    output_path=file_path,
                )

            QMessageBox.information(
                self, "导出成功", f"批量报告已成功导出到:\n{file_path}"
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出报告时出错:\n{e}")
