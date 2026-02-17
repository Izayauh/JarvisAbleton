# Parameter Normalization Guide

## Overview

This guide documents the parameter normalization system in JarvisAbleton, lessons learned from debugging, and best practices for adding new device support.

---

## How Parameter Normalization Works

### The Challenge

Ableton Live's OSC API expects all parameter values in a **normalized range [0.0, 1.0]**, but users and presets work with **human-readable values** (e.g., "500 Hz", "75 ms", "3 dB", "100%"). The normalization system bridges this gap.

### The Solution: `smart_normalize_parameter()`

Located in `ableton_controls/reliable_params.py`, this function intelligently converts human values to normalized values based on:
1. **Parameter name** (e.g., "Frequency", "Attack", "Threshold")
2. **Device name** (e.g., "Compressor", "EQ Eight", "Reverb")
3. **Parameter range** (min/max from Ableton)

### Conversion Flow

```
User Input (e.g., "75 ms")
    ↓
Auto-percentage check (lines 1095-1120)
    ↓
smart_normalize_parameter() (lines 220-338)
    ↓
Specific handler (e.g., release_log, freq_log)
    ↓
Normalized value (0.0 - 1.0)
    ↓
Ableton OSC API
```

---

## Common Normalization Methods

| Method | Use Case | Formula | Example |
|--------|----------|---------|---------|
| `freq_log` | Frequency (20-20000 Hz) | Logarithmic | 500 Hz → 0.44 |
| `threshold_lut` | Compressor threshold | Lookup table | -19 dB → 0.43 |
| `ratio_lut` | Compressor ratio | Lookup table | 4:1 → 0.75 |
| `attack_log` | Attack time (ms) | Logarithmic | 7 ms → 0.58 |
| `release_log` | Release time (ms) | Logarithmic | 75 ms → 0.22 |
| `decay_log` | Reverb decay (ms/s) | Logarithmic | 2.4s → 0.44 |
| `percent` | Dry/Wet, Mix | Linear | 100% → 1.0 |
| `gain_db` | Gain, Output | Linear dB | 3 dB → varies by range |
| `linear_fallback` | Unknown params | Linear scale | Based on min/max |
| `passthrough` | Already normalized | No conversion | 0.5 → 0.5 |

---

## Critical Lessons Learned

### 1. Always Validate Parameter Types

**Problem**: Assumed Compressor "Makeup" was a dB gain knob (common in other DAWs).  
**Reality**: It's a toggle button (on/off for auto-makeup).  
**Fix**: Removed the `makeup_linear` handler, changed preset from `"Makeup": 3` to `"Makeup": 1`.

**Lesson**: Never assume parameter types. Use `get_device_parameters` to verify:
```bash
python ableton_bridge.py get_device_parameters --track_index 0 --device_index 1
```

### 2. Case-Sensitive Keyword Matching Breaks Auto-Detection

**Problem**: `"release" in "Release"` → `False` in Python (case-sensitive).  
**Impact**: Auto-percentage conversion fired on time parameters, turning `75 ms` into `0.75 ms`.  
**Fix**: Convert `param_name` to lowercase before keyword checks (line 1106).

**Lesson**: Always use `.lower()` when doing keyword matching in parameter names.

### 3. New Methods Must Be Registered in `_SMART_METHODS`

**Problem**: Added `utility_width_percent` and `base_linear` but forgot to register them in `_SMART_METHODS` set.  
**Impact**: The smart normalization results were ignored, falling back to incorrect linear handling.  
**Fix**: Added to `_SMART_METHODS` at line 1137.

**Lesson**: When adding a new conversion method, **always** add its name to `_SMART_METHODS`.

### 4. Parameter Indices Change by Device State

**Problem**: Multiband Dynamics semantic mappings pointed to wrong indices (e.g., index 20 vs actual 19).  
**Reality**: Ableton's parameter layout can vary based on device state, enabled bands, etc.  
**Fix**: Got live parameter dump and updated all indices.

**Lesson**: Use parameter dumps from the **actual device state** you'll be controlling. Don't rely on documentation or assumptions.

### 5. Some Parameters Are Context-Dependent

**Problem**: Utility "Bass Mono" looked like a frequency (value: 120 Hz).  
**Reality**: It's two parameters: "Bass Mono" (toggle at index 6) + "Bass Freq" (frequency at index 7).  
**Fix**: Split preset into two separate parameters.

**Lesson**: Check parameter dumps to understand multi-part controls (toggles + values).

### 6. Auto-Percentage Only for Normalized Ranges

**Problem**: Width param has range [0, 2], not [0, 1], so auto-% didn't fire.  
**Impact**: System tried to set 100 (raw) instead of 1.0 (normalized).  
**Fix**: Added device-specific `utility_width_percent` handler.

**Lesson**: Auto-percentage only applies when `pmin==0.0 and pmax==1.0`. For custom ranges, add specific handlers.

### 7. Bipolar Ranges Need Offset Normalization

**Problem**: Saturator "Base" has range [-36, 36], not [0, 36].  
**Fix**: `(value + 36) / 72.0` to correctly map bipolar range.

**Lesson**: Always check min/max values. Bipolar ranges need `(value - min) / (max - min)`.

---

## Best Practices

### Adding Support for a New Device

1. **Get a parameter dump**:
   ```bash
   python ableton_bridge.py get_device_parameters --track_index X --device_index Y
   ```

2. **Identify parameter types**:
   - Frequency → use `freq_log`
   - Time (ms) → use `attack_log` / `release_log` / `decay_log`
   - Gain (dB) → use `gain_db`
   - Percentage → use `percent` or auto-%
   - Toggles → use `passthrough` (0 or 1)
   - Custom → add new handler

3. **Add semantic mappings** (if needed):
   ```python
   "DeviceName": {
       "param_key": ("Ableton Param Name", fallback_index),
   }
   ```

4. **Add normalization handler** (if needed):
   ```python
   if 'keyword' in name_lower and 'device' in device_lower:
       if value_range_check:
           return (normalized_value, "method_name")
   ```

5. **Register in `_SMART_METHODS`**:
   ```python
   _SMART_METHODS = {
       ...,
       "method_name",
   }
   ```

6. **Test thoroughly**:
   ```bash
   python scripts/apply_vocal_preset.py --track 0 --preset path/to/preset.json
   ```

### Debugging Parameter Issues

1. **Check the report**: `logs/vocal_preset_report.json` shows:
   - `normalized_sent`: What was sent to Ableton
   - `actual_value`: What Ableton returned
   - `conversion_method`: Which handler was used
   - `min`/`max`: Parameter range

2. **Test raw values**: Bypass normalization to test OSC:
   ```bash
   python ableton_bridge.py set_device_parameter --track_index 0 --device_index 1 --param_index 8 --value 0.5
   ```

3. **Check parameter names**: Case-sensitive! "Release" ≠ "release" in semantic mappings.

4. **Verify indices**: They can change based on device state. Always use live dumps.

5. **Check conversion method**: If it says `passthrough` or `linear_fallback`, the smart handler didn't fire.

---

## Common Pitfalls

| Issue | Symptom | Fix |
|-------|---------|-----|
| Value always returns 0.0 | Wrong param index or toggle expecting dB | Get param dump, verify index and type |
| Value clamped to max | Value outside param's real range | Check if param is bipolar or has unexpected range |
| Auto-% fires on time params | `75 ms` becomes `0.75 ms` | Add param name to `non_percentage_keywords` |
| Smart handler ignored | Report shows `linear_fallback` | Add method name to `_SMART_METHODS` |
| Keyword matching fails | Case mismatch | Use `.lower()` before keyword checks |
| Multi-value param fails | One param name controls multiple values | Split into separate params (e.g., Bass Mono + Bass Freq) |

---

## Parameter Dump Examples

### Compressor
```json
{
  "names": [
    "Device On",        // 0
    "Threshold",        // 1
    "Ratio",           // 2
    "Expansion Ratio", // 3
    "Attack",          // 4
    "Release",         // 5
    "Auto Release On/Off", // 6
    "Output Gain",     // 7
    "Makeup",          // 8 ← Toggle, not knob!
    "Dry/Wet",         // 9
    ...
  ]
}
```

### Utility
```json
{
  "names": [
    "Device On",       // 0
    "Left Inv",       // 1
    "Right Inv",      // 2
    "Channel Mode",   // 3
    "Stereo Width",   // 4
    "Mono",          // 5
    "Bass Mono",     // 6 ← Toggle
    "Bass Freq",     // 7 ← Frequency for Bass Mono
    "Balance",       // 8
    "Gain",          // 9
    "Mute",          // 10
    "DC Filter"      // 11
  ]
}
```

---

## Implementation Checklist

When adding a new device or fixing normalization:

- [ ] Get live parameter dump from Ableton
- [ ] Identify parameter types (frequency, time, gain, toggle, etc.)
- [ ] Add semantic mappings (if user-friendly names differ from Ableton names)
- [ ] Add normalization handlers (if standard methods don't apply)
- [ ] Register new methods in `_SMART_METHODS`
- [ ] Update `non_percentage_keywords` (if adding time/frequency params)
- [ ] Test with real preset values
- [ ] Check `vocal_preset_report.json` for verification
- [ ] Document any device-specific quirks

---

## Files to Know

| File | Purpose |
|------|---------|
| `ableton_controls/reliable_params.py` | Core normalization logic |
| `ableton_bridge.py` | CLI for testing parameters |
| `scripts/apply_vocal_preset.py` | Full preset application |
| `logs/vocal_preset_report.json` | Detailed per-parameter results |
| `knowledge/chains/*.json` | Preset files |

---

## Version History

### 2026-02-17: Major Normalization Overhaul
- Fixed 15 parameter normalization issues
- Added CLI flag support
- Fixed case-sensitive keyword matching
- Removed incorrect Makeup handler
- Added Multiband Dynamics, Saturator Base, Utility Width/Bass Mono support
- Achieved 100% success rate (68/68 parameters)

---

## See Also

- [Ableton OSC API Documentation](https://docs.cycling74.com/max8/vignettes/ableton_live_object_model)
- `reliable_params.py` inline comments for specific conversion formulas
- `walkthrough.md` in artifacts directory for this fix session
