# Python 3.8 & 3.12 Compatibility Changes

## Overview

This document outlines all changes made to ensure the unit tests are compatible with both Python 3.8 and Python 3.12.

## Changes Made

### 1. Added `from __future__ import annotations`

Added to all Python source files to ensure consistent type hint behavior across Python versions.

**Files Updated:**

- `src/lib/nip47.py`
- `src/lib/event.py`
- `src/lib/utils.py`
- `src/lib/nip04.py`
- `tests/test_nwc_units.py`

**Why:** This import enables postponed evaluation of type hints (PEP 563), which allows using modern type hint syntax in older Python versions. It's especially important for forward references and union types.

### 2. Fixed Type Hints in `src/lib/nip47.py`

**URIOptions Dataclass:**

```python
# Before (Python 3.10+ compatible, but not 3.8)
relay_url: str = None
secret: str = None
wallet_pubkey: str = None
nostr_wallet_connect_url: str = None
expiry_unix: int = None
budget_msat: Millisatoshi = None
spent_msat: Millisatoshi = None

# After (Python 3.8+ compatible)
relay_url: Optional[str] = None
secret: Optional[str] = None
wallet_pubkey: Optional[str] = None
nostr_wallet_connect_url: Optional[str] = None
expiry_unix: Optional[int] = None
budget_msat: Optional[Millisatoshi] = None
spent_msat: Optional[Millisatoshi] = None
```

**Added Import:**

```python
from typing import List, Optional
```

**Why:** Python 3.8 requires explicit `Optional` type hints for values that may be `None`. Modern Python versions (3.10+) support the `Type | None` syntax, but `Optional[Type]` works across all versions.

### 3. Enhanced Type Hints in `src/lib/event.py`

**Added `Optional` import and improved type annotations:**

- Event.**init**() method parameters now have proper Optional type hints:

```python
def __init__(
    self,
    id: Optional[str] = None,
    sig: Optional[str] = None,
    kind: Optional[int] = None,
    content: Optional[str] = None,
    tags: Optional[list] = None,
    pubkey: Optional[str] = None,
    created_at: Optional[int] = None,
):
```

- EventTags.get_tag_value_pos() return type fixed:

```python
def get_tag_value_pos(
    self, tag_name: str, pos: int = 0, default: Optional[str] = None
) -> Optional[str]:
```

## Testing

All changes have been validated to work with both Python 3.8 and Python 3.12+.

**Run tests:**

```bash
# Python 3.8
python3.8 -m pytest tests/test_nwc_units.py -v

# Python 3.12+
python3.12 -m pytest tests/test_nwc_units.py -v
```

## Summary

These compatibility changes ensure the NWC plugin works seamlessly across:

- Python 3.8 (commonly used in stable deployments)
- Python 3.12+ (modern development environments)

The changes enable forward compatibility while maintaining backward compatibility with older Python versions. No functional changes were made—only type hint syntax was modernized.

## Migration Guide

If you're working with this code:

1. Always use `Optional[Type]` instead of `Type | None`
2. Include `from __future__ import annotations` in new modules
3. Run tests with multiple Python versions before deployment
4. Check that your type checking tool (mypy, pylance) is configured for Python 3.8+

### 4. Created `pyproject.toml`

Added a modern Python package configuration file with:

- Python requirement: `requires-python = ">=3.8,<4"`
- Explicit dependency specification
- Pytest configuration for compatibility

**Key Configuration:**

```toml
requires-python = ">=3.8,<4"
asyncio_mode = "auto"
minversion = "7.0" (pytest)
```

## Python Version Compatibility Matrix

### Features Working in Both Versions:

- ✅ Type hints with `Optional[Type]`
- ✅ Dataclasses
- ✅ `from __future__ import annotations`
- ✅ Standard library imports
- ✅ String formatting
- ✅ Async/await syntax
- ✅ F-strings

### Features NOT Used (for compatibility):

- ❌ Union types using `|` (Python 3.10+ only)
- ❌ Match statements (Python 3.10+ only)
- ❌ Type hints using lowercase built-ins like `list[str]` (Python 3.9+ only)
- ❌ Parenthesized context managers (Python 3.10+ only)

## Testing Recommendations

### Manual Testing Steps:

1. **Python 3.8 Testing:**

   ```bash
   # Create virtual environment with Python 3.8
   python3.8 -m venv .venv38
   source .venv38/bin/activate
   pip install -r requirements.txt
   pip install -e .
   pytest tests/
   ```

2. **Python 3.12 Testing:**

   ```bash
   # Create virtual environment with Python 3.12
   python3.12 -m venv .venv312
   source .venv312/bin/activate
   pip install -r requirements.txt
   pip install -e .
   pytest tests/
   ```

3. **Syntax Validation:**
   ```bash
   python -m py_compile src/lib/*.py tests/*.py
   ```

### Continuous Integration (CI) Recommendation:

Set up GitHub Actions or similar CI pipeline to test against both Python versions:

```yaml
python-version: ["3.8", "3.9", "3.10", "3.11", "3.12"]
```

## Breaking Changes

None. All changes are backward compatible with Python 3.8 and forward compatible with Python 3.12+.

## Migration Guide for Future Python Versions

When dropping Python 3.8 support (if desired), you can:

1. **Remove `from __future__ import annotations`** - no longer needed as type hints will be evaluated at runtime
2. **Use modern Union syntax:**
   ```python
   # Instead of Optional[str]
   str | None
   ```
3. **Use lowercase built-in types in hints:**
   ```python
   # Instead of from typing import List
   list[str]  # Only in Python 3.9+
   dict[str, int]  # Only in Python 3.9+
   ```

## Summary

The unit tests are now fully compatible with both Python 3.8 and Python 3.12+. All changes follow PEP 8 standards and maintain backward compatibility while supporting modern Python features.
