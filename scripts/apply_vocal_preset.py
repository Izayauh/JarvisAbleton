#!/usr/bin/env python3
"""
Apply Vocal Preset — Single-preset live test

Reads a vocal chain JSON (default: Travis Scott) and applies it to a track
in Ableton Live using the bridge layer. No LLM, no research pipeline, no
async — just load devices and set parameters.

Usage:
    python scripts/apply_vocal_preset.py --track 0
    python scripts/apply_vocal_preset.py --track 0 --preset knowledge/chains/travis_scott.json
    python scripts/apply_vocal_preset.py --track 0 --dry-run          # validate only
    python scripts/apply_vocal_preset.py --track 0 --device 2         # start from device #2 only (skip loads, just set params)

Requirements:
    - Ableton Live running with AbletonOSC on port 11000
    - JarvisDeviceLoader Remote Script active on port 11002
"""

import argparse
import json
import os
import sys
import time

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from osc_preflight import check_osc_bridge


# ---------------------------------------------------------------------------
# Bridge helpers — call ableton_bridge functions in-process
# ---------------------------------------------------------------------------

def _execute(func_name: str, args: dict) -> dict:
    """Call an ableton_bridge function directly."""
    import ableton_bridge
    dispatch = ableton_bridge._build_dispatch(args)
    if func_name not in dispatch:
        return {"success": False, "message": f"Unknown function: {func_name}"}
    try:
        return dispatch[func_name]()
    except Exception as e:
        return {"success": False, "message": str(e)}


# ---------------------------------------------------------------------------
# Core: load one device and set its parameters
# ---------------------------------------------------------------------------

def load_and_configure_device(track_index: int, plugin_name: str,
                               parameters: dict, device_index: int,
                               dry_run: bool = False) -> dict:
    """
    Load a single device onto a track and configure its parameters.

    Args:
        track_index: 0-based track index
        plugin_name: Ableton device name (e.g. "EQ Eight")
        parameters: Dict of param_name -> value
        device_index: Expected device index after loading
        dry_run: If True, print plan without executing

    Returns:
        Summary dict with load/param results
    """
    result = {
        "plugin_name": plugin_name,
        "device_index": device_index,
        "loaded": False,
        "params_set": 0,
        "params_failed": 0,
        "param_details": [],
        "errors": [],
    }

    if dry_run:
        print(f"  [DRY-RUN] Would load '{plugin_name}' at device index {device_index}")
        for name, val in parameters.items():
            print(f"    {name} = {val}")
        result["loaded"] = True
        result["params_set"] = len(parameters)
        return result

    # --- Load the device ---
    print(f"  Loading '{plugin_name}'...", end=" ", flush=True)
    load_result = _execute("add_plugin_to_track", {
        "track_index": track_index,
        "plugin_name": plugin_name,
        "position": -1,
    })

    if not load_result.get("success"):
        msg = load_result.get("message", "unknown error")
        print(f"FAILED ({msg})")
        result["errors"].append(f"Load failed: {msg}")
        return result

    print("OK")
    result["loaded"] = True

    # Give Ableton time to initialize the device
    time.sleep(1.0)

    # --- Verify the device appeared ---
    devices_result = _execute("get_track_devices", {"track_index": track_index})
    if devices_result.get("success"):
        devices = devices_result.get("devices", [])
        print(f"    Device chain now: {devices}")
        if device_index < len(devices):
            actual_name = devices[device_index]
            if plugin_name.lower() not in actual_name.lower():
                print(f"    WARNING: Expected '{plugin_name}' at index {device_index}, "
                      f"got '{actual_name}'")

    # --- Set parameters ---
    if not parameters:
        return result

    print(f"    Setting {len(parameters)} parameters...")
    param_result = _execute("set_device_parameters_by_name", {
        "track_index": track_index,
        "device_index": device_index,
        "params": parameters,
    })

    if param_result.get("success"):
        total = param_result.get("total", 0)
        succeeded = param_result.get("succeeded", 0)
        failed_count = param_result.get("failed", 0)
        not_found = param_result.get("not_found", 0)
        result["params_set"] = succeeded
        result["params_failed"] = failed_count + not_found

        for detail in param_result.get("details", []):
            status = "OK" if detail.get("success") else "FAIL"
            name = detail.get("param_name", "?")
            req = detail.get("requested_value", "?")
            actual = detail.get("actual_value", "?")
            verified = detail.get("verified", False)
            vstr = "verified" if verified else "unverified"
            print(f"      [{status}] {name}: {req} -> {actual} ({vstr})")
            result["param_details"].append(detail)

        if not_found > 0:
            print(f"    {not_found} parameter(s) not found on device")
        if failed_count > 0:
            print(f"    {failed_count} parameter(s) failed to set")
    else:
        msg = param_result.get("message", "unknown")
        print(f"    Parameter setting failed: {msg}")
        result["errors"].append(f"Params failed: {msg}")
        result["params_failed"] = len(parameters)

    return result


def set_params_only(track_index: int, plugin_name: str,
                    parameters: dict, device_index: int) -> dict:
    """Set parameters on an already-loaded device (skip loading)."""
    result = {
        "plugin_name": plugin_name,
        "device_index": device_index,
        "loaded": True,
        "params_set": 0,
        "params_failed": 0,
        "param_details": [],
        "errors": [],
    }

    print(f"  Setting params on existing device {device_index} ('{plugin_name}')...")
    param_result = _execute("set_device_parameters_by_name", {
        "track_index": track_index,
        "device_index": device_index,
        "params": parameters,
    })

    if param_result.get("success"):
        succeeded = param_result.get("succeeded", 0)
        failed_count = param_result.get("failed", 0)
        not_found = param_result.get("not_found", 0)
        result["params_set"] = succeeded
        result["params_failed"] = failed_count + not_found

        for detail in param_result.get("details", []):
            status = "OK" if detail.get("success") else "FAIL"
            name = detail.get("param_name", "?")
            req = detail.get("requested_value", "?")
            actual = detail.get("actual_value", "?")
            verified = detail.get("verified", False)
            vstr = "verified" if verified else "unverified"
            print(f"      [{status}] {name}: {req} -> {actual} ({vstr})")
            result["param_details"].append(detail)
    else:
        msg = param_result.get("message", "unknown")
        print(f"    Failed: {msg}")
        result["errors"].append(msg)
        result["params_failed"] = len(parameters)

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Apply a vocal preset to a track")
    parser.add_argument("--track", type=int, required=True, help="Track index (0-based)")
    parser.add_argument("--preset", type=str,
                        default=os.path.join(_REPO_ROOT, "knowledge", "chains", "travis_scott.json"),
                        help="Path to preset JSON file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print plan without executing")
    parser.add_argument("--device", type=int, default=None,
                        help="Start device index (skip loading, just set params from this index)")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip OSC preflight check")
    args = parser.parse_args()

    # Load preset
    print(f"Loading preset: {args.preset}")
    with open(args.preset) as f:
        preset = json.load(f)

    artist = preset.get("artist", "Unknown")
    track_type = preset.get("track_type", "vocal")
    chain = preset.get("chain", [])
    print(f"Preset: {artist} {track_type} chain ({len(chain)} devices)")
    print()

    # Preflight
    if not args.dry_run and not args.skip_preflight:
        print("[PREFLIGHT] Checking OSC bridge...")
        preflight = check_osc_bridge(_execute, attempts=3, delay_s=0.5)
        if not preflight["ok"]:
            print(f"[FAIL] OSC bridge unreachable: {preflight['message']}")
            print("Make sure Ableton is running with AbletonOSC active.")
            sys.exit(1)
        print(f"[OK] OSC bridge responding\n")

        # Verify track exists
        track_list = _execute("get_track_list", {})
        if track_list.get("success"):
            tracks = track_list.get("tracks", [])
            if args.track >= len(tracks):
                print(f"[FAIL] Track {args.track} does not exist. "
                      f"Available: {len(tracks)} tracks (0-{len(tracks)-1})")
                sys.exit(1)
            track_name = tracks[args.track].get("name", f"Track {args.track + 1}")
            print(f"Target: Track {args.track + 1} ({track_name})\n")

    # Show plan
    print("=" * 60)
    print(f"VOCAL CHAIN: {artist}")
    print("=" * 60)
    for i, device in enumerate(chain):
        name = device.get("plugin_name", "?")
        purpose = device.get("purpose", "")
        params = device.get("parameters", {})
        print(f"  {i+1}. {name} ({len(params)} params) — {purpose}")
    print()

    if args.dry_run:
        print("[DRY-RUN MODE] No changes will be made.\n")

    # Apply chain
    results = []
    total_params_set = 0
    total_params_failed = 0
    total_loaded = 0
    total_load_failed = 0

    # Get current device count to calculate device indices
    if not args.dry_run and args.device is None:
        dev_count_result = _execute("get_num_devices", {"track_index": args.track})
        existing_devices = dev_count_result.get("count", 0) if dev_count_result.get("success") else 0
        print(f"Existing devices on track: {existing_devices}\n")
    else:
        existing_devices = 0

    for i, device in enumerate(chain):
        plugin_name = device.get("plugin_name", "")
        parameters = device.get("parameters", {})

        # Calculate the device index: existing devices + position in our chain
        if args.device is not None:
            # User specified starting device index — set params only
            dev_idx = args.device + i
            r = set_params_only(args.track, plugin_name, parameters, dev_idx)
        else:
            dev_idx = existing_devices + i
            r = load_and_configure_device(
                args.track, plugin_name, parameters, dev_idx,
                dry_run=args.dry_run)

        results.append(r)
        if r["loaded"]:
            total_loaded += 1
        else:
            total_load_failed += 1
        total_params_set += r["params_set"]
        total_params_failed += r["params_failed"]
        print()

    # Summary
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"  Devices loaded:     {total_loaded}/{len(chain)}")
    if total_load_failed:
        print(f"  Devices FAILED:     {total_load_failed}")
    print(f"  Parameters set:     {total_params_set}")
    if total_params_failed:
        print(f"  Parameters FAILED:  {total_params_failed}")

    # Per-device summary
    print()
    for r in results:
        status = "OK" if r["loaded"] and r["params_failed"] == 0 else "PARTIAL" if r["loaded"] else "FAIL"
        print(f"  [{status}] {r['plugin_name']}: "
              f"{r['params_set']}/{r['params_set']+r['params_failed']} params")
        for err in r["errors"]:
            print(f"         Error: {err}")

    # Write report
    log_dir = os.path.join(_REPO_ROOT, "logs")
    os.makedirs(log_dir, exist_ok=True)
    report_path = os.path.join(log_dir, "vocal_preset_report.json")
    report = {
        "preset": os.path.basename(args.preset),
        "artist": artist,
        "track_index": args.track,
        "dry_run": args.dry_run,
        "devices_loaded": total_loaded,
        "devices_failed": total_load_failed,
        "params_set": total_params_set,
        "params_failed": total_params_failed,
        "results": results,
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport: {report_path}")

    all_ok = total_load_failed == 0 and total_params_failed == 0
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
