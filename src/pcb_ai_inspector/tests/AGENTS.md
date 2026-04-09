# Test Suite

**Parent:** `./AGENTS.md`

## OVERVIEW

pytest test suite for the application including unit tests and mock UI tests.

## WHERE TO LOOK

| Task | File | Description |
|------|------|-------------|
| Device tests | `test_device.py` | GPU/CPU detection tests |
| Unit core tests | `test_unit_core.py` | Core module tests |
| Preprocessor tests | `test_preprocessor.py` | Image preprocessing tests |
| Preprocessor logic | `test_preprocessor_logic.py` | Preprocessing logic unit tests |
| Exception injection | `test_exception_injection.py` | Error handling tests |
| UI mock tests | `test_ui_mock.py` | UI component mock tests |

## CONVENTIONS

- pytest with pytest-cov
- Test files: `test_*.py` or `*_test.py`
- Test classes: `Test*`
- Test functions: `test_*`
- Use mocking for UI tests to avoid Qt dependency

## COMMANDS

```bash
make test    # pytest with coverage
```

## NOTES

- UI tests use mocked Qt components
- Mock UI tests in `test_ui_mock.py` verify panel signals and interactions
- Core logic tests don't require Qt runtime
