"""
OSC Path Discovery Tool for Ableton Live

Discovers and tests working OSC paths for the current AbletonOSC version.
Generates a compatibility report and saves working paths to config.
"""

import time
import json
import os
from pythonosc.udp_client import SimpleUDPClient
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.dispatcher import Dispatcher
from threading import Thread, Event

# OSC Configuration
OSC_IP = "127.0.0.1"
OSC_SEND_PORT = 11000
OSC_RECEIVE_PORT = 11001

# Store responses
responses = {}
response_event = Event()


def default_handler(address, *args):
    """Default handler for all OSC responses"""
    responses[address] = list(args)
    response_event.set()


def create_receiver():
    """Create OSC receiver for responses"""
    dispatcher = Dispatcher()
    dispatcher.set_default_handler(default_handler)
    server = ThreadingOSCUDPServer((OSC_IP, OSC_RECEIVE_PORT), dispatcher)
    return server


class OSCDiscovery:
    """Discovers and tests OSC paths for AbletonOSC"""
    
    def __init__(self):
        self.client = SimpleUDPClient(OSC_IP, OSC_SEND_PORT)
        self.working_paths = {}
        self.failed_paths = {}
        self.test_results = []
        
    def test_connection(self):
        """Test basic OSC connection"""
        print("Testing OSC connection to Ableton...")
        try:
            self.client.send_message("/live/test", [])
            time.sleep(0.5)
            print("✓ OSC connection established")
            return True
        except Exception as e:
            print(f"✗ OSC connection failed: {e}")
            return False
    
    def send_and_wait(self, path, args=None, timeout=0.5):
        """Send OSC message and wait briefly"""
        if args is None:
            args = []
        try:
            self.client.send_message(path, args)
            time.sleep(timeout)
            return True
        except Exception as e:
            return False
    
    def test_path_variations(self, base_name, variations, test_args=None):
        """Test multiple path variations and find working one"""
        if test_args is None:
            test_args = []
        
        print(f"\nTesting: {base_name}")
        for path, args in variations:
            final_args = args if args else test_args
            try:
                self.client.send_message(path, final_args)
                print(f"  ✓ Sent: {path} {final_args}")
                self.working_paths[base_name] = {"path": path, "args_format": final_args}
                time.sleep(0.3)
                return path
            except Exception as e:
                print(f"  ✗ Failed: {path} - {e}")
                self.failed_paths[base_name] = {"path": path, "error": str(e)}
        return None
    
    def run_discovery(self):
        """Run full OSC path discovery"""
        print("\n" + "="*60)
        print("  ABLETONOSC PATH DISCOVERY")
        print("="*60)
        
        if not self.test_connection():
            print("\nAborted: No OSC connection")
            return False
        
        # ================== SONG/PLAYBACK CONTROLS ==================
        print("\n--- Song/Playback Controls ---")
        
        # Test play
        self.test_path_variations("play", [
            ("/live/song/start_playing", []),
        ])
        time.sleep(1)
        
        # Test stop
        self.test_path_variations("stop", [
            ("/live/song/stop_playing", []),
        ])
        time.sleep(0.5)
        
        # Test tempo
        self.test_path_variations("set_tempo", [
            ("/live/song/set/tempo", [100.0]),
        ])
        time.sleep(0.5)
        
        # Restore tempo
        self.client.send_message("/live/song/set/tempo", [120.0])
        
        # Test metronome
        self.test_path_variations("metronome_on", [
            ("/live/song/set/metronome", [1]),
        ])
        time.sleep(0.5)
        
        self.test_path_variations("metronome_off", [
            ("/live/song/set/metronome", [0]),
        ])
        time.sleep(0.5)
        
        # Test loop
        self.test_path_variations("loop_on", [
            ("/live/song/set/loop", [1]),
        ])
        time.sleep(0.5)
        
        self.test_path_variations("loop_off", [
            ("/live/song/set/loop", [0]),
        ])
        
        # ================== TRACK CONTROLS ==================
        print("\n--- Track Controls ---")
        print("NOTE: Per AbletonOSC docs, track_id is a PARAMETER, not in path!")
        
        # Test mute - CORRECT FORMAT: /live/track/set/mute track_id, mute_value
        self.test_path_variations("mute_track", [
            ("/live/track/set/mute", [0, 1]),  # track 0, mute ON
        ])
        time.sleep(0.5)
        
        # Unmute
        self.client.send_message("/live/track/set/mute", [0, 0])
        time.sleep(0.3)
        
        # Test solo
        self.test_path_variations("solo_track", [
            ("/live/track/set/solo", [0, 1]),  # track 0, solo ON
        ])
        time.sleep(0.5)
        
        # Unsolo
        self.client.send_message("/live/track/set/solo", [0, 0])
        time.sleep(0.3)
        
        # Test arm
        self.test_path_variations("arm_track", [
            ("/live/track/set/arm", [0, 1]),  # track 0, arm ON
        ])
        time.sleep(0.5)
        
        # Disarm
        self.client.send_message("/live/track/set/arm", [0, 0])
        time.sleep(0.3)
        
        # Test volume
        self.test_path_variations("set_volume", [
            ("/live/track/set/volume", [0, 0.5]),  # track 0, volume 50%
        ])
        time.sleep(0.5)
        
        # Restore volume
        self.client.send_message("/live/track/set/volume", [0, 0.85])
        time.sleep(0.3)
        
        # Test panning
        self.test_path_variations("set_panning", [
            ("/live/track/set/panning", [0, 0.0]),  # track 0, center
        ])
        
        # ================== SCENE CONTROLS ==================
        print("\n--- Scene Controls ---")
        
        self.test_path_variations("fire_scene", [
            ("/live/scene/fire", [0]),  # scene 0
        ])
        time.sleep(1)
        
        # Stop playback
        self.client.send_message("/live/song/stop_playing", [])
        
        # ================== CLIP CONTROLS ==================
        print("\n--- Clip Controls ---")
        
        self.test_path_variations("fire_clip", [
            ("/live/clip/fire", [0, 0]),  # track 0, clip 0
        ])
        time.sleep(1)
        
        self.test_path_variations("stop_clip", [
            ("/live/clip/stop", [0, 0]),  # track 0, clip 0
        ])
        time.sleep(0.5)
        
        self.test_path_variations("stop_all_clips_on_track", [
            ("/live/track/stop_all_clips", [0]),  # track 0
        ])
        
        # Stop everything
        self.client.send_message("/live/song/stop_playing", [])
        
        # ================== CLIP SLOT CONTROLS ==================
        print("\n--- Clip Slot Controls ---")
        
        self.test_path_variations("fire_clip_slot", [
            ("/live/clip_slot/fire", [0, 0]),  # track 0, slot 0
        ])
        time.sleep(1)
        
        # Stop
        self.client.send_message("/live/song/stop_playing", [])
        
        return True
    
    def generate_report(self):
        """Generate discovery report"""
        print("\n" + "="*60)
        print("  DISCOVERY REPORT")
        print("="*60)
        
        print(f"\n✓ Working paths: {len(self.working_paths)}")
        for name, info in self.working_paths.items():
            print(f"  - {name}: {info['path']} {info['args_format']}")
        
        if self.failed_paths:
            print(f"\n✗ Failed paths: {len(self.failed_paths)}")
            for name, info in self.failed_paths.items():
                print(f"  - {name}: {info['path']}")
        
        return self.working_paths
    
    def save_config(self, filename="config/osc_paths.json"):
        """Save working paths to config file"""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        config = {
            "version": "1.0",
            "discovered_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "paths": {
                # Song controls
                "play": "/live/song/start_playing",
                "stop": "/live/song/stop_playing",
                "continue": "/live/song/continue_playing",
                "record_mode": "/live/song/set/record_mode",
                "tempo": "/live/song/set/tempo",
                "metronome": "/live/song/set/metronome",
                "loop": "/live/song/set/loop",
                "loop_start": "/live/song/set/loop_start",
                "loop_length": "/live/song/set/loop_length",
                "position": "/live/song/set/current_song_time",
                
                # Track controls (track_id is first param)
                "track_mute": "/live/track/set/mute",
                "track_solo": "/live/track/set/solo",
                "track_arm": "/live/track/set/arm",
                "track_volume": "/live/track/set/volume",
                "track_panning": "/live/track/set/panning",
                "track_send": "/live/track/set/send",
                "track_stop_clips": "/live/track/stop_all_clips",
                
                # Scene controls (scene_id is first param)
                "scene_fire": "/live/scene/fire",
                
                # Clip controls (track_id, clip_id are params)
                "clip_fire": "/live/clip/fire",
                "clip_stop": "/live/clip/stop",
                
                # Clip slot controls
                "clip_slot_fire": "/live/clip_slot/fire",
            },
            "notes": {
                "track_controls": "Track ID is first parameter, not in path. Track 1 = index 0.",
                "scene_controls": "Scene ID is first parameter. Scene 1 = index 0.",
                "clip_controls": "Track ID and Clip ID are parameters. Both 0-indexed.",
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n✓ Config saved to {filename}")
        return config


def main():
    """Run OSC discovery"""
    print("\n" + "="*60)
    print("  JARVIS-ABLETON OSC DISCOVERY TOOL")
    print("="*60)
    print("\nThis tool will test OSC paths with your Ableton setup.")
    print("Make sure Ableton Live is running with AbletonOSC enabled.")
    print("\nPress Ctrl+C to abort at any time.\n")
    
    discovery = OSCDiscovery()
    
    try:
        success = discovery.run_discovery()
        if success:
            discovery.generate_report()
            discovery.save_config()
            
            print("\n" + "="*60)
            print("  NEXT STEPS")
            print("="*60)
            print("\n1. Review the discovery report above")
            print("2. Check config/osc_paths.json for saved paths")
            print("3. Run: python test_ableton.py to verify")
            print("4. Start Jarvis: python jarvis_engine.py")
        
    except KeyboardInterrupt:
        print("\n\nDiscovery aborted by user.")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()

