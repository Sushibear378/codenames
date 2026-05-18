# main.py
import sys
from login import assign_role_color
import socket

from ui import StartingScreenUI

def start_server():
    assignments = assign_role_color()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('10.97.36.101', 5000))
    server.listen(3)
    print("Server listening...")
    for i in range(1, 4):
        conn, addr = server.accept()
        print(f"Client {i} connected: {addr}")
        role, color = assignments[f'client_{i}']
        conn.sendall(f"{role},{color}".encode())
        conn.close()
    server_role, server_color = assignments['server']
    return server_role, server_color

def start_client():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(('10.97.36.101', 5000))
    data = client.recv(1024).decode()
    role, color = data.split(',')
    client.close()
    return role, color

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        role, color = start_server()
        StartingScreenUI(role,color)
    else:
        role, color = start_client()
        StartingScreenUI(role,color)