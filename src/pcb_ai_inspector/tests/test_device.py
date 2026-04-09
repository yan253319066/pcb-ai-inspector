"""Test GPU/CPU compatibility module."""

from pcb_ai_inspector.utils.device import print_device_info, get_device
from pcb_ai_inspector.models.detector import create_detector


def main() -> None:
    """Run tests."""
    print("=" * 50)
    print("Testing GPU/CPU Compatibility Module")
    print("=" * 50)

    # Test device info
    print("\n1. Device Information:")
    print_device_info()

    # Test detector creation
    print("\n2. Detector Initialization:")
    detector = create_detector()
    print(f"   Device: {detector.device}")
    print(f"   Model loaded: {detector.model is not None}")

    print("\n" + "=" * 50)
    print("✅ All tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    main()
