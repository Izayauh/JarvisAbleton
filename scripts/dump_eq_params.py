from pythonosc.udp_client import SimpleUDPClient
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer
import threading
import time

# Configuration
SEND_PORT = 11000  # To AbletonOSC
LISTEN_PORT = 11001 # From AbletonOSC (default reply port)
TRACK_IDX = 0
DEVICE_IDX = 0

received_params = {}
param_names = {}
param_values = {}

def handle_param_name(address, *args):
    # Address: /live/device/get/parameters/name
    # Args: (track_idx, device_idx, param_idx, name) OR list of names?
    # Actually, standard AbletonOSC usually sends individual messages or a bundle.
    # Let's handle the typical case: /live/device/param/name (track, device, param, name)
    # But the query is /get/parameters/name.
    # Let's just print what we get to reverse engineer the map.
    pass

def handle_any(address, *args):
    global param_names, param_values
    
    # Logic to parse parameter names
    # Expected format for name response: /live/device/param/name track device param index name
    if "name" in address and len(args) >= 3:
        try:
            p_idx = args[2]
            p_name = args[3]
            param_names[p_idx] = p_name
        except:
            pass
            
    # Logic to parse values
    # Expected format: /live/device/param/value track device param index value
    if "value" in address and "parameter" in address and len(args) >= 3:
        try:
            p_idx = args[2]
            p_val = args[3]
            param_values[p_idx] = p_val
        except:
            pass

def start_server():
    dispatcher = Dispatcher()
    dispatcher.set_default_handler(handle_any)
    
    server = BlockingOSCUDPServer(("127.0.0.1", LISTEN_PORT), dispatcher)
    print(f"Listening on {LISTEN_PORT}...")
    return server

def dump_map():
    # Start server in thread
    server = start_server()
    st = threading.Thread(target=server.serve_forever)
    st.daemon = True
    st.start()

    client = SimpleUDPClient("127.0.0.1", SEND_PORT)
    
    print("Querying EQ Eight parameters...")
    # Request names and values for range 50-80
    for i in range(50, 80):
        client.send_message("/live/device/get/parameter/name", [TRACK_IDX, DEVICE_IDX, i])
        client.send_message("/live/device/get/parameter/value", [TRACK_IDX, DEVICE_IDX, i])
        time.sleep(0.01) # fast burst
        
    print("Waiting for replies (3s)...")
    time.sleep(3)
    
    print("\n--- EQ Eight Parameter Map ---")
    sorted_indices = sorted(list(set(list(param_names.keys()) + list(param_values.keys()))))
    
    for idx in sorted_indices:
        name = param_names.get(idx, "Unknown")
        val = param_values.get(idx, "?")
        print(f"Param {idx}: {name} = {val}")

    server.shutdown()

if __name__ == "__main__":
    dump_map()
