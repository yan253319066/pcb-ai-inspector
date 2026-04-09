"""
PCB AI Inspector 日志配置模块。

提供集中式日志设置，包括：
- 文件和控制台处理器
- 轮转支持
- 模块特定日志记录器
- 性能日志记录
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


# 默认日志目录
DEFAULT_LOG_DIR = Path("logs")
DEFAULT_LOG_LEVEL = logging.INFO


class ColoredFormatter(logging.Formatter):
    """支持控制台输出颜色的自定义格式化器。"""

    # ANSI 颜色代码
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """使用颜色格式化日志记录。"""
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        return super().format(record)


def get_log_dir() -> Path:
    """获取或创建日志目录。

    返回:
        日志目录的路径
    """
    log_dir = DEFAULT_LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def setup_logging(
    log_level: int = DEFAULT_LOG_LEVEL,
    log_dir: Optional[Path] = None,
    console_output: bool = True,
    file_output: bool = True,
    rotation_max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    rotation_backup_count: int = 5,
) -> logging.Logger:
    """为应用程序设置日志。

    参数:
        log_level: 日志级别（默认: INFO）
        log_dir: 日志文件目录（默认: logs/）
        console_output: 启用控制台输出
        file_output: 启用文件输出
        rotation_max_bytes: 轮转前的最大大小
        rotation_backup_count: 保留的备份文件数量

    返回:
        根日志记录器实例
    """
    # Get log directory
    if log_dir is None:
        log_dir = get_log_dir()

    # Root logger
    root_logger = logging.getLogger("pcb_ai_inspector")
    root_logger.setLevel(log_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create formatters
    file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_formatter = ColoredFormatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # File handler with rotation
    if file_output:
        log_file = log_dir / f"pcb_inspector_{datetime.now():%Y%m%d}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_file),
            maxBytes=rotation_max_bytes,
            backupCount=rotation_backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """获取特定模块的日志记录器。

    参数:
        name: 模块名称（通常是 __name__）

    返回:
        日志记录器实例
    """
    return logging.getLogger(f"pcb_ai_inspector.{name}")


class OperationLogger:
    """用于跟踪用户操作和系统事件的日志记录器。"""

    def __init__(self, name: str = "operations") -> None:
        """初始化操作日志记录器。

        参数:
            name: 日志记录器名称后缀
        """
        self._logger = get_logger(f"ops.{name}")
        self._start_time: Optional[datetime] = None

    def info(self, message: str, **kwargs: object) -> None:
        """记录信息消息。"""
        self._logger.info(message, extra=self._format_extra(kwargs))

    def warning(self, message: str, **kwargs: object) -> None:
        """记录警告消息。"""
        self._logger.warning(message, extra=self._format_extra(kwargs))

    def error(self, message: str, **kwargs: object) -> None:
        """记录错误消息。"""
        self._logger.error(message, extra=self._format_extra(kwargs))

    def start_operation(self, operation: str, **kwargs: object) -> None:
        """标记操作开始。

        参数:
            operation: 操作名称
            **kwargs: 附加上下文数据
        """
        self._start_time = datetime.now()
        self._logger.info(
            f"操作开始: {operation}",
            extra=self._format_extra({"operation": operation, **kwargs}),
        )

    def end_operation(
        self, operation: str, success: bool = True, **kwargs: object
    ) -> float:
        """标记操作结束并返回持续时间。

        参数:
            operation: 操作名称
            success: 操作是否成功
            **kwargs: 附加上下文数据

        返回:
            持续时间（秒）
        """
        if self._start_time is None:
            duration = 0.0
        else:
            duration = (datetime.now() - self._start_time).total_seconds()
            self._start_time = None

        status = "完成" if success else "失败"
        self._logger.info(
            f"操作 {status}: {operation} ({duration:.2f}秒)",
            extra=self._format_extra(
                {
                    "operation": operation,
                    "status": status,
                    "duration_seconds": duration,
                    **kwargs,
                }
            ),
        )
        return duration

    @staticmethod
    def _format_extra(kwargs: dict) -> dict:
        """格式化日志的额外数据。"""
        return {"extra_data": kwargs} if kwargs else {}


def log_function_call(func):
    """记录函数调用及其执行时间的装饰器。

    使用方法:
        @log_function_call
        def my_function(arg1, arg2):
            pass
    """
    import functools
    import time

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()

        logger.debug(f"调用 {func.__name__}，参数: args={args}, kwargs={kwargs}")

        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.debug(f"{func.__name__} 完成，用时 {duration:.3f}秒")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{func.__name__} 失败，用时 {duration:.3f}秒: {e}")
            raise

    return wrapper


# 快速设置的便捷函数
def init_logging() -> logging.Logger:
    """使用默认设置初始化日志。

    返回:
        根日志记录器实例
    """
    return setup_logging()


if __name__ == "__main__":
    # Test logging
    logger = init_logging()
    logger.info("Logging initialized")
    logger.debug("Debug message")
    logger.warning("Warning message")
    logger.error("Error message")
