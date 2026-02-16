from pythonosc.udp_client import SimpleUDPClient
import time
import mss
import mss.tools
import os

def refine_eqs():
    client = SimpleUDPClient("127.0.0.1", 11000)
    
    print("--- REFINING EQ SETTINGS ---")
    
    # --- EQ 1 (Index 0): Subtractive / Cleanup ---
    # Goal: High Pass (Low Cut) @ 100Hz to remove mud
    print("Configuring EQ 1 (Subtractive): Low Cut @ 100Hz")
    
    # Band 1 On (Param 4) -> 1.0 (On)
    client.send_message("/live/device/set/parameter/value", [0, 0, 4, 1.0])
    
    # Band 1 Type (Param 5) -> 0.0 (Low Cut / High Pass)
    # Note: 0.0 is typically the Low Cut filter shape
    client.send_message("/live/device/set/parameter/value", [0, 0, 5, 0.0])
    
    # Band 1 Freq (Param 6) -> 100Hz
    # Mapping: In AbletonOSC, parameters often take 0.0-1.0 normalized range.
    # 100Hz is roughly 0.22 in the log scale (20Hz-20kHz)
    client.send_message("/live/device/set/parameter/value", [0, 0, 6, 0.22])
    
    # Band 1 Q (Param 8) -> 0.71 (Standard Butterworth slope)
    # Normalized 0.0-1.0. 0.4-0.5 is usually standard Q (0.71)
    client.send_message("/live/device/set/parameter/value", [0, 0, 8, 0.45])

    time.sleep(0.2)

    # --- EQ 2 (Index 1): Additive / Shine ---
    # Goal: High Shelf boost @ 7kHz (Slight)
    print("Configuring EQ 2 (Additive): High Shelf Boost @ 7kHz")
    
    # Band 4 On (Param 34) -> 1.0 (On)
    client.send_message("/live/device/set/parameter/value", [0, 1, 34, 1.0])
    
    # Band 4 Type (Param 35) -> High Shelf
    # Correct EQ Eight types: 0=LP48, 1=LP24, 2=LP12, 3=Notch, 4=HP12, 5=HP24, 6=HP48, 7=Bell, 8=LowShelf, 9=HighShelf
    # High Shelf = 9
    client.send_message("/live/device/set/parameter/value", [0, 1, 35, 9.0])
    
    # Band 4 Freq (Param 36) -> 7kHz
    # 7kHz is in the upper registers.
    # If 0.8 was ~10k, let's try 0.75
    client.send_message("/live/device/set/parameter/value", [0, 1, 36, 0.75])
    
    # Band 4 Gain (Param 37) -> Slight Boost (+2dB)
    # Assuming normalized 0.0-1.0 where 0.5 is 0dB.
    # 1.0 = +15dB. 0.5 = 0dB.
    # We want +2-3dB. That's about 10-20% of the boost range.
    # Try 0.58
    client.send_message("/live/device/set/parameter/value", [0, 1, 37, 0.58])

    print("Settings sent. Capturing proof...")
    time.sleep(1.0) # Wait for UI update
    
    # Capture Monitor 3
    with mss.mss() as sct:
        monitors = sct.monitors
        if len(monitors) > 3:
            # Monitor 3 is index 3
            monitor = monitors[3]
            filename = f"ableton_precision_{int(time.time())}.png"
            filepath = os.path.join(os.getcwd(), filename)
            
            sct_img = sct.grab(monitor)
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=filepath)
            
            print(f"WSL_PATH: {filepath.replace('C:\\', '/mnt/c/').replace('\\', '/')}")
        else:
            print("Error: Monitor 3 not found in list.")

if __name__ == "__main__":
    refine_eqs()
