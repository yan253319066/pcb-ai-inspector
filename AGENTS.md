# AGENTS.md - PCB AI Inspector

**Project:** PCB Defect AI Detection (YOLOv11 + PyQt6)  
**Python:** 3.11 | **License:** AGPL-3.0

---

## Build / Lint / Test Commands

```bash
# Development setup
cd pcb-ai-inspector
pip install -e ".[dev]"

# Run all tests
make test
# Or: pytest src/pcb_ai_inspector/tests -v

# Run single test
pytest src/pcb_ai_inspector/tests/test_file.py::TestClass::test_method -v

# Run tests with coverage
make test-cov
# Or: pytest --cov=pcb_ai_inspector --cov-report=html

# Format code
make format
# Or: black src/pcb_ai_inspector && isort src/pcb_ai_inspector

# Lint + Type check
make lint
# Or: flake8 src/pcb_ai_inspector && mypy src/pcb_ai_inspector

# Type check only
make typecheck

# Run application
make run
# Or: python -m pcb_ai_inspector
```

---

## Code Style Guidelines

### Formatting
- **Line length:** 100 characters (black, flake8)
- **Formatter:** black + isort
- **Indentation:** 4 spaces
- **Trailing commas:** preferred for multi-line imports

### Imports (isort)
```python
# Standard library
from pathlib import Path
import json

# Third party
import pytest
from PyQt6.QtWidgets import QWidget

# Local application
from pcb_ai_inspector.core import DefectType
from pcb_ai_inspector.models import YOLODetector
```
- Use `TYPE_CHECKING` guard for heavy imports (torch, cv2) in type hints:
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import torch
    import cv2
```

### Type Hints
- **Strict mode:** mypy enabled with `disallow_untyped_defs = true`
- Use explicit types for all function parameters and return values
- Use `Optional[X]` instead of `X | None` for compatibility

### Naming Conventions
- **Classes:** PascalCase (`class ManualPanel`)
- **Functions/methods:** snake_case (`def get_defect_info`)
- **Constants:** UPPER_SNAKE_CASE (`MAX_IMAGE_SIZE`)
- **Private methods:** prefix with `_` (`def _setup_ui`)
- **UI panels:** suffix with `Panel`, `Dialog`, `Widget`

### Error Handling
- Use `loguru` for logging: `logger.warning()`, `logger.error()`
- Raise specific exceptions with clear messages
- Never silently swallow exceptions in production code

---

## Project Structure

```
pcb-ai-inspector/
├── src/pcb_ai_inspector/
│   ├── core/          # Domain models (defect_types, settings, history)
│   ├── models/        # AI detector (YOLO + ONNX)
│   ├── ui/            # PyQt6 GUI components
│   ├── reports/       # PDF/Excel report generation
│   ├── utils/         # Device detection, logging
│   └── tests/         # pytest suite
├── configs/           # App configurations
├── pyproject.toml    # Project metadata + tool config
└── Makefile          # Dev commands
```

---

## Key Patterns

### Defect Types (use Enum, not dict)
```python
from enum import Enum

class DefectType(Enum):
    MISSING_HOLE = "missing_hole"
    SPUR = "spur"
    SHORT = "short"

def get_defect_info(defect_type: DefectType) -> dict: ...
```

### UI Panel (signal-based communication)
```python
class MyPanel(QWidget):
    my_signal = pyqtSignal(str, list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        # ... widgets
```

### Type hints for heavy imports
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import torch
    import cv2

class Detector:
    def predict(self, image: "cv2.Mat") -> list["DetectionResult"]: ...
```

---

## Anti-Patterns (DO NOT DO)

- ❌ Direct `torch`/`cv2` imports in type hints → use `TYPE_CHECKING`
- ❌ Hardcoded paths → use `settings.py` or config files
- ❌ Map/dict for fixed types → use Enums from `defect_types.py`
- ❌ Panels accessing MainWindow internals directly → use signals
- ❌ Conda activate in Makefile separate lines → use `conda run`
- ❌ License check returns True on failure → security bypass

---

## UI Module Architecture

```
MainWindow (QMainWindow)
├── MenuBar / Toolbar / StatusBar
├── QTabWidget
│   ├── ManualDetectionPanel    # Image detection
│   └── RealtimeDetectionPanel  # Camera detection
└── BatchDetectionHandler       # Batch controller (non-GUI)
```

**Communication:** Child panels emit pyqtSignals → MainWindow handles.

---

## Notes

- GPU detection: `torch.cuda.is_available()` + `onnxruntime.get_available_providers()`
- Tests: pytest with pytest-cov
- Package layout: src/ layout (PEP 517)
- Controllers: Plain Python classes (no QWidget inheritance)