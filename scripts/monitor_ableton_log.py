"""
Real-time Ableton Log Monitor

Monitors Ableton's Log.txt file and displays new entries in real-time,
especially focusing on JarvisDeviceLoader messages.
"""

import time
import os
from pathlib import Path

LOG_PATH = r"C:\Users\isaia\AppData\Roaming\Ableton\Live 11.3.43\Preferences\Log.txt"

def tail_file(filepath, interval=0.5):
    """
    Continuously monitor a file for new lines

    Args:
        filepath: Path to the log file
        interval: How often to check for new lines (seconds)
    """
    # Get initial file size
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        # Seek to end of file
        f.seek(0, 2)

        print("="*80)
        print("MONITORING ABLETON LOG")
        print(f"File: {filepath}")
        print("="*80)
        print("\nWaiting for new log entries...")
        print("(Focus on JarvisDeviceLoader, plugin loading, and errors)\n")

        while True:
            try:
                # Read new lines
                line = f.readline()

                if line:
                    # Check if it's a relevant line
                    lower = line.lower()
                    if any(keyword in lower for keyword in ['jarvis', 'plugin', 'device', 'error', 'exception', 'failed', 'load']):
                        # Highlight important lines
                        if 'error' in lower or 'exception' in lower or 'failed' in lower:
                            print(f"\n[ERROR] {line.strip()}")
                        elif 'jarvis' in lower:
                            print(f"\n[JARVIS] {line.strip()}")
                        elif 'load' in lower or 'device' in lower:
                            print(f"[INFO] {line.strip()}")
                        else:
                            print(line.strip())
                else:
                    # No new line, wait a bit
                    time.sleep(interval)

            except KeyboardInterrupt:
                print("\n\nStopping log monitor...")
                break
            except Exception as e:
                print(f"\nError reading log: {e}")
                time.sleep(interval)

if __name__ == "__main__":
    if not os.path.exists(LOG_PATH):
        print(f"ERROR: Log file not found at {LOG_PATH}")
        print("\nPlease update LOG_PATH in this script to match your Ableton log location.")
    else:
        try:
            tail_file(LOG_PATH)
        except Exception as e:
            print(f"Error: {e}")
