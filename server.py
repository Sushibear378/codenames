# server.py (run this on your computer)
import socket
import threading

def handle_client(conn, addr):
    data = conn.recv(1024)
    print(f"Received from {addr}: {data.decode()}")
    conn.sendall(b"ACK from server")
    conn.close()

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('10.97.36.101', 5000))  # Listen on all interfaces
server.listen(4)

print("Server listening...")
for _ in range(4):
    conn, addr = server.accept()
    threading.Thread(target=handle_client, args=(conn, addr)).start()
    #ai slop