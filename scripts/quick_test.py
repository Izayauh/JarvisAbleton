from pythonosc.udp_client import SimpleUDPClient
import socket

print("Testing JarvisDeviceLoader...")
client = SimpleUDPClient("127.0.0.1", 11002)
client.send_message("/jarvis/test", [])

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.settimeout(3.0)
sock.bind(("127.0.0.1", 11003))

try:
    data, addr = sock.recvfrom(1024)
    print("JarvisDeviceLoader is responding!")
except socket.timeout:
    print("No response")
sock.close()

print("\nNow loading EQ Eight on track 1...")
client.send_message("/jarvis/device/load", [0, "EQ Eight"])

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.settimeout(10.0)
sock.bind(("127.0.0.1", 11003))

try:
    data, addr = sock.recvfrom(4096)
    print("Response:", data)
except socket.timeout:
    print("No response - check Ableton log")
sock.close()
