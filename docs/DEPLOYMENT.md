# 打包发布指南

本文档介绍如何将PCB AI Inspector打包为可执行文件进行分发。

## 环境要求

- Python 3.11.9
- Windows 10/11 64位
- 至少8GB内存

## 安装打包工具

```bash
pip install pyinstaller
```

## 打包命令

### 方式一：使用 Makefile

```bash
cd pcb-ai-inspector
make build
```

### 方式二：手动执行

```bash
pyinstaller pcb-ai-inspector.spec
```

## 输出文件

打包完成后，可执行文件位于：
- `dist/pcb-ai-inspector/pcb-ai-inspector.exe`

## 打包配置说明

关键配置文件 `pcb-ai-inspector.spec`：

```python
a = Analysis(
    ['src/pcb_ai_inspector/__main__.py'],
    pathex=[],
    binaries=[],          # 包含模型文件
    datas=[
        ('models', 'models'),    # 模型目录
        ('resources', 'resources'),  # 资源文件
    ],
    hiddenimports=[
        'cv2',
        'torch',
        'onnxruntime',
        'PIL',
        'PyQt6',
    ],
    ...
)
```

## 注意事项

### 模型文件

确保 `models/` 目录包含以下文件：
- `best.pt` 或 `best.onnx` - 检测模型

### 依赖精简

如需减小体积：
1. 使用ONNX模型替代PyTorch
2. 只包含必要的CUDA库
3. 使用虚拟环境隔离

### 图标设置

替换 `resources/icon.ico` 可自定义应用图标。

### 首次运行

首次运行exe时，会自动解压临时文件，请耐心等待。

## 分发方式

1. **直接分发**：打包整个 `dist/pcb-ai-inspector` 文件夹
2. **单exe打包**：使用 onefile 模式（文件更大但只需一个exe）
3. **安装包**：使用 NSIS 或 Inno Setup 创建安装程序

## 常见问题

**Q: 打包后运行无反应？**
A: 检查是否缺少DLL依赖，使用Dependency Walker查看缺少的库。

**Q: 模型加载失败？**
A: 确保模型文件在datas中正确配置，检查相对路径。

**Q: 杀毒软件误报？**
A: 正常现象，可提交误报或添加数字签名。

**Q: exe文件太大？**
A: 正常现象，PyInstaller打包Python应用通常较大（200MB+）。可考虑分卷压缩分发。
