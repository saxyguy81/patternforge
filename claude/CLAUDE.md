### Quick Test Commands

```bash
# Run all tests (queued)
pytest tests/ -q

# Run specific test file
pytest tests/test_exact_mode.py -v

# Run specific test
pytest tests/test_exact_mode.py::test_exact_mode_simple_paths -v

# Run with short traceback
pytest tests/ -v --tb=short
```

## Architecture

### Tokenization (`splitmethod`)

Two tokenization methods:

1. **`splitmethod='classchange'`** (DEFAULT, RECOMMENDED)
   - Splits on character class changes (alpha → digit → other)
   - Example: `SRAMController_512x64` → `[sram, controller, 512, x, 64]`
   - Best for CamelCase, mixed alphanumeric identifiers

2. **`splitmethod='char'`** (ADVANCED)
   - Splits into individual characters
   - Example: `chip/cpu` → `[c, h, i, p, /, c, p, u]`
   - Automatically uses `min_token_len=1` (ignores global setting)
   - Use for character-level pattern discovery

### EXACT Mode

`mode="EXACT"` guarantees zero false positives (`metrics['fp'] == 0`).

**Implementation**:
- Automatically sets `max_fp=0` in `solver.py:762-776`
- Validates inverted solutions don't violate FP constraint (lines 790, 807)
- May return empty solutions (coverage=0) rather than violate FP guarantee

**Bug fixed** (commit b13994a): Previously, inverted solutions could violate FP constraint.

## Recent Changes

### 2025-01-06: Fixed Critical EXACT Mode Bug
- **Problem**: EXACT mode was producing false positives
- **Cause**: Inverted solutions returned without checking max_fp constraint
- **Fix**: Added FP validation before returning inverted solutions
- **Files**: `src/patternforge/engine/solver.py`, `tests/test_exact_mode.py`

### 2025-01-06: Fixed splitmethod='char' Tokenization
- **Problem**: `splitmethod='char'` treated entire string as one token instead of splitting into characters
- **Cause**: Bug in `tokens.py:40` - `raw_tokens = [text]` instead of `list(text)`
- **Fix**: Split into individual characters, auto-set `min_token_len=1`
- **Files**: `src/patternforge/engine/tokens.py`, `tests/test_splitmethod_char.py`, `USER_GUIDE.md`
