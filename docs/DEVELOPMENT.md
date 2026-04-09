# PCB AI Inspector - 开发环境设置

## 环境要求

- Python 3.11.9 (通过 Anaconda)
- Windows 10/11 64位
- 推荐 8GB+ RAM
- 可选: NVIDIA GTX 1650+ (GPU 加速)

## 快速开始

### 1. 创建 Conda 环境

```bash
conda create -n pcb-ai python=3.11.9 -y
conda activate pcb-ai
```

### 2. 安装依赖

**仅生产依赖:**
```bash
pip install -r requirements.txt
```

**包含开发依赖:**
```bash
pip install -e ".[dev]"
```

### 3. 验证安装

```bash
python -c "import ultralytics; import PyQt6; print('OK')"
```

## 开发工具

### 代码格式化

```bash
# 格式化所有代码
make format

# 或手动执行
black src/pcb_ai_inspector
isort src/pcb_ai_inspector
```

### 代码检查

```bash
# 运行所有检查
make lint

# 或单独执行
flake8 src/pcb_ai_inspector
mypy src/pcb_ai_inspector
```

### 运行测试

```bash
make test        # 运行测试
make test-cov    # 运行测试并生成覆盖率报告
```

### Pre-commit Hooks (可选)

```bash
# 安装 pre-commit
pip install pre-commit

# 安装 git hooks
pre-commit install

# 手动运行
pre-commit run --all-files
```

## 项目结构

```
pcb-ai-inspector/
├── src/
│   └── pcb_ai_inspector/
│       ├── core/              # 核心模块
│       │   ├── defect_types.py    # 缺陷类型定义
│       │   ├── activation.py      # 激活系统
│       │   ├── history.py         # 检测历史记录
│       │   └── settings.py        # 设置管理
│       ├── models/            # AI 模型相关
│       │   └── detector.py        # YOLO 检测器
│       ├── reports/           # 报告生成
│       │   └── report_generator.py
│       ├── ui/               # UI 组件
│       │   ├── main_window.py     # 主窗口
│       │   ├── image_viewer.py   # 图像查看器
│       │   ├── defect_overlay.py  # 缺陷标注
│       │   ├── defect_list.py     # 缺陷列表
│       │   ├── detection_pipeline.py  # 检测流程
│       │   ├── detection_result_handler.py  # 结果处理
│       │   ├── report_preview_dialog.py  # 报告预览
│       │   ├── settings_dialog.py # 设置对话框
│       │   └── history_dialog.py  # 历史对话框
│       ├── utils/            # 工具函数
│       │   ├── device.py         # 设备检测
│       │   └── logging_config.py  # 日志配置
│       └── tests/            # 测试代码
│           └── test_device.py     # 设备测试
├── docs/                    # 文档
├── logs/                    # 日志文件
├── .vscode/                 # VSCode 配置
├── requirements.txt         # 依赖清单
├── pyproject.toml          # 项目配置
└── Makefile               # 开发命令
```

## 核心模块说明

### 激活系统 (core/activation.py)

离线授权系统，支持硬件绑定和授权码验证。

```python
from pcb_ai_inspector.core.activation import ActivationManager, check_activation

# 检查激活状态
info = check_activation()
print(f"状态: {info.state}, 消息: {info.message}")

# 激活软件
manager = ActivationManager()
success, message = manager.activate("XXXX-XXXX-XXXX-XXXX")
```

### 历史记录 (core/history.py)

SQLite 数据库存储检测历史，支持搜索和统计。

```python
from pcb_ai_inspector.core.history import get_history_manager

manager = get_history_manager()

# 添加检测记录
manager.add_detection(
    image_path="/path/to/image.png",
    defects=detections,
    processing_time_ms=150.0,
    device="CUDA",
)

# 获取统计
stats = manager.get_statistics()
print(f"总检测: {stats.total_detections}")
```

### 设置管理 (core/settings.py)

持久化存储用户配置。

```python
from pcb_ai_inspector.core.settings import get_settings_manager

manager = get_settings_manager()

# 获取设置
threshold = manager.get("detection.confidence_threshold")

# 保存设置
manager.set("display.show_boxes", False)
manager.save()
```

### 日志系统 (utils/logging_config.py)

集中式日志配置，支持文件轮转和控制台输出。

```python
from pcb_ai_inspector.utils.logging_config import get_logger

logger = get_logger(__name__)
logger.info("日志消息")
```

## 常用命令

| 命令 | 说明 |
|------|------|
| `make install` | 安装生产依赖 |
| `make dev` | 安装开发依赖 |
| `make test` | 运行测试 |
| `make lint` | 运行代码检查 |
| `make format` | 格式化代码 |
| `make clean` | 清理构建产物 |
| `make run` | 运行应用 |

## 代码规范

### 命名规范

- 类名: `PascalCase` (如 `MainWindow`)
- 函数/方法: `snake_case` (如 `get_defect_info`)
- 常量: `UPPER_SNAKE_CASE` (如 `MAX_IMAGE_SIZE`)
- 私有成员: `_prefixed_with_underscore`

### 类型注解

- 所有函数必须包含类型注解
- 公共 API 必须有完整的类型签名
- 使用 `from __future__ import annotations` 允许前向引用

### 文档字符串

- 所有公共类/函数必须有 docstring
- 使用 Google 风格的 docstring

```python
def get_defect_info(defect_type: DefectType) -> DefectDefinition:
    """获取缺陷类型的量化定义。
    
    Args:
        defect_type: 缺陷类型枚举
        
    Returns:
        缺陷的量化定义对象
        
    Raises:
        ValueError: 当缺陷类型无效时
    """
    ...
```

## 提交代码

1. 确保 `make lint` 和 `make test` 通过
2. 使用清晰的 commit message
3. 创建 pull request 请求合并

## 故障排除

### 导入错误

确保在项目根目录执行命令，或设置 `PYTHONPATH`:

```bash
export PYTHONPATH="${PWD}/src:$PYTHONPATH"  # Linux/Mac
set PYTHONPATH=%CD%\src;%PYTHONPATH%        # Windows
```

### PyTorch CUDA 问题

如果 GPU 不可用，安装 CPU 版本:

```bash
pip uninstall torch
pip install torch --index-url https://download.pytorch.org/whl/cpu
```
