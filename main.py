import mimetypes
import urllib.parse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket
import logging
from urllib.parse import unquote_plus
from datetime import datetime, timedelta
import json
from threading import Thread

BASE_DIR = Path()
UDP_IP = '127.0.0.1'
UDP_PORT = 5000
HTTP_PORT = 3000
HTTP_HOST = '0.0.0.0'
MESSAGE = {}


class GoitFramework(BaseHTTPRequestHandler):
    def do_GET(self):
        route = urllib.parse.urlparse(self.path)
        print(route.query)
        match route.path:
            case '/':
                self.send_html('index.html')
            case '/message':
                self.send_html('message.html')
            case _:
                file = BASE_DIR.joinpath(route.path[1:])
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html('error.html', 404)

    def do_POST(self):
        size = self.headers.get("Content-Length")
        data = self.rfile.read(int(size))
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.sendto(data, (UDP_IP, UDP_PORT))
        client_socket.close()
        save_data(data)
        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

    def send_html(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as file:
            self.wfile.write(file.read())

    def send_static(self, filename, status_code=200):
        self.send_response(status_code)
        mime_type, *_ = mimetypes.guess_type(filename)
        if mime_type:
            self.send_header('Content-Type', mime_type)
        else:
            self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        with open(filename, 'rb') as file:
            self.wfile.write(file.read())


def save_data(data):
    try:
        parse_data = unquote_plus(data.decode())
        parse_dict = {key: value for key, value in [el.split('=') for el in parse_data.split('&')]}
        
        current_time = str(datetime.now() + timedelta(hours=0))
        MESSAGE[current_time] = parse_dict

        with open('storage/data.json', 'w', encoding='utf-8') as file:
            json.dump(MESSAGE, file, ensure_ascii=False, indent=4)
            file.write('\n')

    except ValueError as error:
        logging.error(f'ValueError in save_data_from_form: {error}')
    except OSError as error:
        logging.error(f'OSError in save_data_from_form: {error}')


def run_http_server(host, port):
    address = (host, port)
    http_server = HTTPServer(address, GoitFramework)
    logging.info("Starting http")
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()


def run_client(ip, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((ip, port))
    logging.info("Starting socket server")
    try:
        while True:
            msg, address = server_socket.recvfrom(1024)
            logging.info(f"Socket receiver {address}: {msg}")
            save_data(msg)
    except KeyboardInterrupt:
        pass
    finally:
        server_socket.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format="%(threadName)s%(message)s")
    server = Thread(target=run_http_server, args=(HTTP_HOST, HTTP_PORT))
    server.start()

    server_socket = Thread(target=run_client, args=(UDP_IP, UDP_PORT))
    server_socket.start()
