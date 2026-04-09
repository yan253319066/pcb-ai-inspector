"""
PCB AI Inspector 批量检测管道。

处理多图像检测，支持进度跟踪、
取消操作和结果聚合。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Iterator

import cv2
import numpy as np
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from ..models.detector import YOLODetector, DetectionResult
from ..core.settings import get_settings_manager
from ..core.defect_types import DefectType


logger = logging.getLogger(__name__)


class DetectionStatus(Enum):
    """检测任务的状态。"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DetectionMode(Enum):
    """检测模式。"""

    SINGLE = "single"
    BATCH = "batch"
    CONTINUOUS = "continuous"


@dataclass
class DetectionTask:
    """A single detection task."""

    id: str
    image_path: Path
    status: DetectionStatus = DetectionStatus.PENDING
    detections: list[DetectionResult] = field(default_factory=list)
    error: Optional[str] = None
    processing_time_ms: float = 0.0

    @property
    def has_defects(self) -> bool:
        """Check if task has any defects detected."""
        return len(self.detections) > 0

    @property
    def defect_count(self) -> int:
        """Get number of defects detected."""
        return len(self.detections)


@dataclass
class BatchResult:
    """Result of a batch detection operation."""

    mode: DetectionMode
    total_images: int
    successful: int
    failed: int
    cancelled: int
    total_defects: int
    tasks: list[DetectionTask]
    start_time: datetime
    end_time: datetime
    processing_time_seconds: float

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_images == 0:
            return 0.0
        return self.successful / self.total_images

    @property
    def defects_per_image(self) -> float:
        """Calculate average defects per image."""
        if self.successful == 0:
            return 0.0
        return self.total_defects / self.successful

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "mode": self.mode.value,
            "total_images": self.total_images,
            "successful": self.successful,
            "failed": self.failed,
            "cancelled": self.cancelled,
            "total_defects": self.total_defects,
            "success_rate": f"{self.success_rate:.1%}",
            "defects_per_image": f"{self.defects_per_image:.1f}",
            "processing_time": f"{self.processing_time_seconds:.1f}s",
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
        }


class DetectionWorker(QThread):
    """
    Worker thread for running detection tasks.

    Emits signals for progress updates and completion.
    """

    # Signals
    progress = pyqtSignal(int, int, str)  # current, total, current_image_name
    task_completed = pyqtSignal(str, list)  # task_id, detections
    task_failed = pyqtSignal(str, str)  # task_id, error_message
    batch_completed = pyqtSignal(object)  # BatchResult
    cancelled = pyqtSignal()

    def __init__(
        self,
        detector: YOLODetector,
        mode: DetectionMode,
        image_paths: list[Path],
        confidence_threshold: float = 0.5,
        parent: Optional[QObject] = None,
    ) -> None:
        """Initialize the detection worker.

        Args:
            detector: YOLO detector instance
            mode: Detection mode
            image_paths: List of image paths to process
            confidence_threshold: Minimum confidence for detections
        """
        super().__init__(parent)
        self._detector = detector
        self._mode = mode
        self._image_paths = image_paths
        self._confidence_threshold = confidence_threshold
        self._tasks: list[DetectionTask] = []
        self._is_cancelled = False
        self._start_time = datetime.now()

    def run(self) -> None:
        """Run the detection worker."""
        total = len(self._image_paths)

        for idx, image_path in enumerate(self._image_paths):
            if self._is_cancelled:
                # Mark remaining tasks as cancelled
                for remaining_path in self._image_paths[idx:]:
                    task = DetectionTask(
                        id=str(remaining_path),
                        image_path=remaining_path,
                        status=DetectionStatus.CANCELLED,
                    )
                    self._tasks.append(task)
                self.cancelled.emit()
                break

            task = DetectionTask(id=str(image_path), image_path=image_path)
            self._tasks.append(task)

            # Emit progress
            self.progress.emit(idx + 1, total, image_path.name)

            try:
                # Load image
                image = cv2.imread(str(image_path))
                if image is None:
                    raise ValueError(f"Failed to load image: {image_path}")

                # Run detection
                import time

                # Set confidence threshold
                self._detector.set_confidence_threshold(self._confidence_threshold)

                start = time.perf_counter()
                result = self._detector.detect(image)
                detections = result.detections
                elapsed = (time.perf_counter() - start) * 1000

                # Use detections directly (already DetectionResult objects)
                results = detections

                task.status = DetectionStatus.COMPLETED
                task.detections = results
                task.processing_time_ms = elapsed

                self.task_completed.emit(task.id, results)

            except Exception as e:
                task.status = DetectionStatus.FAILED
                task.error = str(e)
                logger.error(f"Detection failed for {image_path}: {e}")
                self.task_failed.emit(task.id, str(e))

        # Create batch result
        end_time = datetime.now()
        completed_tasks = [
            t for t in self._tasks if t.status == DetectionStatus.COMPLETED
        ]
        failed_tasks = [t for t in self._tasks if t.status == DetectionStatus.FAILED]
        cancelled_tasks = [
            t for t in self._tasks if t.status == DetectionStatus.CANCELLED
        ]

        result = BatchResult(
            mode=self._mode,
            total_images=total,
            successful=len(completed_tasks),
            failed=len(failed_tasks),
            cancelled=len(cancelled_tasks),
            total_defects=sum(t.defect_count for t in completed_tasks),
            tasks=self._tasks,
            start_time=self._start_time,
            end_time=end_time,
            processing_time_seconds=(end_time - self._start_time).total_seconds(),
        )

        self.batch_completed.emit(result)

    def cancel(self) -> None:
        """Cancel the worker."""
        self._is_cancelled = True


class DetectionPipeline:
    """Main detection pipeline manager for batch processing."""

    def __init__(self, model_path: Optional[Path] = None) -> None:
        """Initialize the detection pipeline.

        Args:
            model_path: Optional path to the YOLO model file
        """
        self._model_path = model_path
        self._detector: Optional[YOLODetector] = None
        self._worker: Optional["DetectionWorker"] = None

    def load_model(self) -> None:
        """Load the YOLO model (强制重新加载以应用最新设置)."""
        # 强制重新加载设置
        settings_manager = get_settings_manager(force_reload=True)
        preprocessing_settings = {
            "enable_preprocessing": settings_manager.settings.preprocessing.enable_preprocessing,
            "lighting_preset": settings_manager.settings.preprocessing.lighting_preset,
            "binarization_method": settings_manager.settings.preprocessing.binarization_method,
            "enable_denoise": settings_manager.settings.preprocessing.enable_denoise,
            "denoise_kernel": settings_manager.settings.preprocessing.denoise_kernel,
            "adaptive_block_size": settings_manager.settings.preprocessing.adaptive_block_size,
            "adaptive_c": settings_manager.settings.preprocessing.adaptive_c,
            "fixed_threshold": settings_manager.settings.preprocessing.fixed_threshold,
            "enable_clahe": settings_manager.settings.preprocessing.enable_clahe,
            "clahe_clip_limit": settings_manager.settings.preprocessing.clahe_clip_limit,
            "clahe_tile_size": settings_manager.settings.preprocessing.clahe_tile_size,
            "enable_roi": settings_manager.settings.preprocessing.enable_roi,
            "roi_margin": settings_manager.settings.preprocessing.roi_margin,
            "roi_min_area_ratio": settings_manager.settings.preprocessing.roi_min_area_ratio,
        }

        # 重新创建检测器以应用新设置
        self._detector = YOLODetector(
            self._model_path,
            enable_preprocessing=preprocessing_settings["enable_preprocessing"],
        )
        # 设置预处理器
        if preprocessing_settings["enable_preprocessing"]:
            from ..models.detector import (
                BinarizationMethod,
                ImagePreprocessor,
                LightingPreset,
            )

            lighting_preset_str = preprocessing_settings["lighting_preset"]
            binarization_method_str = preprocessing_settings["binarization_method"]

            self._detector.preprocessor = ImagePreprocessor(
                lighting_preset=LightingPreset(lighting_preset_str)
                if lighting_preset_str != "unknown"
                else None,
                binarization_method=BinarizationMethod(binarization_method_str),
                enable_denoise=preprocessing_settings["enable_denoise"],
                denoise_kernel=preprocessing_settings["denoise_kernel"],
                adaptive_block_size=preprocessing_settings["adaptive_block_size"],
                adaptive_c=preprocessing_settings["adaptive_c"],
                fixed_threshold=preprocessing_settings["fixed_threshold"],
                enable_clahe=preprocessing_settings["enable_clahe"],
                clahe_clip_limit=preprocessing_settings["clahe_clip_limit"],
                clahe_tile_size=preprocessing_settings["clahe_tile_size"],
                enable_roi=preprocessing_settings["enable_roi"],
                roi_margin=preprocessing_settings["roi_margin"],
                roi_min_area_ratio=preprocessing_settings["roi_min_area_ratio"],
            )

        self._detector.load_model()

    def detect_single(
        self,
        image: np.ndarray,
        confidence_threshold: float = 0.5,
    ) -> list[DetectionResult]:
        """
        Detect defects in a single image.

        Args:
            image: Image as numpy array (BGR format)
            confidence_threshold: Minimum confidence for detections

        Returns:
            List of DetectionResult objects
        """
        if self._detector is None:
            self.load_model()

        if self._detector is None:
            raise RuntimeError("Detector not initialized")

        # 设置置信度阈值
        self._detector.confidence_threshold = confidence_threshold

        result = self._detector.detect(image)
        if result is None:
            return []
        return result.detections

    def detect_batch(
        self,
        image_paths: list[Path],
        confidence_threshold: float = 0.5,
        mode: DetectionMode = DetectionMode.BATCH,
    ) -> DetectionWorker:
        """
        Start batch detection.

        Args:
            image_paths: List of image paths to process
            confidence_threshold: Minimum confidence for detections
            mode: Detection mode

        Returns:
            DetectionWorker instance for progress tracking
        """
        # 每次批量检测前重新加载模型和设置
        self.load_model()

        if self._detector is None:
            raise RuntimeError("Detector not initialized")

        self._worker = DetectionWorker(
            detector=self._detector,
            mode=mode,
            image_paths=image_paths,
            confidence_threshold=confidence_threshold,
        )

        return self._worker

    def cancel(self) -> None:
        """Cancel the current batch if running."""
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()

    def get_supported_formats(self) -> list[str]:
        """Get list of supported image formats."""
        return [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"]

    def is_supported_format(self, path: Path) -> bool:
        """Check if a file is a supported image format."""
        return path.suffix.lower() in self.get_supported_formats()

    def scan_directory(self, directory: Path, recursive: bool = False) -> list[Path]:
        """
        Scan a directory for supported images.

        Args:
            directory: Directory to scan
            recursive: Whether to scan subdirectories

        Returns:
            List of image paths
        """
        if not directory.exists():
            return []

        image_paths = []
        extensions = self.get_supported_formats()

        if recursive:
            for ext in extensions:
                image_paths.extend(directory.rglob(f"*{ext}"))
        else:
            for ext in extensions:
                image_paths.extend(directory.glob(f"*{ext}"))

        return sorted(image_paths)
