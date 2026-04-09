"""
PCB AI Inspector 缺陷列表小部件。

在可排序、可过滤的表格中显示检测结果，
包含统计信息和导出功能。
"""

from __future__ import annotations

from typing import Optional
from datetime import datetime

from PyQt6.QtCore import (
    Qt,
    QAbstractTableModel,
    QModelIndex,
    QSortFilterProxyModel,
    pyqtSignal,
)
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLayout,
    QTableView,
    QHeaderView,
    QPushButton,
    QLabel,
    QComboBox,
    QLineEdit,
    QGroupBox,
    QAbstractItemView,
)

from ..core.defect_types import DefectType, DEFECT_DEFINITIONS, DEFECT_COLORS_LIGHT, DEFECT_LABELS
from .defect_overlay import DetectionResult


class DefectTableModel(QAbstractTableModel):
    """
    检测结果的表格模型。

    列：
        - 序号（行号）
        - 类型（缺陷类型）
        - 置信度（检测置信度）
        - 位置（边界框位置）
        - 尺寸（边界框尺寸）
    """

    # 列定义
    class Columns:
        INDEX = 0
        TYPE = 1
        CONFIDENCE = 2
        POSITION = 3
        SIZE = 4
        X1 = 5
        Y1 = 6
        X2 = 7
        Y2 = 8

    COLUMN_COUNT = 9
    COLUMN_HEADERS = ["#", "缺陷类型", "置信度", "位置", "尺寸", "x1", "y1", "x2", "y2"]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初始化表格模型。"""
        super().__init__(parent)
        self._detections: list[DetectionResult] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """返回行数。"""
        return len(self._detections)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """返回列数。"""
        return self.COLUMN_COUNT

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> any:
        """返回给定索引和角色的数据。"""
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if row < 0 or row >= len(self._detections):
            return None

        detection = self._detections[row]

        if role == Qt.ItemDataRole.DisplayRole:
            if col == self.Columns.INDEX:
                return str(row + 1)
            elif col == self.Columns.TYPE:
                return DEFECT_LABELS.get(
                    detection.defect_type, detection.defect_type.value
                )
            elif col == self.Columns.CONFIDENCE:
                return f"{detection.confidence:.1%}"
            elif col == self.Columns.POSITION:
                return f"({detection.x1:.0f}, {detection.y1:.0f})"
            elif col == self.Columns.SIZE:
                return f"{detection.width:.0f} × {detection.height:.0f}"
            elif col == self.Columns.X1:
                return f"{detection.x1:.1f}"
            elif col == self.Columns.Y1:
                return f"{detection.y1:.1f}"
            elif col == self.Columns.X2:
                return f"{detection.x2:.1f}"
            elif col == self.Columns.Y2:
                return f"{detection.y2:.1f}"
        elif role == Qt.ItemDataRole.UserRole:
            # 为序号列提供数字类型的值用于排序
            if col == self.Columns.INDEX:
                return row + 1
            # 为置信度列提供数字类型的值用于排序
            elif col == self.Columns.CONFIDENCE:
                return detection.confidence
            # 为坐标和尺寸列提供数字类型的值用于排序
            elif col == self.Columns.X1:
                return detection.x1
            elif col == self.Columns.Y1:
                return detection.y1
            elif col == self.Columns.X2:
                return detection.x2
            elif col == self.Columns.Y2:
                return detection.y2
        elif role == Qt.ItemDataRole.BackgroundRole:
            # Color code by defect type using the centralized color definitions
            if detection.defect_type in DEFECT_COLORS_LIGHT:
                rgb = DEFECT_COLORS_LIGHT[detection.defect_type]
                return QColor(*rgb)
            return None
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (
                self.Columns.CONFIDENCE,
                self.Columns.X1,
                self.Columns.Y1,
                self.Columns.X2,
                self.Columns.Y2,
            ):
                return Qt.AlignmentFlag.AlignRight

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> any:
        """返回表头数据。"""
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return (
                    self.COLUMN_HEADERS[section]
                    if section < len(self.COLUMN_HEADERS)
                    else None
                )
            elif orientation == Qt.Orientation.Vertical:
                return str(section + 1)
        return None

    def set_detections(self, detections: list[DetectionResult]) -> None:
        """设置检测结果。"""
        self.beginResetModel()
        self._detections = detections.copy()
        self.endResetModel()

    def get_detection(self, row: int) -> Optional[DetectionResult]:
        """获取指定行的检测结果。"""
        if 0 <= row < len(self._detections):
            return self._detections[row]
        return None

    def clear(self) -> None:
        """清空所有检测结果。"""
        self.beginResetModel()
        self._detections.clear()
        self.endResetModel()


class DefectListWidget(QWidget):
    """
    Widget for displaying and managing detection results.

    Features:
        - Sortable table view
        - Filter by defect type
        - Search by confidence
        - Statistics summary
        - Export capability
    """

    # Signals
    detection_selected = pyqtSignal(int)  # Row index
    filter_changed = pyqtSignal(str, float)  # Filter type, min confidence

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the defect list widget."""
        super().__init__(parent)

        # Data
        self._model = DefectTableModel(self)
        self._proxy_model = QSortFilterProxyModel(self)
        self._proxy_model.setSourceModel(self._model)
        self._proxy_model.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        # 使用 UserRole 进行排序，确保序号列按数字排序
        self._proxy_model.setSortRole(Qt.ItemDataRole.UserRole)

        # Setup UI
        self._setup_ui()

        # Connect signals
        self._table_view.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )

    def _setup_ui(self) -> None:
        """设置用户界面。"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Statistics bar
        stats_layout = QHBoxLayout()
        self._stats_label = QLabel("无检测结果")
        self._stats_label.setStyleSheet("font-weight: bold;")
        stats_layout.addWidget(self._stats_label)
        stats_layout.addStretch()

        # Filter controls
        filter_group = QGroupBox("筛选")
        filter_layout = QHBoxLayout(filter_group)

        # Type filter
        filter_layout.addWidget(QLabel("缺陷类型:"))
        self._type_filter = QComboBox()
        self._type_filter.addItem("全部", None)
        for defect_type in DefectType:
            self._type_filter.addItem(
                DEFECT_LABELS.get(defect_type, defect_type.value),
                defect_type,
            )
        self._type_filter.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self._type_filter)

        # Confidence filter
        filter_layout.addWidget(QLabel("最低置信度:"))
        self._confidence_filter = QLineEdit()
        self._confidence_filter.setPlaceholderText("0.0")
        self._confidence_filter.setMaximumWidth(60)
        self._confidence_filter.returnPressed.connect(self._on_filter_changed)
        filter_layout.addWidget(self._confidence_filter)

        # Apply filter button
        self._apply_filter_btn = QPushButton("应用")
        self._apply_filter_btn.clicked.connect(self._on_filter_changed)
        filter_layout.addWidget(self._apply_filter_btn)

        # Clear filter button
        self._clear_filter_btn = QPushButton("清除")
        self._clear_filter_btn.clicked.connect(self._on_clear_filter)
        filter_layout.addWidget(self._clear_filter_btn)
        
        # Add stretch to align all filter controls to the left
        filter_layout.addStretch()

        layout.addLayout(stats_layout)
        layout.addWidget(filter_group)

        # Table view
        self._table_view = QTableView()
        self._table_view.setModel(self._proxy_model)
        self._table_view.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table_view.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._table_view.setSortingEnabled(True)
        self._table_view.verticalHeader().setVisible(False)
        self._table_view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._table_view.setAlternatingRowColors(True)

        # Hide internal columns (x1, y1, x2, y2)
        for col in range(DefectTableModel.Columns.X1, DefectTableModel.Columns.Y2 + 1):
            self._table_view.setColumnHidden(col, True)

        layout.addWidget(self._table_view)

    def set_detections(self, detections: list[DetectionResult]) -> None:
        """Set detection results to display."""
        self._model.set_detections(detections)
        self._update_statistics()

    def clear(self) -> None:
        """清空所有检测结果。"""
        self._model.clear()
        self._update_statistics()

    def get_selected_detection(self) -> Optional[DetectionResult]:
        """获取当前选中的检测结果。"""
        indices = self._table_view.selectionModel().selectedRows()
        if indices:
            # Map through proxy model
            source_index = self._proxy_model.mapToSource(indices[0])
            return self._model.get_detection(source_index.row())
        return None

    def _update_statistics(self) -> None:
        """更新统计信息显示。"""
        detections = self._model._detections

        if not detections:
            self._stats_label.setText("无检测结果")
            return

        # Count by type
        type_counts: dict[DefectType, int] = {dt: 0 for dt in DefectType}
        for d in detections:
            type_counts[d.defect_type] += 1

        # Format stats
        stats_parts = [f"总计: {len(detections)} 个缺陷"]
        for dt, count in type_counts.items():
            if count > 0:
                label = DEFECT_LABELS.get(dt, dt.value)
                stats_parts.append(f" | {label}: {count}")

        self._stats_label.setText(" ".join(stats_parts))

    def _on_filter_changed(self) -> None:
        """处理筛选条件变化。"""
        # Get filter values
        defect_type = self._type_filter.currentData()
        min_confidence_str = self._confidence_filter.text().strip()

        # Parse confidence
        min_confidence = 0.0
        if min_confidence_str:
            try:
                # Input is percentage (0-100) or ratio (0-1)
                value = float(min_confidence_str)
                if value > 1:
                    value = value / 100
                min_confidence = value
            except ValueError:
                pass

        # Apply type filter
        if defect_type is None:
            self._proxy_model.setFilterKeyColumn(DefectTableModel.Columns.TYPE)
            self._proxy_model.setFilterRegularExpression("")
        else:
            self._proxy_model.setFilterKeyColumn(DefectTableModel.Columns.TYPE)
            import re

            # DEFECT_LABELS.get() 返回 str | None，需要确保不为 None
            label: str = DEFECT_LABELS.get(defect_type) or defect_type.value
            self._proxy_model.setFilterRegularExpression(f"^{re.escape(label)}$")

        # Apply confidence filter
        if min_confidence > 0:
            self._proxy_model.setFilterKeyColumn(DefectTableModel.Columns.CONFIDENCE)
            # For numeric filtering, we need a different approach
            # Use sort/filter for numeric comparison
            threshold_pattern = f".*[5-9]\\d%|100%" if min_confidence >= 0.5 else ".*"
            self._proxy_model.setFilterRegularExpression(threshold_pattern)

        self.filter_changed.emit(
            defect_type.value if defect_type else "all",
            min_confidence,
        )

    def _on_clear_filter(self) -> None:
        """清除所有筛选条件。"""
        self._type_filter.setCurrentIndex(0)
        self._confidence_filter.clear()
        self._proxy_model.setFilterRegularExpression("")

    def _on_selection_changed(self, selected: any, deselected: any) -> None:
        """处理行选择变化。"""
        indices = self._table_view.selectionModel().selectedRows()
        if indices:
            source_index = self._proxy_model.mapToSource(indices[0])
            self.detection_selected.emit(source_index.row())


class StatisticsWidget(QWidget):
    """Widget for displaying detection statistics."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初始化统计信息小部件。"""
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置用户界面。"""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("检测统计")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        # Stats grid
        self._stats_layout = QVBoxLayout()
        layout.addLayout(self._stats_layout)

        layout.addStretch()

    def update_statistics(
        self, detections: list[DetectionResult], total_area: float = 0.0
    ) -> None:
        """
        Update statistics display.

        Args:
            detections: List of detection results
            total_area: Total image area for defect density calculation
        """
        # Clear existing - need to remove both widgets and layouts
        while self._stats_layout.count():
            item = self._stats_layout.takeAt(0)
            if item:
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    # Recursively clear nested layouts
                    self._clear_layout(item.layout())
                    item.layout().deleteLater()

        if not detections:
            no_data = QLabel("暂无数据")
            no_data.setStyleSheet("color: gray;")
            self._stats_layout.addWidget(no_data)
            return

        # Count by type
        type_counts: dict[DefectType, int] = {dt: 0 for dt in DefectType}
        for d in detections:
            type_counts[d.defect_type] += 1

        # Average confidence
        avg_confidence = sum(d.confidence for d in detections) / len(detections)

        # Defect density (per mm² assuming 1px = 0.05mm)
        total_defect_area = sum(d.area for d in detections)
        if total_area > 0:
            density = (
                (total_defect_area * 0.0025) / (total_area * 0.0025) * 100
            )  # Percentage
        else:
            density = 0.0

        # Add stats
        self._add_stat_row("总缺陷数", str(len(detections)))
        self._add_stat_row("平均置信度", f"{avg_confidence:.1%}")
        self._add_stat_row("缺陷密度", f"{density:.1f}%")

        # Add separator
        separator = QLabel("─── 按类型 ───")
        separator.setStyleSheet("color: gray; font-size: 10px;")
        self._stats_layout.addWidget(separator)

        # Add per-type counts
        for dt, count in type_counts.items():
            if count > 0:
                label = DEFECT_LABELS.get(dt, dt.value)
                self._add_stat_row(label, str(count))

    def _add_stat_row(self, label: str, value: str) -> None:
        """Add a stat row."""
        row_layout = QHBoxLayout()
        row_layout.addWidget(QLabel(label))
        row_layout.addStretch()
        value_label = QLabel(value)
        value_label.setStyleSheet("font-weight: bold;")
        row_layout.addWidget(value_label)
        self._stats_layout.addLayout(row_layout)

    def _clear_layout(self, layout: QLayout) -> None:
        """Recursively clear a layout."""
        while layout.count():
            item = layout.takeAt(0)
            if item:
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    self._clear_layout(item.layout())
                    item.layout().deleteLater()
