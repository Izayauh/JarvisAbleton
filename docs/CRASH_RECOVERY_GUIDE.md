# Ableton Crash Recovery System

## Overview

The JarvisAbleton crash recovery system automatically detects when Ableton Live crashes during automated tests and automatically restarts it, handles recovery dialogs, and resumes testing. This makes long-running tests much more robust and reliable.

## Features

✅ **Automatic Crash Detection** - Detects OSC connection errors and process termination  
✅ **Automatic Ableton Restart** - Launches Ableton when crashes are detected  
✅ **Recovery Dialog Handling** - Automatically clicks "Yes" on "Recover Work?" dialogs  
✅ **Test Resumption** - Tests continue automatically after recovery  
✅ **Improved Device Deletion** - Enhanced timing prevents crashes during device deletion  

## Installation

Install the required dependencies:

```powershell
pip install -r requirements_crash_recovery.txt
```

This installs:
- `psutil` - Process management and monitoring
- `pyautogui` - GUI automation for recovery dialogs
- `pygetwindow` - Window management

## Usage

### Running Tests with Crash Recovery

The enhanced test system is **enabled by default**:

```powershell
# Run with crash recovery (default)
python tests/run_incremental_test.py

# Run with crash recovery and diagnostics
python tests/run_incremental_test.py --diagnose

# Disable crash recovery
python tests/run_incremental_test.py --no-recovery

# Strict mode (fail on errors) with crash recovery
python tests/run_incremental_test.py --strict
```

### What Happens During a Crash

1. **Detection** - System detects:
   - OSC error: `[WinError 10054] Connection forcibly closed`
   - No response from Ableton
   - Process termination

2. **Recovery** - System automatically:
   - Logs the crash with timestamp
   - Force closes any remaining Ableton processes
   - Relaunches Ableton Live
   - Waits for full startup (15-20 seconds)
   - Looks for recovery dialog

3. **Dialog Handling** - If "Recover Work?" appears:
   - Finds the dialog window
   - Activates it
   - Presses Enter (accepts "Yes")
   - Waits for recovery to complete

4. **Resumption** - System continues:
   - Verifies OSC connection
   - Retries the failed operation
   - Continues with remaining tests

### Example Output

```
💥 [CRASH] CRASH DETECTED (attempt 1/3)
ℹ️ [INFO] Attempting to restart Ableton...
ℹ️ [INFO] Closing existing Ableton instance (PID: 12345)...
✅ [OK] Ableton closed successfully
ℹ️ [INFO] Launching Ableton Live...
✅ [OK] Ableton process started (PID: 12346)
ℹ️ [INFO] Waiting 15.0s for Ableton to fully load...
✅ [OK] Ableton should be ready
ℹ️ [INFO] Looking for recovery dialog...
✅ [OK] Sent Enter to accept recovery
ℹ️ [INFO] Testing OSC connection...
✅ [OK] OSC connection OK (device count: 0)
✅ [OK] Recovery successful!
```

## Configuration

### Ableton Process Manager

Configure in code or when initializing:

```python
from ableton_controls.process_manager import get_ableton_manager

manager = get_ableton_manager(
    ableton_path="C:/Program Files/Ableton/Live 11/Program/Ableton Live 11.exe",  # Auto-detected if None
    project_path="C:/path/to/project.als",  # Optional project to open
    startup_wait=15.0,  # Seconds to wait after launching
    recovery_action="yes",  # "yes", "no", or "ask" - default action for crash dialog
    verbose=True  # Print status messages
)

# Close Ableton (graceful, then force)
manager.close_ableton(force=True)

# Open Ableton with a project
manager.launch_ableton(project_path="my_song.als")

# Handle recovery dialog with No (start fresh)
manager.handle_recovery_dialog(reopen_project=False)
```

You can also use the convenience methods on the controller:

```python
from ableton_controls import ableton

ableton.open_ableton(project_path="song.als")
ableton.close_ableton(force=True)
ableton.restart_ableton(reopen_project=False, force_kill=True)
```

### Crash Detector

Configure crash recovery behavior:

```python
from ableton_controls.process_manager import get_ableton_manager  # process control
from tests.crash_resilient_wrapper import get_crash_detector

detector = get_crash_detector(
    auto_recover=True,  # Automatically restart on crash
    max_recovery_attempts=3,  # Maximum recovery attempts
    recovery_wait=20.0,  # Seconds to wait after recovery
    verbose=True  # Print status messages
)
```

### Device Deletion Timing

Improved timing in `chain_test_utils.py` prevents crashes:

```python
# Gentle mode (default) - Slower but safer
clear_track_devices(track_index, reliable, gentle=True)

# Timings in gentle mode:
- delete_delay = 1.2s      # Between each device deletion
- verify_delay = 2.0s      # After deletion round
- batch_size = 2           # Devices per batch
- batch_pause = 2.5s       # After each batch
- Special 3s pause before final device (index 0)
```

## Architecture

### Components

1. **AbletonProcessManager** (`ableton_controls/process_manager.py`)
   - Process detection and monitoring
   - Launch, close (graceful + force), and restart capabilities
   - Recovery dialog handling with Yes/No choice
   - Configurable default via `recovery_action` ("yes", "no", "ask")
   - Backward-compat stub at `tests/ableton_process_manager.py`

2. **AbletonController** (`ableton_controls/controller.py`)
   - Convenience methods: `open_ableton()`, `close_ableton()`, `restart_ableton()`
   - Delegates to process manager singleton

3. **AbletonCrashDetector** (`tests/crash_resilient_wrapper.py`)
   - Error pattern detection
   - Automatic recovery orchestration
   - Operation retry logic

3. **Enhanced Tests** (`tests/run_incremental_test.py`)
   - Integrated crash recovery
   - Crash-aware device clearing
   - Resilient test execution

### Crash Detection Patterns

The system detects these error patterns:

```python
CRASH_INDICATORS = [
    "WinError 10054",  # Connection forcibly closed
    "WinError 10061",  # Connection refused
    "Connection refused",
    "No response from Ableton",
    "OSC error",
    "Timeout: No response",
]
```

## Troubleshooting

### Recovery Dialog Not Handled

**Symptom:** Ableton restarts but recovery dialog stays open

**Solutions:**
1. Ensure `pyautogui` and `pygetwindow` are installed
2. Check if antivirus is blocking GUI automation
3. Manually click "Yes" - test will continue
4. Increase recovery wait time

### Ableton Not Auto-Detected

**Symptom:** `Ableton path not found` error

**Solutions:**
1. Manually specify path:
   ```python
   manager = get_ableton_manager(
       ableton_path="C:/Your/Custom/Path/Ableton Live 11.exe"
   )
   ```
2. Check common installation paths:
   - `C:\ProgramData\Ableton\Live 11 Suite\Program\`
   - `C:\Program Files\Ableton\Live 11\Program\`

### Crash Loop (Multiple Crashes)

**Symptom:** Ableton keeps crashing repeatedly

**Solutions:**
1. Check Ableton's Log.txt for underlying issues
2. Verify Remote Scripts are installed correctly
3. Try restarting computer
4. Disable plugins that might be causing issues
5. Run with `--no-recovery` and fix underlying problem

### Process Not Detected

**Symptom:** `Ableton is not running` but it is

**Solutions:**
1. Check Task Manager for `Ableton Live` process
2. Restart Ableton manually
3. Check if running as different user
4. Process name might be different - check `psutil.process_iter()`

## Known Limitations

1. **Recovery dialog timing** - If Ableton shows the dialog immediately, it might be missed. The system waits 10 seconds for it to appear.

2. **Project-specific settings** - Recovered project might have different settings than a fresh start.

3. **Plugin state** - Some plugins might not recover their state correctly.

4. **Windows only** - Current implementation is Windows-specific. Mac/Linux need different approaches.

## Advanced Usage

### Decorating Functions with Crash Recovery

Wrap your own functions with crash recovery:

```python
from ableton_controls.process_manager import get_ableton_manager  # process control
from tests.crash_resilient_wrapper import with_crash_recovery

@with_crash_recovery("my_operation")
def load_many_devices(track_index, device_list):
    for device in device_list:
        # ... load device ...
    return result
```

### Manual Recovery

Manually trigger recovery:

```python
from ableton_controls.process_manager import get_ableton_manager
from tests.crash_resilient_wrapper import get_crash_detector

detector = get_crash_detector()

if detector.detect_crash():
    success = detector.recover_from_crash()
    if success:
        # Continue operations
    else:
        # Handle failure
```

### Checking Ableton Status

```python
from ableton_controls.process_manager import get_ableton_manager

manager = get_ableton_manager()

# Check if running
is_running, pid = manager.is_ableton_running()
print(f"Running: {is_running}, PID: {pid}")

# Get process object
process = manager.get_ableton_process()
if process:
    print(f"Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB")
```

## Performance Impact

- **Normal operation**: Minimal overhead, just process monitoring
- **During crash**: 20-30 seconds recovery time
- **Recovery overhead**: ~1-2% of total test time for stable systems
- **Heavy crash scenarios**: Can save hours of manual intervention

## Best Practices

1. **Always use gentle mode** for device deletion
2. **Enable crash recovery** for long-running tests
3. **Check logs** after tests to see if crashes occurred
4. **Monitor patterns** - frequent crashes indicate underlying issues
5. **Keep Ableton updated** to avoid known bugs
6. **Test with recovery disabled** first to find root causes

## Contributing

To improve crash detection:

1. Add new error patterns to `CRASH_INDICATORS`
2. Improve recovery dialog detection
3. Add support for other OSes
4. Enhance timing heuristics

## Support

If you encounter issues:

1. Run with `--diagnose` flag
2. Check `tests/logs/` for detailed logs
3. Review Ableton's `Log.txt`
4. Report crash patterns not being detected
5. Share recovery scenarios that don't work

## Future Enhancements

- [ ] Mac/Linux support
- [x] Configurable recovery dialog strategies (Yes/No/Ask via `recovery_action`)
- [x] Process control from AbletonController (open/close/restart)
- [ ] Automatic crash log collection
- [ ] Crash pattern learning
- [ ] Recovery strategy selection based on error type
- [ ] Integration with CI/CD pipelines
- [ ] Crash statistics and reporting

