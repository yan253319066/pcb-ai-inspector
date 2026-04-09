"""
PCB AI Inspector - 主入口点

本模块提供 PCB 缺陷检测软件的主应用程序入口点。
"""

import sys
import os
from pathlib import Path

from loguru import logger


def setup_logging(log_dir: Path | None = None) -> None:
    """配置应用程序的日志系统。

    参数:
        log_dir: 日志文件目录。默认为 ~/.pcb-ai-inspector/logs
    """
    if log_dir is None:
        log_dir = Path.home() / ".pcb-ai-inspector" / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)

    logger.remove()

    logger.add(
        log_dir / "app_{time}.log",
        rotation="10 MB",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    if sys.stdout is not None:
        logger.add(
            sys.stdout,
            level="INFO",
            format="{time:HH:mm:ss} | {level} | {message}",
        )


def main() -> int:
    """应用程序主入口点。

    返回:
        退出码（0 表示成功，非零表示失败）
    """
    setup_logging()
    logger.info("=" * 50)
    logger.info("PCB AI Inspector 启动中...")
    logger.info("=" * 50)

    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt

        app = QApplication(sys.argv)
        app.setApplicationName("PCB AI Inspector")
        app.setOrganizationName("PCB-AI")
        app.setApplicationVersion("1.0.0")

        if not getattr(sys, "frozen", False):
            from pcb_ai_inspector.core.activation import check_activation
            if not check_activation().state == "activated":
                logger.warning("许可证检查失败")
                return 1

        from pcb_ai_inspector.ui.main_window import MainWindow

        window = MainWindow()
        window.show()

        logger.info("应用程序窗口已显示")
        return app.exec()

    except Exception as e:
        logger.exception(f"应用程序启动失败: {e}")
        input("按回车键退出...")
        return 1


if __name__ == "__main__":
    sys.exit(main())
