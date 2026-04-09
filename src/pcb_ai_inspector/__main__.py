"""
PCB AI Inspector - 主入口点

本模块提供 PCB 缺陷检测软件的主应用程序入口点。
"""

from __future__ import annotations

import sys
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

    # 移除默认处理器，避免重复输出
    logger.remove()

    logger.add(
        log_dir / "app_{time}.log",
        rotation="10 MB",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    # 同时输出到控制台
    logger.add(
        sys.stdout,
        level="INFO",
        format="{time:HH:mm:ss} | {level} | {message}",
    )


def check_license() -> bool:
    """检查软件授权状态。

    返回:
        已激活或处于评估模式时返回 True
    """
    try:
        from pcb_ai_inspector.core.activation import check_activation

        info = check_activation()

        if info.state == "activated":
            logger.info("许可证: 已激活")
            return True
        elif info.state == "evaluation":
            logger.info(f"许可证: 评估版 ({info.message})")
            return True
        else:
            logger.warning(f"许可证: {info.message}")
            return True  # 允许在未授权模式下运行用于演示

    except Exception as e:
        logger.warning(f"许可证检查失败: {e}")
        return True  # 如果激活模块失败，允许运行


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
        # 检查许可证
        if not check_license():
            logger.error("许可证检查失败")
            return 1

        # 避免循环导入，在此处导入
        from pcb_ai_inspector.ui.main_window import MainWindow
        from PyQt6.QtWidgets import QApplication

        app = QApplication(sys.argv)
        app.setApplicationName("PCB AI Inspector")
        app.setOrganizationName("PCB-AI")
        app.setApplicationVersion("1.0.0")

        window = MainWindow()
        window.show()

        logger.info("应用程序窗口已显示")
        return app.exec()

    except Exception as e:
        logger.exception(f"应用程序启动失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
