# 模型训练指南

本文档介绍如何训练自己的PCB缺陷检测模型，适用于毕设、比赛或自定义需求。

## 环境准备

```bash
cd pcb_model
pip install -e ".[dev]"
```

## 数据集准备

### 1. 数据格式

支持两种格式：
- **YOLO格式**：images/train, images/val, labels/train, labels/val
- **VOC格式**：JPEGImages, Annotations (需转换)

### 2. 缺陷类别

默认支持10种缺陷类型（见 `utils/constants.py`）：
```
0: short_circuit (短路)
1: open_circuit (开路)
2: missing_hole (缺孔)
3: spur (毛刺)
4: mousebite (鼠咬)
5: spurious_copper (多余铜皮)
6: hole_breakout (孔 breakout)
7: conductor_scratch (导体划痕)
8: foreign_object (异物)
9: pin_hole (针孔)
```

### 3. 数据增强建议

- 翻转、旋转（水平翻转即可，PCB不建议垂直翻转）
- 颜色抖动、光照变化
- Mosaic、MixUp等YOLO内置增强

## 训练模型

### 方式一：训练基底模型

```bash
# 使用VOC格式数据集
python scripts/convert_to_yolo.py --data ../pcb_data --output data/

# 开始训练
python scripts/train_base_model.py --data data/merged --epochs 200 --batch 16 --device cuda
```

### 方式二：微调现有模型

```bash
# 基于预训练模型微调
python scripts/finetune_model.py --model ../pcb-ai-inspector/models/best.pt --data data/merged --epochs 50
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| --data | 数据集目录 | 必需 |
| --epochs | 训练轮次 | 200 |
| --batch | 批次大小 | 16 |
| --model | 模型大小 (n/s/m/l/x) | s |
| --device | 设备 (cuda/cpu) | cuda |
| --imgsz | 输入图像尺寸 | 1280 |

## 模型导出

训练完成后，导出为ONNX格式以提高推理速度：

```bash
python scripts/export_onnx.py --model runs/train/base_model/weights/best.pt --output models/
```

## 替换模型

将导出的模型文件放入 `pcb-ai-inspector/models/` 目录：
- `best.pt` - PyTorch模型
- `best.onnx` - ONNX模型（推荐）

## 常见问题

**Q: 训练时显存不足？**
A: 减小batch_size，或使用更小的模型尺寸（--model n）

**Q: 精度不够高？**
A: 增加epochs，使用更大的图像尺寸（--imgsz 1280），或使用m/l/x模型

**Q: 如何添加新的缺陷类型？**
A: 修改 `utils/constants.py` 中的 CLASS_NAMES，重新训练模型

**Q: 可以在CPU上训练吗？**
A: 可以，但速度非常慢。建议使用GPU，或使用Google Colab免费GPU。

## 进阶

- 使用 `merge_datasets.py` 合并多个数据集
- 使用 `data_cleaner.py` 清洗数据
- 使用 `compare_results.py` 对比不同模型效果
