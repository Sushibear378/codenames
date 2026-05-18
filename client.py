# client.py
import socket

server_ip = '10.97.36.101'
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((server_ip, 5000))
client.sendall('Hello from client'.encode())  # encode to bytes
result = client.recv(1024)
print(result.decode())
client.close()