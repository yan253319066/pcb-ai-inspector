"""
PCB AI Inspector 历史记录对话框。

显示带有过滤和统计信息的检测历史。
窗口属性从配置读取。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QGroupBox,
    QHeaderView,
    QMessageBox,
    QWidget,
    QComboBox,
    QLineEdit,
)

from ..core.history import HistoryManager, get_history_manager, DetectionRecord
from ..core.settings import get_settings_manager


class HistoryDialog(QDialog):
    """显示检测历史的对话框。"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize history dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._manager = get_history_manager()

        # 从设置获取对话框尺寸
        ui_settings = get_settings_manager().settings.ui_layout
        self.setWindowTitle("检测历史")
        self.setMinimumSize(
            ui_settings.history_dialog_width, ui_settings.history_dialog_height
        )

        self._setup_ui()
        self._load_history()

    def _setup_ui(self) -> None:
        """Setup the UI."""
        self.setWindowTitle("检测历史")
        self.setMinimumSize(900, 550)

        layout = QVBoxLayout(self)

        # 过滤条件区域
        filter_group = QGroupBox("过滤条件")
        filter_layout = QHBoxLayout(filter_group)

        # 日期过滤
        filter_layout.addWidget(QLabel("日期:"))
        self._date_input = QLineEdit()
        self._date_input.setPlaceholderText("YYYY-MM-DD")
        self._date_input.setMaximumWidth(120)
        filter_layout.addWidget(self._date_input)

        # 工位过滤
        filter_layout.addWidget(QLabel("工位:"))
        self._station_input = QLineEdit()
        self._station_input.setPlaceholderText("工位名称")
        self._station_input.setMaximumWidth(100)
        filter_layout.addWidget(self._station_input)

        # 班次过滤
        filter_layout.addWidget(QLabel("班次:"))
        self._shift_input = QComboBox()
        self._shift_input.setEditable(True)
        self._shift_input.addItems(["", "日班", "夜班", "早班", "中班", "晚班"])
        self._shift_input.setMaximumWidth(100)
        filter_layout.addWidget(self._shift_input)

        # 结果过滤
        filter_layout.addWidget(QLabel("结果:"))
        self._result_filter = QComboBox()
        self._result_filter.addItems(["", "PASS", "FAIL"])
        self._result_filter.setMaximumWidth(80)
        filter_layout.addWidget(self._result_filter)

        # 查询按钮
        self._query_btn = QPushButton("查询")
        self._query_btn.clicked.connect(self._load_history)
        filter_layout.addWidget(self._query_btn)

        # 清除过滤按钮
        self._clear_filter_btn = QPushButton("清除过滤")
        self._clear_filter_btn.clicked.connect(self._clear_filter)
        filter_layout.addWidget(self._clear_filter_btn)

        filter_layout.addStretch()

        layout.addWidget(filter_group)

        # 统计信息
        stats = self._manager.get_statistics()

        stats_group = QGroupBox("统计信息")
        stats_layout = QHBoxLayout(stats_group)

        stats_layout.addWidget(QLabel(f"总检测次数: <b>{stats.total_detections}</b>"))
        stats_layout.addWidget(QLabel(f"总缺陷数: <b>{stats.total_defects}</b>"))
        stats_layout.addWidget(
            QLabel(f"成功率: <b>{stats.success_count}/{stats.total_detections}</b>")
        )
        stats_layout.addWidget(
            QLabel(f"平均处理时间: <b>{stats.average_processing_time_ms:.0f}ms</b>")
        )
        stats_layout.addStretch()

        layout.addWidget(stats_group)

        # 表格 - 增加列数显示工业字段
        self._table = QTableWidget()
        self._table.setColumnCount(9)
        self._table.setHorizontalHeaderLabels(
            [
                "时间",
                "生产线",
                "工位",
                "班次",
                "结果",
                "图像名称",
                "缺陷数",
                "处理时间",
                "状态",
            ]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.itemDoubleClicked.connect(self._on_double_click)
        self._table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self._table)

        # 按钮区域
        button_layout = QHBoxLayout()

        self._refresh_btn = QPushButton("刷新")
        self._refresh_btn.clicked.connect(self._load_history)
        button_layout.addWidget(self._refresh_btn)

        self._view_image_btn = QPushButton("查看图像")
        self._view_image_btn.clicked.connect(self._view_selected_image)
        button_layout.addWidget(self._view_image_btn)

        self._delete_btn = QPushButton("删除选中")
        self._delete_btn.clicked.connect(self._delete_selected)
        button_layout.addWidget(self._delete_btn)

        self._clear_btn = QPushButton("清空历史")
        self._clear_btn.clicked.connect(self._clear_history)
        button_layout.addWidget(self._clear_btn)

        button_layout.addStretch()

        self._close_btn = QPushButton("关闭")
        self._close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self._close_btn)

        layout.addLayout(button_layout)

    def _load_history(self) -> None:
        """Load detection history into table with filters."""
        # 获取过滤条件
        date_filter = self._date_input.text().strip()
        station_filter = self._station_input.text().strip()
        shift_filter = self._shift_input.currentText().strip()
        result_filter = self._result_filter.currentText().strip()

        # 根据过滤条件查询
        records: list[DetectionRecord] = []

        if date_filter:
            records = self._manager.query_by_date(date_filter)
        elif station_filter:
            records = self._manager.query_by_station(station_filter)
        elif shift_filter:
            records = self._manager.query_by_shift(shift_filter)
        else:
            records = self._manager.get_recent_detections(limit=200)

        # 客户端过滤（结果筛选）
        if result_filter:
            records = [r for r in records if r.result == result_filter]

        # 显示记录数
        self._table.setRowCount(len(records))

        for row, record in enumerate(records):
            # 时间
            time_str = (
                record.timestamp[:19].replace("T", " ") if record.timestamp else ""
            )
            time_item = QTableWidgetItem(time_str)
            time_item.setData(Qt.ItemDataRole.UserRole, record.id)
            self._table.setItem(row, 0, time_item)

            # 生产线
            self._table.setItem(row, 1, QTableWidgetItem(record.production_line or "-"))

            # 工位
            self._table.setItem(row, 2, QTableWidgetItem(record.station_name or "-"))

            # 班次
            self._table.setItem(row, 3, QTableWidgetItem(record.shift_config or "-"))

            # 结果 (PASS/FAIL)
            result_text = record.result or "-"
            result_item = QTableWidgetItem(result_text)
            if result_text == "PASS":
                result_item.setBackground(Qt.GlobalColor.green)
            elif result_text == "FAIL":
                result_item.setBackground(Qt.GlobalColor.red)
            self._table.setItem(row, 4, result_item)

            # 图像名称
            self._table.setItem(row, 5, QTableWidgetItem(record.image_name))

            # 缺陷数
            defect_text = str(record.defect_count)
            defect_item = QTableWidgetItem(defect_text)
            if record.defect_count > 0:
                defect_item.setBackground(Qt.GlobalColor.yellow)
            self._table.setItem(row, 6, defect_item)

            # 处理时间
            time_ms = (
                f"{record.processing_time_ms:.0f}ms"
                if record.processing_time_ms
                else "-"
            )
            self._table.setItem(row, 7, QTableWidgetItem(time_ms))

            # 状态
            status_text = "成功" if record.status == "success" else record.status
            self._table.setItem(row, 8, QTableWidgetItem(status_text or "-"))

        # 调整列宽
        self._table.resizeColumnsToContents()
        self._table.setColumnWidth(0, 150)  # 时间
        self._table.setColumnWidth(5, 200)  # 图像名称

    def _clear_filter(self) -> None:
        """Clear all filters."""
        self._date_input.clear()
        self._station_input.clear()
        self._shift_input.setCurrentIndex(0)
        self._result_filter.setCurrentIndex(0)
        self._load_history()

    def _delete_selected(self) -> None:
        """Delete selected history record."""
        current_row = self._table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "提示", "请先选择要删除的记录")
            return

        item = self._table.item(current_row, 0)
        if item is None:
            return

        record_id = item.data(Qt.ItemDataRole.UserRole)

        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除这条记录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._manager.delete_record(record_id)
            self._load_history()

    def _clear_history(self) -> None:
        """Clear all history."""
        reply = QMessageBox.question(
            self,
            "确认清空",
            "确定要清空所有检测历史吗？此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._manager.clear_history()
            self._load_history()
            QMessageBox.information(self, "完成", "历史记录已清空")

    def _on_double_click(self, item: object = None) -> None:
        """双击表格查看图像。"""
        self._view_selected_image()

    def _view_selected_image(self) -> None:
        """查看选中的图像。"""
        current_row = self._table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "提示", "请先选择要查看的记录")
            return

        # 获取图像名称
        image_name_item = self._table.item(current_row, 5)
        if image_name_item is None:
            return

        image_name = image_name_item.text()

        # 获取该记录的所有信息
        time_item = self._table.item(current_row, 0)
        if time_item is None:
            return

        record_id = time_item.data(Qt.ItemDataRole.UserRole)
        record = self._manager.get_detection(record_id)

        if record is None:
            QMessageBox.warning(self, "提示", "无法获取记录详情")
            return

        # 检查是否有保存的图像
        if record.marked_image_path:
            image_path = Path(record.marked_image_path)
            if image_path.exists():
                self._show_image_dialog(image_path, record)
                return
            else:
                QMessageBox.information(
                    self, "提示", f"标注图文件不存在:\n{record.marked_image_path}"
                )
                return

        # 如果没有保存的图像，尝试从原图路径加载
        if record.image_path:
            original_path = Path(record.image_path)
            if original_path.exists():
                self._show_image_dialog(original_path, record)
                return

        QMessageBox.information(self, "提示", "未找到保存的图像文件")

    def _show_image_dialog(self, image_path: Path, record) -> None:
        """显示图像对话框。"""
        from PyQt6.QtWidgets import (
            QDialog,
            QVBoxLayout,
            QLabel,
            QScrollArea,
            QPushButton,
        )
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtCore import Qt

        dialog = QDialog(self)
        dialog.setWindowTitle(f"检测图像 - {image_path.name}")
        dialog.setMinimumSize(800, 600)

        layout = QVBoxLayout(dialog)

        # 图像显示
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            QMessageBox.warning(self, "提示", "无法加载图像")
            return

        label = QLabel()
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll_area.setWidget(label)
        layout.addWidget(scroll_area)

        # 信息显示
        info_label = QLabel(
            f"<b>时间:</b> {record.timestamp}<br>"
            f"<b>结果:</b> {record.result}<br>"
            f"<b>缺陷数:</b> {record.defect_count}<br>"
            f"<b>处理时间:</b> {record.processing_time_ms:.0f}ms"
        )
        layout.addWidget(info_label)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec()


if __name__ == "__main__":
    # Test dialog
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    dialog = HistoryDialog()
    dialog.exec()
