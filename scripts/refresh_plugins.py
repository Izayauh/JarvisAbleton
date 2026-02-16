from pythonosc.udp_client import SimpleUDPClient
import socket

print("Requesting plugin refresh to trigger diagnostic logging...")
client = SimpleUDPClient("127.0.0.1", 11002)
client.send_message("/jarvis/plugins/refresh", [])

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.settimeout(15.0)
sock.bind(("127.0.0.1", 11003))

try:
    data, addr = sock.recvfrom(4096)
    print("Response:", data)
except socket.timeout:
    print("Timeout - check Ableton log for diagnostic output")
sock.close()
