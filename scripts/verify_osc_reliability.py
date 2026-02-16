#!/usr/bin/env python3
"""
OSC Reliability Stress Test

Live stress test for the verified SET→GET loop on track-level OSC operations.
Requires Ableton Live running with AbletonOSC active.

Usage:
    python scripts/verify_osc_reliability.py --track 0 --quick
    python scripts/verify_osc_reliability.py --track 0 --iterations 100

Exit 0 if all tests >= 95% verified, exit 1 otherwise.
"""

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

# Ensure repo root is on sys.path
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from osc_preflight import check_osc_bridge


# ---------------------------------------------------------------------------
# Data classes (consistent with tests/parameter_reliability_test.py)
# ---------------------------------------------------------------------------

@dataclass
class VerifyResult:
    """Result of a single verified SET operation."""
    iteration: int
    operation: str
    expected: object
    actual: object
    verified: bool
    attempts: int
    latency_s: float
    message: str = ""


@dataclass
class StressTestReport:
    """Aggregate results for one test category."""
    test_name: str
    iterations: int = 0
    verified_count: int = 0
    unverified_count: int = 0
    error_count: int = 0
    total_latency_s: float = 0.0
    results: List[VerifyResult] = field(default_factory=list)

    @property
    def verified_rate(self) -> float:
        return (self.verified_count / self.iterations * 100) if self.iterations else 0.0

    @property
    def avg_latency_ms(self) -> float:
        return (self.total_latency_s / self.iterations * 1000) if self.iterations else 0.0

    def add(self, r: VerifyResult):
        self.results.append(r)
        self.iterations += 1
        self.total_latency_s += r.latency_s
        if r.verified:
            self.verified_count += 1
        elif r.actual is None:
            self.error_count += 1
        else:
            self.unverified_count += 1

    def to_dict(self) -> dict:
        return {
            "test_name": self.test_name,
            "iterations": self.iterations,
            "verified_count": self.verified_count,
            "unverified_count": self.unverified_count,
            "error_count": self.error_count,
            "verified_rate_pct": round(self.verified_rate, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
        }


# ---------------------------------------------------------------------------
# Execute helper — calls ableton_bridge as a library
# ---------------------------------------------------------------------------

def _execute(func_name: str, args: dict) -> dict:
    """Call an ableton_bridge function directly (in-process)."""
    import ableton_bridge
    dispatch = ableton_bridge._build_dispatch(args)
    if func_name not in dispatch:
        return {"success": False, "message": f"Unknown function: {func_name}"}
    try:
        return dispatch[func_name]()
    except Exception as e:
        return {"success": False, "message": str(e)}


# ---------------------------------------------------------------------------
# Test runners
# ---------------------------------------------------------------------------

def run_mute_test(track_index: int, iterations: int) -> StressTestReport:
    """Toggle mute on/off with verify=True."""
    report = StressTestReport(test_name="mute_toggle")
    for i in range(iterations):
        muted_val = i % 2  # alternate 0, 1
        t0 = time.time()
        result = _execute("mute_track", {
            "track_index": track_index,
            "muted": muted_val,
            "verify": True,
        })
        elapsed = time.time() - t0
        report.add(VerifyResult(
            iteration=i,
            operation=f"mute={muted_val}",
            expected=muted_val,
            actual=result.get("actual"),
            verified=result.get("verified", False),
            attempts=result.get("attempts", 0),
            latency_s=elapsed,
            message=result.get("message", ""),
        ))
    return report


def run_volume_test(track_index: int, iterations: int) -> StressTestReport:
    """Set volume to cycling values with verify=True."""
    report = StressTestReport(test_name="volume_set")
    values = [0.0, 0.5, 0.85, 1.0, 0.25]
    for i in range(iterations):
        vol = values[i % len(values)]
        t0 = time.time()
        result = _execute("set_track_volume", {
            "track_index": track_index,
            "volume": vol,
            "verify": True,
        })
        elapsed = time.time() - t0
        report.add(VerifyResult(
            iteration=i,
            operation=f"volume={vol}",
            expected=vol,
            actual=result.get("actual"),
            verified=result.get("verified", False),
            attempts=result.get("attempts", 0),
            latency_s=elapsed,
            message=result.get("message", ""),
        ))
    return report


def run_solo_test(track_index: int, iterations: int) -> StressTestReport:
    """Toggle solo on/off with verify=True."""
    report = StressTestReport(test_name="solo_toggle")
    for i in range(iterations):
        soloed_val = i % 2
        t0 = time.time()
        result = _execute("solo_track", {
            "track_index": track_index,
            "soloed": soloed_val,
            "verify": True,
        })
        elapsed = time.time() - t0
        report.add(VerifyResult(
            iteration=i,
            operation=f"solo={soloed_val}",
            expected=soloed_val,
            actual=result.get("actual"),
            verified=result.get("verified", False),
            attempts=result.get("attempts", 0),
            latency_s=elapsed,
            message=result.get("message", ""),
        ))
    return report


# ---------------------------------------------------------------------------
# Safe state restore
# ---------------------------------------------------------------------------

def restore_safe_state(track_index: int):
    """Restore track to safe state: unmuted, unsoloed, volume 0.85."""
    _execute("mute_track", {"track_index": track_index, "muted": 0})
    _execute("solo_track", {"track_index": track_index, "soloed": 0})
    _execute("set_track_volume", {"track_index": track_index, "volume": 0.85})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="OSC reliability stress test")
    parser.add_argument("--track", type=int, default=0, help="Track index (0-based)")
    parser.add_argument("--iterations", type=int, default=100, help="Iterations per test")
    parser.add_argument("--quick", action="store_true", help="Quick mode (10 iterations)")
    args = parser.parse_args()

    iterations = 10 if args.quick else args.iterations

    # Preflight
    print(f"[PREFLIGHT] Checking OSC bridge...")
    preflight = check_osc_bridge(_execute, attempts=3, delay_s=0.5)
    if not preflight["ok"]:
        print(f"[FAIL] OSC bridge unreachable: {preflight['message']}")
        sys.exit(1)
    print(f"[OK] OSC bridge responding (latency: {preflight.get('latency_ms', '?')}ms)")

    print(f"\nRunning stress test on track {args.track} with {iterations} iterations per test\n")

    reports: List[StressTestReport] = []

    # Run tests
    for name, runner in [
        ("Mute Toggle", run_mute_test),
        ("Volume Set", run_volume_test),
        ("Solo Toggle", run_solo_test),
    ]:
        print(f"--- {name} ---")
        report = runner(args.track, iterations)
        reports.append(report)
        print(f"  Verified: {report.verified_count}/{report.iterations} "
              f"({report.verified_rate:.1f}%)  "
              f"Avg latency: {report.avg_latency_ms:.0f}ms")

    # Restore
    print("\nRestoring safe state...")
    restore_safe_state(args.track)

    # Summary
    print("\n" + "=" * 60)
    print("STRESS TEST SUMMARY")
    print("=" * 60)
    all_pass = True
    for r in reports:
        status = "PASS" if r.verified_rate >= 95.0 else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"  [{status}] {r.test_name}: {r.verified_rate:.1f}% verified "
              f"({r.verified_count}/{r.iterations})")

    # Write JSON report
    log_dir = os.path.join(_REPO_ROOT, "logs")
    os.makedirs(log_dir, exist_ok=True)
    report_path = os.path.join(log_dir, "osc_reliability_report.json")
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "track_index": args.track,
        "iterations_per_test": iterations,
        "all_pass": all_pass,
        "reports": [r.to_dict() for r in reports],
    }
    with open(report_path, "w") as f:
        json.dump(report_data, f, indent=2)
    print(f"\nReport written to: {report_path}")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
