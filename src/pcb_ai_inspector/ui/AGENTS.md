# UI Components

**Parent:** `./AGENTS.md`

## OVERVIEW

PyQt6 GUI layer for PCB defect detection application. Modular architecture with separate panels for different detection modes.

## WHERE TO LOOK

| Task | File | Description |
|------|------|-------------|
| Main window | `main_window.py` | App shell, menus, toolbar, status bar |
| Manual detection | `manual_panel.py` | Image viewers, settings, results table |
| Realtime detection | `realtime_panel.py` | Camera preview, live detection |
| Batch processing | `batch_handler.py` | Batch detection controller (non-QWidget) |
| Detection flow | `detection_pipeline.py` | Threaded detection worker |
| Image display | `image_viewer.py` | Zoomable/pannable image viewer |
| Defect overlay | `defect_overlay.py` | Bounding box rendering |
| Defect list | `defect_list.py` | Sortable/filterable results table |
| Settings dialog | `settings_dialog.py` | Configuration UI |
| Report preview | `report_preview_dialog.py` | PDF/Excel preview |

## MODULE ARCHITECTURE

```
MainWindow (QMainWindow)
├── MenuBar (File, Detection, Help)
├── Toolbar (Open, Detect, Cancel)
├── QTabWidget
│   ├── ManualDetectionPanel (QWidget)
│   │   ├── ImageViewer (original image)
│   │   ├── DetectionOverlay (marked image)
│   │   ├── StatisticsWidget
│   │   ├── DefectListWidget
│   │   └── QTableWidget (results table)
│   └── RealtimeDetectionPanel (QWidget)
│       ├── QLabel (camera preview)
│       ├── DefectListWidget
│       └── Camera controls
├── StatusBar + ProgressBar
└── BatchDetectionHandler (controller, non-GUI)
```

## SIGNAL COMMUNICATION

Child panels emit signals → MainWindow handles:

```python
# ManualDetectionPanel signals
image_selected = pyqtSignal(str, list, object)  # path, detections, marked_image
zoom_changed = pyqtSignal(float)
detect_requested = pyqtSignal()

# RealtimeDetectionPanel signals
detection_completed = pyqtSignal(list)  # DetectionResult list
capture_requested = pyqtSignal(object)  # np.ndarray frame
save_requested = pyqtSignal(object)

# BatchDetectionHandler signals (via .signals)
progress_updated = pyqtSignal(int, int, str)
task_completed = pyqtSignal(str, list, object, object)
batch_completed = pyqtSignal(object)
```

## CONVENTIONS

- PyQt6 signals/slots for event handling
- QMainWindow subclass for main app
- QDialog subclasses for modal dialogs
- QWidget subclasses for panels (use signals for parent communication)
- Plain Python classes for controllers (no QWidget inheritance)
- Resource paths via `PyQt6.QtCore.QResource`

## PATTERNS

### Creating a new panel
```python
class MyPanel(QWidget):
    # Define signals for parent communication
    my_signal = pyqtSignal(...)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self) -> None:
        # Build UI with layouts and widgets
    
    def _setup_connections(self) -> None:
        # Connect internal signals/slots
```

### Setting detector reference
```python
class MyPanel(QWidget):
    def set_detector(self, detector: Optional[YOLODetector]) -> None:
        self._detector = detector
```

## NOTES

- UI runs in main thread; detection in worker thread
- Image loading via PIL → QPixmap conversion
- Overlaypainting for defect visualization
- Panels are instantiated in MainWindow and wired via signals
- BatchDetectionHandler is a plain controller class (no GUI)
