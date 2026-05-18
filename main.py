python
import sys

def run_server():
    # Placeholder for server logic
    print("Server started. Waiting for clients...")

def run_client():
    # Placeholder for client logic
    server_ip = sys.stdin.readline().strip()
    print(f"Client started. Connecting to server at {server_ip}...")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        from ui import CodenamesUI
        ui = CodenamesUI()
        ui.run()
    elif sys.argv[1] == "server":
        run_server()
    elif sys.argv[1] == "client":
        run_client()
    else:
        print("Unknown argument.")