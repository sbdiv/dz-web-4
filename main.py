from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
from pathlib import Path
import mimetypes
import logging
import socket
import json
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
BUFFER_SIZE = 1024
HTTP_PORT = 3000
HTTP_HOST = '0.0.0.0'
SOCKET_HOST = '127.0.0.1'
SOCKET_PORT = 5000
DATA_FILE = BASE_DIR / 'storage' / 'data.json'

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        route_path = parsed_url.path

        if route_path == '/':
            self.send_html_response('index.html')
        elif route_path == '/message':
            self.send_html_response('message.html')
        else:
            static_file_path = BASE_DIR.joinpath('static', route_path[1:])
            if static_file_path.exists():
                self.send_static_response(static_file_path)
            else:
                self.send_html_response('error.html', status_code=404)

    def send_html_response(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()

        with open(filename, 'rb') as file:
            self.wfile.write(file.read())

    def send_static_response(self, filename, status_code=200):
        self.send_response(status_code)
        mime_type, _ = mimetypes.guess_type(filename)

        if mime_type:
            self.send_header('Content-Type', mime_type)
        else:
            self.send_header('Content-Type', 'text/plain')

        self.end_headers()

        with open(filename, 'rb') as file:
            self.wfile.write(file.read())

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length'))
        post_data = self.rfile.read(content_length).decode('utf-8')
        parsed_post_data = urllib.parse.parse_qs(post_data)

        username = parsed_post_data.get('username', [''])[0]
        message = parsed_post_data.get('message', [''])[0]

        if username and message:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            entry = {timestamp: {"username": username, "message": message}}

            with open(DATA_FILE, 'a+') as json_file:
                json.dump(entry, json_file, indent=2)
                json_file.write('\n')

            socket_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            socket_client.sendto(post_data.encode('utf-8'), (SOCKET_HOST, SOCKET_PORT))
            socket_client.close()

            self.send_response(302)
            self.send_header('Location', '/message')
            self.end_headers()
        else:
            self.send_html_response('error.html', status_code=400)

def run_http_server(host, port):
    server_address = (host, port)
    http_server = HTTPServer(server_address, RequestHandler)

    logging.info("Starting HTTP server")
    
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        http_server.server_close()

if __name__ == '__main__':
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    import threading

    http_thread = threading.Thread(target=run_http_server, args=(HTTP_HOST, HTTP_PORT))
    http_thread.start()


    socket_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_server.bind((SOCKET_HOST, SOCKET_PORT))

    logging.info("Starting socket server")

    while True:
        data, addr = socket_server.recvfrom(BUFFER_SIZE)
        logging.info(f"Received data from {addr}: {data.decode('utf-8')}")

    socket_server.close()
