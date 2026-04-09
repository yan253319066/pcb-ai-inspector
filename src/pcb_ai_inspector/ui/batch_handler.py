"""
PCB AI Inspector 批量检测处理器模块。

处理批量检测的业务逻辑和信号转发，
作为 DetectionPipeline 和 MainWindow 之间的适配器。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal

if TYPE_CHECKING:
    from .detection_pipeline import DetectionPipeline, DetectionWorker, BatchResult
    from .detection_result_handler import DetectionResultHandler
    from .defect_overlay import DetectionResult


class BatchHandlerSignals(QObject):
    """批量处理器信号。"""

    # 任务完成: (image_name, detections, original_image, marked_image)
    task_completed = pyqtSignal(str, list, object, object)

    # 任务失败: (image_name, error_message)
    task_failed = pyqtSignal(str, str)

    # 进度更新: (current, total, image_name)
    progress_updated = pyqtSignal(int, int, str)

    # 批量完成: (BatchResult)
    batch_completed = pyqtSignal(object)

    # 批量取消
    batch_cancelled = pyqtSignal()

    # 状态变化: (status_message)
    status_changed = pyqtSignal(str)


class BatchDetectionHandler:
    """
    批量检测处理器。

    负责管理批量检测的流程，连接 DetectionPipeline 的工作线程信号，
    并将其转换为 UI 更新的事件。

    Signals (via signals attribute):
        task_completed(image_name, detections, original_image, marked_image)
        task_failed(image_name, error_message)
        progress_updated(current, total, image_name)
        batch_completed(BatchResult)
        batch_cancelled()
        status_changed(str)
    """

    def __init__(
        self,
        pipeline: Optional["DetectionPipeline"] = None,
        result_handler: Optional["DetectionResultHandler"] = None,
    ) -> None:
        """初始化批量检测处理器。"""
        self._pipeline = pipeline
        self._result_handler = result_handler
        self._worker: Optional["DetectionWorker"] = None
        self._is_running = False

        # 存储所有结果 {image_path: {'detections': [], 'marked_image': np.ndarray, 'image': np.ndarray}}
        self._all_results: dict[str, dict] = {}

        # 信号对象
        self.signals = BatchHandlerSignals()

    def set_pipeline(self, pipeline: "DetectionPipeline") -> None:
        """设置检测管道。"""
        self._pipeline = pipeline

    def set_result_handler(self, handler: "DetectionResultHandler") -> None:
        """设置结果处理器。"""
        self._result_handler = handler

    def start_batch(
        self, image_paths: list[Path], confidence: float
    ) -> "DetectionWorker":
        """
        开始批量检测。

        Args:
            image_paths: 要处理的图像路径列表
            confidence: 置信度阈值

        Returns:
            DetectionWorker 实例
        """
        if self._pipeline is None:
            raise RuntimeError("Pipeline not set")

        # 清空之前的结果
        self._all_results.clear()
        self._is_running = True

        # 启动批量检测
        self._worker = self._pipeline.detect_batch(
            image_paths,
            confidence_threshold=confidence,
        )

        # 连接信号
        self._worker.progress.connect(self._on_progress)
        self._worker.task_completed.connect(self._on_task_completed)
        self._worker.task_failed.connect(self._on_task_failed)
        self._worker.batch_completed.connect(self._on_batch_completed)
        self._worker.cancelled.connect(self._on_batch_cancelled)

        # 启动工作线程
        self._worker.start()

        self.signals.status_changed.emit("正在批量检测...")

        return self._worker

    def cancel(self) -> None:
        """取消当前批量检测。"""
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()

    def get_all_results(self) -> dict[str, dict]:
        """获取所有检测结果。"""
        return self._all_results

    def is_running(self) -> bool:
        """检查是否正在运行。"""
        return self._is_running

    def clear_results(self) -> None:
        """清空存储的结果。"""
        self._all_results.clear()

    def _on_progress(self, current: int, total: int, image_name: str) -> None:
        """处理进度更新。"""
        self.signals.progress_updated.emit(current, total, image_name)
        self.signals.status_changed.emit(f"正在检测: {image_name} ({current}/{total})")

    def _on_task_completed(self, task_id: str, detections: list) -> None:
        """处理单个任务完成。"""
        # 延迟导入避免循环依赖
        import cv2

        image_path = Path(task_id)
        image_name = image_path.name

        # 加载图像
        original_image = None
        marked_image = None
        ui_detections = None

        try:
            original_image = cv2.imread(str(image_path))
            if original_image is not None:
                # 转换检测结果
                if self._result_handler:
                    ui_detections = self._result_handler.convert_to_ui_result(
                        detections
                    )
                else:
                    ui_detections = detections
                # 不使用 draw_detections_on_image，直接使用原始图像
                marked_image = original_image
        except Exception:
            pass

        # 存储结果
        self._all_results[task_id] = {
            "detections": ui_detections if ui_detections is not None else detections,
            "marked_image": marked_image,
            "image": original_image,
        }

        # 发送信号
        self.signals.task_completed.emit(
            image_name,
            ui_detections if ui_detections is not None else detections,
            original_image,
            marked_image,
        )

    def _on_task_failed(self, task_id: str, error_message: str) -> None:
        """处理单个任务失败。"""
        image_name = Path(task_id).name

        # 存储失败结果
        self._all_results[task_id] = {
            "detections": [],
            "marked_image": None,
            "image": None,
            "error": error_message,
        }

        # 发送信号
        self.signals.task_failed.emit(image_name, error_message)

    def _on_batch_completed(self, result: "BatchResult") -> None:
        """处理批量检测完成。"""
        self._is_running = False
        self._worker = None

        # 发送信号
        self.signals.batch_completed.emit(result)
        self.signals.status_changed.emit(
            f"批量检测完成: {result.successful}/{result.total_images} 成功"
        )

    def _on_batch_cancelled(self) -> None:
        """处理批量检测取消。"""
        self._is_running = False
        self._worker = None

        # 发送信号
        self.signals.batch_cancelled.emit()
        self.signals.status_changed.emit("批量检测已取消")
