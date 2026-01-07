import socket

def check_mcp_status(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        res = s.connect_ex(('127.0.0.1', port))
        print(f"Port {port} result: {res}")
        return res == 0

print(f"8001: {check_mcp_status(8001)}")
print(f"8002: {check_mcp_status(8002)}")
