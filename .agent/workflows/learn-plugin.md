---
description: Learn a new Ableton plugin's parameters and add normalization support
---
// turbo-all

# Learn Plugin Workflow

This workflow discovers all parameters for an Ableton device and generates the semantic mappings/normalization handlers needed for full preset support.

## Prerequisites
- Ableton Live is running with AbletonOSC connected
- The target device is loaded on a track

## Step 1: Identify the target device

Ask the user which track and device to learn: 
- Track index (0-based)
- Device index (0-based)

If unsure, list all devices on the track:
```bash
python ableton_bridge.py get_track_devices --track_index <TRACK>
```

## Step 2: Dump all parameters

```bash
python ableton_bridge.py get_device_parameters --track_index <TRACK> --device_index <DEVICE>
```

Save the output — this is the source of truth for parameter names and indices.

## Step 3: Read each parameter's current value and range

For each parameter index from the dump, get its current value:
```bash
python ableton_bridge.py get_device_parameter_value --track_index <TRACK> --device_index <DEVICE> --param_index <INDEX>
```

Or use the bulk script:
```bash
python scripts/dump_device_params.py --track <TRACK> --device <DEVICE>
```

## Step 4: Classify each parameter

For every parameter, determine its type:

| Type | Indicators | Normalization |
|------|-----------|---------------|
| **Toggle** | Name has "On", "Off", "Mute", "Solo", range [0,1], only 0 or 1 values | `passthrough` |
| **Enum** | Name has "Type", "Mode", "Model", range [0, N] where N is small | `passthrough` or `enum_raw` |
| **Frequency** | Name has "Freq", "Hz", "Cut", "Filter" | `freq_log` |
| **Time (ms)** | Name has "Attack", "Release", "Decay", "Time", "Delay" | `attack_log`, `release_log`, `decay_log` |
| **Gain (dB)** | Name has "Gain", "Output", "Volume", range like [-36,36] or [-24,24] | `gain_db` |
| **Ratio** | Name has "Ratio" | `ratio_lut` |
| **Threshold** | Name has "Threshold" | `threshold_lut` |
| **Percentage** | Name has "Dry/Wet", "Mix", "Amount", "Depth", range [0,1] | `percent` or auto-% |
| **Bipolar** | range like [-X, X], e.g., [-36, 36] | `(value + max) / (2 * max)` |
| **Custom** | Anything else | Needs manual investigation |

### CRITICAL checks:
- **Is it a toggle or a knob?** Look at each parameter in Ableton's UI. "Makeup" looked like a gain knob but was actually a button.
- **Is it one param or two?** Some controls are split (e.g., "Bass Mono" toggle + "Bass Freq" value).
- **What's the real display range?** The OSC range [0,1] doesn't tell you the display range. Check the UI.

## Step 5: Add semantic mappings

In `ableton_controls/reliable_params.py`, add to `SEMANTIC_PARAM_MAPPINGS`:

```python
"DeviceName": {
    "user_friendly_key": ("Ableton Param Name", index),
    # ... for each param that presets need to control
},
```

Rules:
- Keys are lowercase with underscores (e.g., `"high_threshold"`)  
- Values are tuples of (exact Ableton name from dump, fallback index)
- Include ALL params that presets might want to set
- Skip "Device On" (index 0) — handled separately

## Step 6: Add normalization handlers (if needed)

If a parameter needs a new normalization method:

1. Add the handler in `smart_normalize_parameter()`:
```python
if 'keyword' in name_lower and 'device' in device_lower:
    if value_range_check:
        return (normalized_value, "method_name")
```

2. **Register in `_SMART_METHODS`** (line ~1137):
```python
_SMART_METHODS = {
    ...,
    "method_name",
}
```

3. If the param is a percentage-like value > 1.0, add to `non_percentage_keywords` if it should NOT auto-convert.

## Step 7: Create a test preset

Create a JSON preset in `knowledge/chains/` with representative values:
```json
{
  "name": "Test Preset",
  "chain": [
    {
      "plugin_name": "DeviceName",
      "parameters": {
        "ParamName": value,
        ...
      }
    }
  ]
}
```

## Step 8: Run verification test

```bash
python scripts/apply_vocal_preset.py --track <TRACK> --preset knowledge/chains/test_preset.json
```

Check `logs/vocal_preset_report.json` for:
- All `"success": true`
- `conversion_method` is correct (not `linear_fallback` or `passthrough` for params that need smart handling)
- `actual_value` matches expected

## Step 9: Save the parameter dump

Save the dump to `knowledge/device_params/` for future reference:
```bash
python ableton_bridge.py get_device_parameters --track_index <TRACK> --device_index <DEVICE> > knowledge/device_params/DeviceName.json
```

## Step 10: Update documentation

Add the device to `docs/parameter_normalization_guide.md`:
- Parameter dump with index numbers
- Any quirks discovered
- Which params are toggles vs knobs
