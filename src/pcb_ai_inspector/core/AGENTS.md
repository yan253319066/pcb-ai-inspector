# Core Domain Models

**Parent:** `./AGENTS.md`

## OVERVIEW

Domain models and core business logic for PCB defect types, settings, and history.

## WHERE TO LOOK

| Task | File |
|------|------|
| Defect types enum | `defect_types.py` |
| Settings management | `settings.py` |
| Detection history | `history.py` |
| Activation logic | `activation.py` |

## CONVENTIONS

- Use Enum for fixed types (not dict/map)
- Pydantic for settings validation
- TYPE_CHECKING guard for type hints with heavy imports

## ANTI-PATTERNS

- ❌ Map/dict for defect types → use `DefectType` Enum
- ❌ Hardcoded paths → use `settings.py`

## NOTES

- `get_defect_info()` returns localized defect details
- Settings persisted via pydantic + JSON