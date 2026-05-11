# client.py (run this on each client device)
import socket

server_ip = '10.97.36.101'  # e.g., '192.168.1.100'
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((server_ip, 5000))
client.sendall(b'Hello from client')
result = client.recv(1024)
print(result.decode())
client.close()