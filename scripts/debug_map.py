from pythonosc.udp_client import SimpleUDPClient
import socket

print("Running Browser Map...")
client = SimpleUDPClient("127.0.0.1", 11002)
# Trigger the debug dump
client.send_message("/jarvis/debug/browser", [])

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.settimeout(5.0)
sock.bind(("127.0.0.1", 11003))

try:
    data, addr = sock.recvfrom(1024)
    print("Dump triggered successfully")
except:
    print("No response")
sock.close()