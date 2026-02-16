#!/usr/bin/env python3
"""
Log Viewer Script

A utility script to view and tail the Jarvis log files.
Provides convenient access to recent log entries for debugging and transparency.

Usage:
    # View last 50 lines
    python scripts/view_logs.py

    # View last 100 lines
    python scripts/view_logs.py -n 100

    # View all logs
    python scripts/view_logs.py --all

    # Follow logs in real-time (tail -f mode)
    python scripts/view_logs.py --follow

    # Filter by log level
    python scripts/view_logs.py --level ERROR
    python scripts/view_logs.py --level DEBUG

    # Search for specific text
    python scripts/view_logs.py --search "plugin_chain"
"""

import os
import sys
import argparse
import time
from pathlib import Path


def get_log_file_path():
    """Get the path to the main log file"""
    project_root = Path(__file__).parent.parent
    log_file = project_root / "logs" / "jarvis.log"
    return log_file


def tail_file(file_path, num_lines=50):
    """Read the last N lines from a file"""
    if not file_path.exists():
        print(f"Log file not found: {file_path}")
        print("Run Jarvis to generate logs.")
        return []

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    if num_lines == -1:
        return lines
    else:
        return lines[-num_lines:]


def follow_file(file_path):
    """Follow a file in real-time (like tail -f)"""
    if not file_path.exists():
        print(f"Log file not found: {file_path}")
        print("Waiting for log file to be created...")
        while not file_path.exists():
            time.sleep(1)

    print(f"Following {file_path} (Ctrl+C to stop)")
    print("=" * 80)

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        # Seek to end
        f.seek(0, 2)

        try:
            while True:
                line = f.readline()
                if line:
                    print(line, end='')
                else:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nStopped following logs.")


def filter_by_level(lines, level):
    """Filter log lines by level"""
    level = level.upper()
    filtered = []

    for line in lines:
        if f" - {level} - " in line:
            filtered.append(line)

    return filtered


def search_logs(lines, search_term):
    """Search for specific text in logs"""
    search_term = search_term.lower()
    results = []

    for line in lines:
        if search_term in line.lower():
            results.append(line)

    return results


def print_lines(lines, highlight_errors=True):
    """Print log lines with optional highlighting"""
    for line in lines:
        # Handle encoding issues on Windows
        try:
            # Add simple highlighting for errors and warnings
            if highlight_errors:
                if " - ERROR - " in line or "❌" in line:
                    # Red for errors
                    print(f"\033[91m{line}\033[0m", end='')
                elif " - WARNING - " in line or "[WARN]" in line:
                    # Yellow for warnings
                    print(f"\033[93m{line}\033[0m", end='')
                elif " - DEBUG - " in line or "[DBG]" in line:
                    # Gray for debug
                    print(f"\033[90m{line}\033[0m", end='')
                else:
                    print(line, end='')
            else:
                print(line, end='')
        except UnicodeEncodeError:
            # Fallback for Windows console encoding issues
            # Replace problematic unicode characters
            safe_line = line.encode('ascii', errors='replace').decode('ascii')
            print(safe_line, end='')


def main():
    parser = argparse.ArgumentParser(
        description="View Jarvis log files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # View last 50 lines
  %(prog)s -n 100             # View last 100 lines
  %(prog)s --all              # View all logs
  %(prog)s --follow           # Follow logs in real-time
  %(prog)s --level ERROR      # Show only ERROR logs
  %(prog)s --search "plugin"  # Search for "plugin" in logs
        """
    )

    parser.add_argument(
        '-n', '--lines',
        type=int,
        default=50,
        help='Number of lines to display (default: 50)'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Display all log lines'
    )

    parser.add_argument(
        '--follow', '-f',
        action='store_true',
        help='Follow log file in real-time (like tail -f)'
    )

    parser.add_argument(
        '--level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Filter by log level'
    )

    parser.add_argument(
        '--search',
        type=str,
        help='Search for specific text in logs'
    )

    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable color highlighting'
    )

    args = parser.parse_args()

    log_file = get_log_file_path()

    # Follow mode
    if args.follow:
        follow_file(log_file)
        return

    # Read logs
    num_lines = -1 if args.all else args.lines
    lines = tail_file(log_file, num_lines)

    if not lines:
        return

    # Apply filters
    if args.level:
        lines = filter_by_level(lines, args.level)

    if args.search:
        lines = search_logs(lines, args.search)

    # Display results
    if not lines:
        print("No matching log entries found.")
        return

    print(f"Showing {len(lines)} log entries from {log_file}")
    print("=" * 80)
    print_lines(lines, highlight_errors=not args.no_color)

    # Summary
    if len(lines) > 0:
        print("=" * 80)
        print(f"Total entries shown: {len(lines)}")


if __name__ == "__main__":
    main()
