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
