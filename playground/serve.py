#!/usr/bin/env python3
"""
Simple HTTP server for local playground testing.

Usage:
    python serve.py [port]

Default port is 8080. Open http://localhost:8080 in your browser.
"""

import http.server
import socketserver
import sys
import os
import webbrowser
from functools import partial

# Change to playground directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Get port from command line or use default
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

# Create handler with CORS headers
class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers for Pyodide
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        # Cross-origin isolation headers for SharedArrayBuffer (needed by some Pyodide features)
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        self.send_header('Cross-Origin-Embedder-Policy', 'require-corp')
        super().end_headers()

    def log_message(self, format, *args):
        # Color-coded logging
        status = args[1] if len(args) > 1 else ''
        if status.startswith('2'):
            color = '\033[92m'  # Green
        elif status.startswith('3'):
            color = '\033[93m'  # Yellow
        elif status.startswith('4') or status.startswith('5'):
            color = '\033[91m'  # Red
        else:
            color = '\033[0m'
        reset = '\033[0m'
        print(f"{color}{self.address_string()} - [{self.log_date_time_string()}] {format % args}{reset}")

# Run server
handler = CORSRequestHandler

with socketserver.TCPServer(("", PORT), handler) as httpd:
    url = f"http://localhost:{PORT}"
    print(f"\n[*] Quantum Playground Server")
    print(f"{'=' * 40}")
    print(f"[>] Serving from: {os.getcwd()}")
    print(f"[>] URL: {url}")
    print(f"{'=' * 40}")
    print(f"\nPress Ctrl+C to stop the server\n")

    # Try to open browser
    try:
        webbrowser.open(url)
    except:
        pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n[!] Server stopped")
        sys.exit(0)
