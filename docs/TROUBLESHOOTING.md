# 常见问题

## 环境问题

### CUDA/GPU 相关

**Q: 如何在没有GPU的电脑上运行？**
A: 系统会自动检测，无GPU时会切换到CPU模式运行。也可手动安装CPU版PyTorch：
```bash
pip uninstall torch
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

**Q: GPU检测速度慢怎么办？**
A: 确保使用ONNX模型（推荐），或安装CUDA版本的PyTorch。检查是否后台有其他程序占用GPU。

### 依赖安装

**Q: 安装依赖失败？**
A: 建议使用Anaconda创建独立环境：
```bash
conda create -n pcb-ai python=3.11.9 -y
conda activate pcb-ai
pip install -r requirements.txt
```

**Q: import 报错 ModuleNotFoundError？**
A: 确保在项目根目录运行，或设置PYTHONPATH：
```bash
set PYTHONPATH=%CD%\src;%PYTHONPATH%
```

## 模型问题

**Q: 模型文件在哪里？**
A: 首次运行时会自动下载，也可手动放置到 `models/` 目录。支持 .pt (PyTorch) 和 .onnx 格式。

**Q: 如何使用自己训练的模型？**
A: 将模型文件重命名为 `best.pt` 或 `best.onnx` 放入 `models/` 目录即可。

**Q: 检测精度不够高？**
A: 调整置信度阈值（设置中降低到0.15-0.2），或使用更高精度的模型。

## 相机问题

**Q: USB相机无法连接？**
A: 检查相机是否被其他程序占用，更改相机ID（尝试1,2,...），或使用相机工具扫描。

**Q: 工业相机连接失败？**
A: 确保相机和电脑在同一网络，检查IP地址设置，查看相机品牌是否在支持列表中。

**Q: 预览画面卡顿？**
A: 降低显示帧率（设置中调低FPS），或使用较低的相机分辨率。

## 功能问题

**Q: 报告导出失败？**
A: 检查是否有写入权限，确保磁盘空间充足，关闭已打开的Excel/PDF文件。

**Q: 历史记录无法查看？**
A: 首次使用无历史记录，正常现象。检查SQLite文件是否损坏。

## 打包问题

**Q: 打包后运行报错？**
A: 确保所有依赖都在 pyproject.toml 中，使用 make build 或手动运行 pyinstaller。

**Q: exe文件太大？**
A: 使用虚拟环境隔离依赖，考虑分拆为可选模块。

---

更多问题请提交 [GitHub Issues](https://github.com/your-repo/issues)
