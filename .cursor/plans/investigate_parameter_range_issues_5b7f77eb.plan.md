---
name: Investigate Parameter Range Issues
overview: Create a diagnostic script to investigate why AbletonOSC returns incorrect parameter ranges (0-1) for some parameters but correct ranges for others, then implement a fix based on findings.
todos: []
---

# Investigate and Fix Parameter Range Issues

## Root Cause Investigation

The test shows **inconsistent behavior**:

- ✅ Some params get correct ranges: Saturator Drive (-36 to 36), EQ Gain (-15 to 15)
- ❌ Some params get 0-1 range: EQ Frequency (should be ~20-20000 Hz), Compressor Threshold
- ❌ Some params with correct ranges fail to set: Saturator Output, Glue Threshold (send 0.9, read back 0.0)

## Step 1: Create Diagnostic Script

Create `tests/diagnose_parameter_ranges.py` to:

```python
# Compare OSC-reported ranges vs device_kb.py expected ranges
# Test actual parameter behavior:
#   - Send normalized value (0.5)
#   - Read back and check if it's normalized or denormalized
#   - Try sending denormalized value directly
#   - Determine which approach works for each parameter type
```

**Key diagnostics**:

1. Query min/max from OSC with cache cleared
2. Compare against `knowledge/device_kb.py` expected ranges
3. For each problematic parameter:

   - Set to 0.25 normalized, read back → is it 0.25 or denormalized?
   - Set to actual Hz/dB value, read back → does it work?

4. Identify patterns (e.g., all frequency params have 0-1 range?)

## Step 2: Implement Fix Based on Findings

### Option A: If OSC returns wrong ranges

Update [`ableton_controls/reliable_params.py`](ableton_controls/reliable_params.py) `get_parameter_range()`:

- Check if range is suspiciously 0-1 for non-percentage parameters
- Fall back to `device_kb.py` for known devices/parameters
- Log warnings when OSC ranges look incorrect

### Option B: If parameters expect denormalized values

Some parameters might expect **already-denormalized** values despite OSC convention:

- Detect these parameters (test by sending/reading)
- Skip normalization for them
- Send human values directly

### Option C: If it's an AbletonOSC bug

Parameters might need a **different OSC path** for range queries:

- Try `/live/device/get/parameter/min` (singular) per-parameter
- Try querying device class/type to determine ranges
- Check AbletonOSC version/documentation

## Step 3: Fix the Auto-Percentage Conversion

In [`ableton_controls/reliable_params.py`](ableton_controls/reliable_params.py) line ~580:

**Current problematic logic**:

```python
# This incorrectly treats 100 Hz as 100%
if is_normalized_param and value > 1.0 and value <= 100.0:
    target_value = value / 100.0
```

**Needs intelligence**:

- Don't auto-convert if parameter name contains "Frequency", "Hz", "Time", "ms"
- Don't auto-convert if value >> 100 (e.g., 300 Hz, 150 ms)
- Only auto-convert for actual percentage params (0-100 range expected)

## Step 4: Fix Parameters That Reject Normalized Values

For parameters where `sent 0.916667, read 0.000000`:

- These might be **output-only** or have **discrete steps**
- Or require denormalized input despite having real ranges
- Detect failed sets and retry with denormalized value

## Expected Outcome

After investigation and fixes:

- **Diagnostic script** reveals why ranges are wrong
- **Fix targets the root cause** (wrong ranges, wrong send format, or both)
- **Success rate jumps to 85%+** (accounting for legitimate failures like boolean toggles)
- **Parameters work consistently** across all devices

## Files to Create/Modify

1. **Create**: `tests/diagnose_parameter_ranges.py` - Investigation script
2. **Modify**: [`ableton_controls/reliable_params.py`](ableton_controls/reliable_params.py):

   - `get_parameter_range()` - Add fallback to device_kb
   - `set_parameter_verified()` - Fix auto-percentage logic
   - `normalize_value()` - Add parameter-type detection

3. **Reference**: [`knowledge/device_kb.py`](knowledge/device_kb.py) - Use as source of truth for ranges

## Success Criteria

- Diagnostic script identifies root cause
- Fix addresses the actual problem (not workarounds)
- Test success rate ≥ 80% (excluding legitimate edge cases)
- Parameters set to correct human values (100 Hz = 100 Hz, not 1.0)