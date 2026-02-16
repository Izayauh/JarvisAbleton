import mss
import mss.tools
import os
import time
import sys

# Fix console output
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', 'replace').decode())

def capture_all_monitors():
    safe_print("--- MSS MULTI-MONITOR CAPTURE ---")
    
    with mss.mss() as sct:
        monitors = sct.monitors
        safe_print(f"Detected {len(monitors)-1} monitors (plus 'all' composite).")
        
        timestamp = int(time.time())
        saved_files = []
        
        # Monitor 0 is "All monitors combined".
        # Monitor 1, 2, 3... are specific displays.
        for i, monitor in enumerate(monitors):
            if i == 0: continue # Skip the composite view for now
            
            safe_print(f"Capturing Monitor {i}: {monitor}")
            
            filename = f"monitor_{i}_{timestamp}.png"
            filepath = os.path.join(os.getcwd(), filename)
            
            # Capture
            sct_img = sct.grab(monitor)
            
            # Save to file
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=filepath)
            
            wsl_path = filepath.replace("C:\\", "/mnt/c/").replace("\\", "/")
            safe_print(f"   -> Saved: {wsl_path}")
            saved_files.append(wsl_path)
            
    return saved_files

if __name__ == "__main__":
    capture_all_monitors()
