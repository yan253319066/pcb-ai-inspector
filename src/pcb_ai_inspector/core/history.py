"""
PCB AI Inspector 检测历史模块。

提供：
- 检测历史存储和检索
- 统计聚合
- 历史过滤和搜索
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.defect_types import DefectType


@dataclass
class DetectionRecord:
    """单条检测记录。"""

    id: Optional[int] = None
    timestamp: str = ""
    image_path: str = ""
    image_name: str = ""
    defect_count: int = 0
    defects_json: str = ""  # JSON 序列化的缺陷列表
    confidence_threshold: float = 0.5
    processing_time_ms: float = 0.0
    device: str = ""
    status: str = "success"  # success, failed, cancelled
    # 工业场景字段
    production_line: str = ""  # 生产线
    station_name: str = ""  # 工位
    shift_config: str = ""  # 班次
    result: str = ""  # PASS / FAIL
    marked_image_path: str = ""  # 标注图路径


@dataclass
class DefectRecord:
    """检测记录中的单个缺陷。"""

    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    confidence: float
    defect_type: str
    class_id: int


@dataclass
class HistoryStatistics:
    """检测历史的统计信息。"""

    total_detections: int = 0
    total_defects: int = 0
    total_images: int = 0
    total_processing_time_ms: float = 0.0
    success_count: int = 0
    failed_count: int = 0
    defect_counts: dict[str, int] = field(default_factory=dict)
    average_defects_per_image: float = 0.0
    average_processing_time_ms: float = 0.0


class HistoryManager:
    """管理检测历史存储。"""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """初始化历史管理器。

        Args:
            db_path: SQLite 数据库文件路径
        """
        if db_path is None:
            data_dir = Path.home() / ".pcb-ai-inspector"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / "detection_history.db"

        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_database()

    def _init_database(self) -> None:
        """初始化数据库结构。"""
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row

        # 创建表
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                image_path TEXT NOT NULL,
                image_name TEXT NOT NULL,
                defect_count INTEGER DEFAULT 0,
                defects_json TEXT DEFAULT '[]',
                confidence_threshold REAL DEFAULT 0.5,
                processing_time_ms REAL DEFAULT 0.0,
                device TEXT DEFAULT '',
                status TEXT DEFAULT 'success',
                production_line TEXT DEFAULT '',
                station_name TEXT DEFAULT '',
                shift_config TEXT DEFAULT '',
                result TEXT DEFAULT '',
                marked_image_path TEXT DEFAULT ''
            )
        """)

        # 创建索引以加快查询
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON detections(timestamp DESC)
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_image_name 
            ON detections(image_name)
        """)

        # 数据库迁移：添加新列（如果不存在）
        self._migrate_schema()

        self._conn.commit()

    def _migrate_schema(self) -> None:
        """数据库Schema迁移 - 添加新列。"""
        # 检查并添加新列
        columns_to_add = [
            ("production_line", "TEXT DEFAULT ''"),
            ("station_name", "TEXT DEFAULT ''"),
            ("shift_config", "TEXT DEFAULT ''"),
            ("result", "TEXT DEFAULT ''"),
            ("marked_image_path", "TEXT DEFAULT ''"),
        ]

        for column_name, column_def in columns_to_add:
            try:
                self._conn.execute(
                    f"ALTER TABLE detections ADD COLUMN {column_name} {column_def}"
                )
            except sqlite3.OperationalError:
                # 列已存在，忽略
                pass

    def add_detection(
        self,
        image_path: str,
        defects: list,
        confidence_threshold: float = 0.5,
        processing_time_ms: float = 0.0,
        device: str = "",
        status: str = "success",
        production_line: str = "",
        station_name: str = "",
        shift_config: str = "",
        result: str = "",
        marked_image_path: str = "",
    ) -> int:
        """向历史记录添加检测记录。

        Args:
            image_path: 图像的完整路径
            defects: DetectionResult 对象列表
            confidence_threshold: 使用的置信度阈值
            processing_time_ms: 处理时间（毫秒）
            device: 检测使用的设备
            status: 检测状态
            production_line: 生产线名称
            station_name: 工位名称
            shift_config: 班次
            result: PASS/FAIL
            marked_image_path: 标注图路径

        Returns:
            插入记录的 ID
        """
        if self._conn is None:
            raise RuntimeError("数据库未连接")

        # 序列化缺陷
        defects_data = [
            {
                "bbox": list(d.bbox),
                "confidence": float(d.confidence),
                "defect_type": str(
                    d.defect_type.value
                    if hasattr(d.defect_type, "value")
                    else d.defect_type
                ),
                "class_id": getattr(d, "class_id", 0),
            }
            for d in defects
        ]

        image_path_obj = Path(image_path)

        cursor = self._conn.execute(
            """
            INSERT INTO detections (
                timestamp, image_path, image_name, defect_count,
                defects_json, confidence_threshold, processing_time_ms,
                device, status, production_line, station_name,
                shift_config, result, marked_image_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                datetime.now().isoformat(),
                str(image_path),
                image_path_obj.name,
                len(defects),
                json.dumps(defects_data),
                confidence_threshold,
                processing_time_ms,
                device,
                status,
                production_line,
                station_name,
                shift_config,
                result,
                marked_image_path,
            ),
        )

        self._conn.commit()
        return cursor.lastrowid or 0

    def get_recent_detections(self, limit: int = 50) -> list[DetectionRecord]:
        """获取最近的检测记录。

        Args:
            limit: 返回的最大记录数

        Returns:
            DetectionRecord 对象列表
        """
        if self._conn is None:
            return []

        cursor = self._conn.execute(
            """
            SELECT * FROM detections 
            ORDER BY timestamp DESC 
            LIMIT ?
        """,
            (limit,),
        )

        return [self._row_to_record(row) for row in cursor.fetchall()]

    def get_recent(self, limit: int = 100) -> list[DetectionRecord]:
        """获取最近的检测记录（简写方法）。

        Args:
            limit: 返回的最大记录数

        Returns:
            DetectionRecord 对象列表
        """
        return self.get_recent_detections(limit)

    def get_detection(self, record_id: int) -> Optional[DetectionRecord]:
        """获取特定的检测记录。

        Args:
            record_id: 记录 ID

        Returns:
            DetectionRecord 或 None
        """
        if self._conn is None:
            return None

        cursor = self._conn.execute(
            "SELECT * FROM detections WHERE id = ?", (record_id,)
        )
        row = cursor.fetchone()

        if row:
            return self._row_to_record(row)
        return None

    def search_by_name(self, name: str, limit: int = 50) -> list[DetectionRecord]:
        """按图像名称搜索检测。

        Args:
            name: 要搜索的图像名称
            limit: 最大结果数

        Returns:
            匹配的 DetectionRecord 列表
        """
        if self._conn is None:
            return []

        cursor = self._conn.execute(
            """
            SELECT * FROM detections 
            WHERE image_name LIKE ?
            ORDER BY timestamp DESC 
            LIMIT ?
        """,
            (f"%{name}%", limit),
        )

        return [self._row_to_record(row) for row in cursor.fetchall()]

    def query_by_date(self, date: str) -> list[DetectionRecord]:
        """按日期查询检测记录。

        Args:
            date: 日期字符串 YYYY-MM-DD

        Returns:
            匹配的 DetectionRecord 列表
        """
        if self._conn is None:
            return []

        cursor = self._conn.execute(
            """
            SELECT * FROM detections 
            WHERE date(timestamp) = ?
            ORDER BY timestamp DESC
        """,
            (date,),
        )

        return [self._row_to_record(row) for row in cursor.fetchall()]

    def query_by_station(self, station_name: str) -> list[DetectionRecord]:
        """按工位查询检测记录。

        Args:
            station_name: 工位名称

        Returns:
            匹配的 DetectionRecord 列表
        """
        if self._conn is None:
            return []

        cursor = self._conn.execute(
            """
            SELECT * FROM detections 
            WHERE station_name = ?
            ORDER BY timestamp DESC
            LIMIT 100
        """,
            (station_name,),
        )

        return [self._row_to_record(row) for row in cursor.fetchall()]

    def query_by_shift(self, shift_config: str) -> list[DetectionRecord]:
        """按班次查询检测记录。

        Args:
            shift_config: 班次名称

        Returns:
            匹配的 DetectionRecord 列表
        """
        if self._conn is None:
            return []

        cursor = self._conn.execute(
            """
            SELECT * FROM detections 
            WHERE shift_config = ?
            ORDER BY timestamp DESC
            LIMIT 500
        """,
            (shift_config,),
        )

        return [self._row_to_record(row) for row in cursor.fetchall()]

    def search_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[DetectionRecord]:
        """按日期范围搜索检测。

        Args:
            start_date: 开始日期时间
            end_date: 结束日期时间

        Returns:
            范围内的 DetectionRecord 列表
        """
        if self._conn is None:
            return []

        cursor = self._conn.execute(
            """
            SELECT * FROM detections 
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY timestamp DESC
        """,
            (start_date.isoformat(), end_date.isoformat()),
        )

        return [self._row_to_record(row) for row in cursor.fetchall()]

    def get_statistics(self, days: int = 30) -> HistoryStatistics:
        """获取检测历史的统计信息。

        Args:
            days: 包含的天数

        Returns:
            HistoryStatistics 对象
        """
        if self._conn is None:
            return HistoryStatistics()

        # 获取最近 N 天的记录
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)

        cursor = self._conn.execute(
            """
            SELECT 
                COUNT(*) as total_detections,
                SUM(defect_count) as total_defects,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN status != 'success' THEN 1 ELSE 0 END) as failed_count,
                AVG(defect_count) as avg_defects,
                AVG(processing_time_ms) as avg_time
            FROM detections
            WHERE timestamp >= ?
        """,
            (cutoff.isoformat(),),
        )

        row = cursor.fetchone()

        stats = HistoryStatistics()
        stats.total_detections = row["total_detections"] or 0
        stats.total_defects = row["total_defects"] or 0
        stats.total_images = stats.total_detections
        stats.success_count = row["success_count"] or 0
        stats.failed_count = row["failed_count"] or 0
        stats.average_defects_per_image = row["avg_defects"] or 0.0
        stats.average_processing_time_ms = row["avg_time"] or 0.0

        # 获取缺陷类型统计
        defect_cursor = self._conn.execute(
            """
            SELECT defects_json FROM detections WHERE timestamp >= ?
        """,
            (cutoff.isoformat(),),
        )

        defect_counts: dict[str, int] = {}
        for row in defect_cursor.fetchall():
            try:
                defects = json.loads(row["defects_json"])
                for d in defects:
                    defect_type = d.get("defect_type", "unknown")
                    defect_counts[defect_type] = defect_counts.get(defect_type, 0) + 1
            except Exception:
                pass

        stats.defect_counts = defect_counts

        return stats

    def delete_record(self, record_id: int) -> bool:
        """删除检测记录。

        Args:
            record_id: 要删除的记录 ID

        Returns:
            删除成功返回 True
        """
        if self._conn is None:
            return False

        cursor = self._conn.execute("DELETE FROM detections WHERE id = ?", (record_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def clear_history(self) -> None:
        """清除所有检测历史。"""
        if self._conn is None:
            return

        self._conn.execute("DELETE FROM detections")
        self._conn.commit()

    def _row_to_record(self, row: sqlite3.Row) -> DetectionRecord:
        """将数据库行转换为 DetectionRecord。"""
        # 将 Row 转换为字典（支持 .get() 方法）
        row_dict = dict(row)

        return DetectionRecord(
            id=row_dict["id"],
            timestamp=row_dict["timestamp"],
            image_path=row_dict["image_path"],
            image_name=row_dict["image_name"],
            defect_count=row_dict["defect_count"],
            defects_json=row_dict["defects_json"],
            confidence_threshold=row_dict["confidence_threshold"],
            processing_time_ms=row_dict["processing_time_ms"],
            device=row_dict["device"],
            status=row_dict["status"],
            production_line=row_dict.get("production_line", ""),
            station_name=row_dict.get("station_name", ""),
            shift_config=row_dict.get("shift_config", ""),
            result=row_dict.get("result", ""),
            marked_image_path=row_dict.get("marked_image_path", ""),
        )

    def close(self) -> None:
        """关闭数据库连接。"""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "HistoryManager":
        """上下文管理器入口。"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器出口。"""
        self.close()


# 单例实例
_history_manager: Optional[HistoryManager] = None


def get_history_manager() -> HistoryManager:
    """获取全局历史管理器实例。

    Returns:
        HistoryManager 单例
    """
    global _history_manager
    if _history_manager is None:
        _history_manager = HistoryManager()
    return _history_manager


if __name__ == "__main__":
    # 测试历史管理器
    print("=" * 50)
    print("历史管理器测试")
    print("=" * 50)

    # 创建管理器
    manager = HistoryManager(Path("test_history.db"))

    # 添加测试记录
    print("\n添加测试记录...")
    manager.add_detection(
        image_path="/test/image1.png",
        defects=[],
        processing_time_ms=150.0,
        device="CUDA",
    )
    manager.add_detection(
        image_path="/test/image2.png",
        defects=[],
        processing_time_ms=200.0,
        device="CUDA",
    )

    # 获取最近记录
    records = manager.get_recent_detections()
    print(f"最近记录: {len(records)}")
    for r in records:
        print(f"  - {r.image_name}: {r.defect_count} 个缺陷")

    # 统计信息
    stats = manager.get_statistics()
    print(f"\n统计信息:")
    print(f"  总检测次数: {stats.total_detections}")
    print(f"  总缺陷数: {stats.total_defects}")

    # 清理
    manager.clear_history()
    manager.close()

    # 删除测试数据库
    Path("test_history.db").unlink(missing_ok=True)
    print("\n测试完成！")
