#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import json
import os
import subprocess
import time

WHITELIST_SNIPPETS = [
    "Ableton Live",
    "has unexpectedly quit",
    "Recover",
    "plugin scan",
    "audio engine",
]


@dataclass
class WatchdogEvent:
    ts: str
    kind: str
    message: str
    extra: Dict


class AbletonWatchdog:
    def __init__(self, state_path: Path, launch_cmd: Optional[List[str]] = None, ableton_exe: Optional[str] = None):
        self.state_path = state_path
        self.ableton_exe = ableton_exe or os.getenv("ABLETON_EXE", "").strip()
        self.launch_cmd = launch_cmd or self._default_launch_cmd()
        self.events: List[WatchdogEvent] = []
        self.restarts = 0
        self.dialogs_handled = 0

    def _find_ableton_exe(self) -> Optional[str]:
        candidates = []
        if self.ableton_exe:
            candidates.append(self.ableton_exe)
        candidates.extend([
            r"C:\ProgramData\Ableton\Live 12 Suite\Program\Ableton Live 12 Suite.exe",
            r"C:\ProgramData\Ableton\Live 12 Standard\Program\Ableton Live 12 Standard.exe",
            r"C:\ProgramData\Ableton\Live 12 Intro\Program\Ableton Live 12 Intro.exe",
            r"C:\ProgramData\Ableton\Live 11 Suite\Program\Ableton Live 11 Suite.exe",
            r"C:\ProgramData\Ableton\Live 11 Standard\Program\Ableton Live 11 Standard.exe",
            r"C:\ProgramData\Ableton\Live 11 Intro\Program\Ableton Live 11 Intro.exe",
        ])
        for p in candidates:
            if p and Path(p).exists():
                return p
        return None

    def _default_launch_cmd(self) -> List[str]:
        exe = self._find_ableton_exe()
        if exe:
            return [exe]
        return ["cmd", "/c", "start", "", "Ableton Live"]

    def _emit(self, kind: str, message: str, **extra):
        evt = WatchdogEvent(
            ts=datetime.now().isoformat(),
            kind=kind,
            message=message,
            extra=extra,
        )
        self.events.append(evt)

    def _is_ableton_running(self) -> bool:
        # Robust process detection: scan full tasklist output.
        try:
            out = subprocess.check_output(
                ["tasklist"],
                stderr=subprocess.STDOUT,
                text=True,
            )
            low = out.lower()
            return ("ableton live" in low) or ("ableton" in low and ".exe" in low)
        except Exception:
            return False

    def ensure_running(self, max_restarts: int = 3) -> bool:
        if self._is_ableton_running():
            self._emit("heartbeat", "Ableton process detected")
            return True

        while self.restarts < max_restarts:
            self.restarts += 1
            self._emit("restart", "Ableton not running, attempting launch", attempt=self.restarts, launch_cmd=self.launch_cmd)
            try:
                subprocess.Popen(self.launch_cmd)
            except Exception as e:
                self._emit("error", f"Launch failed: {e}", attempt=self.restarts)
                time.sleep(2)
                continue

            # Ableton can take a while to appear in process list.
            for _ in range(12):  # up to ~24s
                time.sleep(2)
                if self._is_ableton_running():
                    self._emit("recovered", "Ableton launch succeeded", attempt=self.restarts)
                    return True

        self._emit("fatal", "Could not start Ableton after retries", restarts=self.restarts)
        return False

    def handle_dialog_text(self, dialog_text: str) -> bool:
        if any(snippet.lower() in dialog_text.lower() for snippet in WHITELIST_SNIPPETS):
            self.dialogs_handled += 1
            self._emit("dialog_auto", "Whitelisted dialog detected; safe auto-click approved", text=dialog_text[:240])
            return True

        self._emit("dialog_blocked", "Unknown dialog detected; manual intervention required", text=dialog_text[:240])
        return False

    def snapshot(self) -> Dict:
        return {
            "restarts": self.restarts,
            "dialogs_handled": self.dialogs_handled,
            "last_event": asdict(self.events[-1]) if self.events else None,
            "events": [asdict(e) for e in self.events[-20:]],
        }

    def persist(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at": datetime.now().isoformat(),
            "watchdog": self.snapshot(),
        }
        self.state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
