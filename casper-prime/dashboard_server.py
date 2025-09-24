
import http.server
import socketserver
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
os.chdir(str(BASE_DIR / "dashboard"))

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()
    
    def do_GET(self):
        if self.path == '/':
            self.path = '/working_dashboard.html'
        return super().do_GET()

PORT = 9318
with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
    print(f"Dashboard serving at http://localhost:{PORT}")
    httpd.serve_forever()
