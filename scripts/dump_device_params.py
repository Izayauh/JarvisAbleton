#!/usr/bin/env python3
"""
Dump all parameters for an Ableton device with detailed info.

Usage:
    python scripts/dump_device_params.py --track 0 --device 1
    python scripts/dump_device_params.py --track 0 --device 1 --save

Outputs a comprehensive JSON with each parameter's:
  - Index, name, current value, min, max
  - Guessed type (toggle, frequency, gain, time, percentage, enum, unknown)
  - Whether it's likely a [0,1] normalized param
"""

import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def classify_parameter(name: str, pmin: float, pmax: float, value: float) -> dict:
    """Classify a parameter based on its name, range, and current value."""
    name_lower = name.lower()
    
    classification = {
        "likely_type": "unknown",
        "normalized_range": pmin == 0.0 and pmax == 1.0,
        "bipolar": pmin < 0 and pmax > 0 and abs(abs(pmin) - abs(pmax)) < 0.01,
        "suggested_method": "passthrough" if pmin == 0.0 and pmax == 1.0 else "linear_fallback",
    }
    
    # Toggle detection
    if pmin == 0.0 and pmax == 1.0 and value in (0.0, 1.0):
        toggle_keywords = ['on', 'off', 'mute', 'solo', 'arm', 'listen', 'mono',
                          'inv', 'filter', 'activator', 'enabled', 's/c on']
        if any(kw in name_lower for kw in toggle_keywords) or name.endswith(' On/Off'):
            classification["likely_type"] = "toggle"
            classification["suggested_method"] = "passthrough"
            classification["notes"] = "Binary on/off - set to 0 or 1"
            return classification
    
    # Enum detection
    if pmin == 0.0 and pmax in range(2, 20) and value == int(value):
        enum_keywords = ['type', 'mode', 'model', 'slope', 'shape', 'waveform',
                        'channel', 'env', 'algorithm']
        if any(kw in name_lower for kw in enum_keywords):
            classification["likely_type"] = "enum"
            classification["suggested_method"] = "enum_raw"
            classification["notes"] = f"Enum with {int(pmax) + 1} options (0-{int(pmax)})"
            return classification
    
    # Frequency detection
    freq_keywords = ['frequency', 'freq', 'hz', 'cut', 'crossover']
    if any(kw in name_lower for kw in freq_keywords):
        classification["likely_type"] = "frequency"
        classification["suggested_method"] = "freq_log"
        classification["notes"] = "Logarithmic frequency mapping (20-20000 Hz)"
        return classification
    
    # Time detection
    time_keywords = ['attack', 'release', 'decay', 'time', 'delay', 'predelay', 'lookahead']
    if any(kw in name_lower for kw in time_keywords):
        if 'attack' in name_lower:
            classification["likely_type"] = "time_ms"
            classification["suggested_method"] = "attack_log"
        elif 'release' in name_lower:
            classification["likely_type"] = "time_ms"
            classification["suggested_method"] = "release_log"
        elif 'decay' in name_lower:
            classification["likely_type"] = "time_ms"
            classification["suggested_method"] = "decay_log"
        elif 'predelay' in name_lower or 'pre delay' in name_lower:
            classification["likely_type"] = "time_ms"
            classification["suggested_method"] = "predelay_linear"
        else:
            classification["likely_type"] = "time_ms"
            classification["suggested_method"] = "release_log"
        classification["notes"] = "Time parameter in milliseconds"
        return classification
    
    # Gain detection
    gain_keywords = ['gain', 'output', 'volume', 'level']
    if any(kw in name_lower for kw in gain_keywords):
        classification["likely_type"] = "gain_db"
        classification["suggested_method"] = "gain_db"
        if classification["bipolar"]:
            classification["notes"] = f"Bipolar gain in dB [{pmin}, {pmax}]"
        else:
            classification["notes"] = f"Gain in dB [{pmin}, {pmax}]"
        return classification
    
    # Threshold detection
    if 'threshold' in name_lower:
        classification["likely_type"] = "threshold"
        classification["suggested_method"] = "threshold_lut"
        classification["notes"] = "Threshold in dB"
        return classification
    
    # Ratio detection
    if 'ratio' in name_lower:
        classification["likely_type"] = "ratio"
        classification["suggested_method"] = "ratio_lut"
        classification["notes"] = "Compression/expansion ratio"
        return classification
    
    # Percentage / mix detection
    pct_keywords = ['dry/wet', 'dry', 'wet', 'mix', 'amount', 'depth', 'width',
                    'blend', 'intensity', 'stereo', 'balance', 'pan']
    if any(kw in name_lower for kw in pct_keywords):
        classification["likely_type"] = "percentage"
        classification["suggested_method"] = "percent"
        classification["notes"] = "Percentage value (0-100%)"
        return classification
    
    # Drive detection
    if 'drive' in name_lower:
        classification["likely_type"] = "drive"
        classification["suggested_method"] = "drive_linear"
        classification["notes"] = f"Drive in dB [{pmin}, {pmax}]"
        return classification
    
    # Q/Resonance detection
    if any(kw in name_lower for kw in ['resonance', ' q', 'q ']):
        classification["likely_type"] = "q"
        classification["suggested_method"] = "q_log"
        classification["notes"] = "Q/Resonance factor"
        return classification
    
    # Bipolar unknown
    if classification["bipolar"]:
        classification["notes"] = f"Bipolar range [{pmin}, {pmax}] - needs investigation"
    elif not classification["normalized_range"]:
        classification["notes"] = f"Custom range [{pmin}, {pmax}] - needs investigation"
    
    return classification


def main():
    parser = argparse.ArgumentParser(description="Dump and classify device parameters")
    parser.add_argument("--track", type=int, required=True, help="Track index (0-based)")
    parser.add_argument("--device", type=int, required=True, help="Device index (0-based)")
    parser.add_argument("--save", action="store_true", help="Save to knowledge/device_params/")
    args = parser.parse_args()
    
    try:
        from ableton_controls.ableton_control import AbletonOSCController
        ableton = AbletonOSCController()
    except Exception as e:
        print(f"Error connecting to Ableton: {e}")
        sys.exit(1)
    
    # Get device name
    try:
        device_name = ableton.get_device_name(args.track, args.device)
    except:
        device_name = f"Device_{args.device}"
    
    # Get parameter names
    try:
        param_names = ableton.get_device_parameters_name_sync(args.track, args.device)
        names = param_names.get("names", [])
    except Exception as e:
        print(f"Error getting parameters: {e}")
        sys.exit(1)
    
    # Get ranges and values for each parameter
    from ableton_controls.reliable_params import ReliableParamController
    rpc = ReliableParamController(ableton)
    
    parameters = []
    for i, name in enumerate(names):
        pmin, pmax = rpc.get_parameter_range(args.track, args.device, i)
        try:
            value = ableton.get_device_parameter_value_sync(args.track, args.device, i)
            if isinstance(value, dict):
                value = value.get("value", 0.0)
        except:
            value = None
        
        classification = classify_parameter(name, pmin, pmax, value if value else 0.0)
        
        param_info = {
            "index": i,
            "name": name,
            "value": value,
            "min": pmin,
            "max": pmax,
            **classification,
        }
        parameters.append(param_info)
    
    # Build output
    result = {
        "device_name": device_name,
        "track_index": args.track,
        "device_index": args.device,
        "param_count": len(names),
        "parameters": parameters,
        "semantic_mapping_template": {},
        "needs_investigation": [],
    }
    
    # Generate semantic mapping template
    for p in parameters:
        if p["index"] == 0:  # Skip "Device On"
            continue
        key = p["name"].lower().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")
        result["semantic_mapping_template"][key] = [p["name"], p["index"]]
        if p["likely_type"] == "unknown":
            result["needs_investigation"].append({
                "index": p["index"],
                "name": p["name"],
                "range": [p["min"], p["max"]],
                "current_value": p["value"],
            })
    
    # Print report
    print(json.dumps(result, indent=2, default=str))
    
    # Print summary
    type_counts = {}
    for p in parameters:
        t = p["likely_type"]
        type_counts[t] = type_counts.get(t, 0) + 1
    
    print(f"\n--- Summary for {device_name} ---", file=sys.stderr)
    print(f"Total parameters: {len(parameters)}", file=sys.stderr)
    for t, count in sorted(type_counts.items()):
        print(f"  {t}: {count}", file=sys.stderr)
    if result["needs_investigation"]:
        print(f"\n⚠️  {len(result['needs_investigation'])} params need manual investigation:", file=sys.stderr)
        for p in result["needs_investigation"]:
            print(f"  [{p['index']}] {p['name']} range={p['range']} value={p['current_value']}", file=sys.stderr)
    
    # Save if requested
    if args.save:
        save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "knowledge", "device_params")
        os.makedirs(save_dir, exist_ok=True)
        safe_name = device_name.replace(" ", "_").replace("/", "_")
        save_path = os.path.join(save_dir, f"{safe_name}.json")
        with open(save_path, "w") as f:
            json.dump(result, indent=2, fp=f, default=str)
        print(f"\n✅ Saved to {save_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
