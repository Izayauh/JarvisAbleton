"""
Storage Manager for Jarvis-Ableton project.

Handles cleanup of accumulated files: screenshots, logs, crash reports, and caches.
"""

import os
import glob
import shutil
import time
import logging

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages disk cleanup for the Jarvis-Ableton project."""

    def __init__(
        self,
        project_root,
        max_screenshot_age_days=7,
        max_log_age_days=30,
        max_cache_age_days=14,
        dry_run=False,
    ):
        self.project_root = project_root
        self.max_screenshot_age_days = max_screenshot_age_days
        self.max_log_age_days = max_log_age_days
        self.max_cache_age_days = max_cache_age_days
        self.dry_run = dry_run

    def _age_days(self, filepath):
        """Return file age in days based on modification time."""
        try:
            mtime = os.path.getmtime(filepath)
            return (time.time() - mtime) / 86400
        except OSError:
            return 0

    def _delete_file(self, filepath):
        """Delete a file and return its size. Respects dry_run."""
        try:
            size = os.path.getsize(filepath)
            if not self.dry_run:
                os.remove(filepath)
            return size
        except OSError as e:
            logger.warning(f"Failed to delete {filepath}: {e}")
            return 0

    def _delete_dir(self, dirpath):
        """Delete a directory tree and return total size. Respects dry_run."""
        total = 0
        try:
            for root, dirs, files in os.walk(dirpath):
                for f in files:
                    try:
                        total += os.path.getsize(os.path.join(root, f))
                    except OSError:
                        pass
            if not self.dry_run:
                shutil.rmtree(dirpath, ignore_errors=True)
        except OSError as e:
            logger.warning(f"Failed to delete directory {dirpath}: {e}")
        return total

    def _dir_size(self, dirpath):
        """Return total size of a directory in bytes."""
        total = 0
        if not os.path.isdir(dirpath):
            return 0
        for root, dirs, files in os.walk(dirpath):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
        return total

    def clean_screenshots(self):
        """Delete old PNG screenshots from root and screenshots/ directory."""
        result = {"deleted_count": 0, "freed_bytes": 0, "files": []}
        max_age = self.max_screenshot_age_days

        # Root-level PNGs (ableton_verify_*, ableton_monitor3_*, research_bot_capture_*)
        patterns = [
            os.path.join(self.project_root, "ableton_verify_*.png"),
            os.path.join(self.project_root, "ableton_monitor3_*.png"),
            os.path.join(self.project_root, "research_bot_capture_*.png"),
            os.path.join(self.project_root, "screenshots", "*.png"),
        ]

        for pattern in patterns:
            for filepath in glob.glob(pattern):
                if self._age_days(filepath) > max_age:
                    size = self._delete_file(filepath)
                    result["deleted_count"] += 1
                    result["freed_bytes"] += size
                    result["files"].append(filepath)

        return result

    def clean_logs(self):
        """Delete old root-level log/test files."""
        result = {"deleted_count": 0, "freed_bytes": 0, "files": []}
        max_age = self.max_log_age_days

        patterns = [
            os.path.join(self.project_root, "debug.log"),
            os.path.join(self.project_root, "test_results.log"),
            os.path.join(self.project_root, "test_output.txt"),
            os.path.join(self.project_root, "integration_test_*.txt"),
        ]

        for pattern in patterns:
            for filepath in glob.glob(pattern):
                if self._age_days(filepath) > max_age:
                    size = self._delete_file(filepath)
                    result["deleted_count"] += 1
                    result["freed_bytes"] += size
                    result["files"].append(filepath)

        return result

    def clean_crash_reports(self):
        """Delete the temp_crash_report/ directory if old enough."""
        result = {"deleted_count": 0, "freed_bytes": 0, "files": []}
        crash_dir = os.path.join(self.project_root, "temp_crash_report")

        if os.path.isdir(crash_dir):
            if self._age_days(crash_dir) > self.max_log_age_days:
                size = self._delete_dir(crash_dir)
                result["deleted_count"] += 1
                result["freed_bytes"] += size
                result["files"].append(crash_dir)

        return result

    def clean_pycache(self):
        """Delete __pycache__/ and .pytest_cache/ directories recursively."""
        result = {"deleted_count": 0, "freed_bytes": 0, "files": []}

        for dirpath, dirnames, _ in os.walk(self.project_root):
            for dirname in dirnames:
                if dirname in ("__pycache__", ".pytest_cache"):
                    full_path = os.path.join(dirpath, dirname)
                    size = self._delete_dir(full_path)
                    result["deleted_count"] += 1
                    result["freed_bytes"] += size
                    result["files"].append(full_path)

        return result

    def get_disk_usage(self):
        """Report disk usage per category. Returns {category: bytes, ..., total_bytes: int}."""
        usage = {}

        # Screenshots
        screenshot_bytes = 0
        for pattern in ["ableton_verify_*.png", "ableton_monitor3_*.png", "research_bot_capture_*.png"]:
            for f in glob.glob(os.path.join(self.project_root, pattern)):
                try:
                    screenshot_bytes += os.path.getsize(f)
                except OSError:
                    pass
        screenshots_dir = os.path.join(self.project_root, "screenshots")
        screenshot_bytes += self._dir_size(screenshots_dir)
        usage["screenshots"] = screenshot_bytes

        # Logs
        log_bytes = 0
        for pattern in ["debug.log", "test_results.log", "test_output.txt", "integration_test_*.txt"]:
            for f in glob.glob(os.path.join(self.project_root, pattern)):
                try:
                    log_bytes += os.path.getsize(f)
                except OSError:
                    pass
        usage["logs"] = log_bytes

        # Crash reports
        usage["crash_reports"] = self._dir_size(os.path.join(self.project_root, "temp_crash_report"))

        # Cache
        cache_bytes = 0
        for dirpath, dirnames, _ in os.walk(self.project_root):
            for dirname in dirnames:
                if dirname in ("__pycache__", ".pytest_cache"):
                    cache_bytes += self._dir_size(os.path.join(dirpath, dirname))
        usage["cache"] = cache_bytes

        usage["total_bytes"] = sum(usage.values())
        return usage

    def clean_all(self):
        """Run all cleanup methods. Returns combined summary."""
        results = {
            "screenshots": self.clean_screenshots(),
            "logs": self.clean_logs(),
            "crash_reports": self.clean_crash_reports(),
            "cache": self.clean_pycache(),
        }

        total_deleted = sum(r["deleted_count"] for r in results.values())
        total_freed = sum(r["freed_bytes"] for r in results.values())

        results["summary"] = {
            "total_deleted": total_deleted,
            "total_freed_bytes": total_freed,
            "total_freed_mb": round(total_freed / (1024 * 1024), 2),
            "dry_run": self.dry_run,
        }

        return results
