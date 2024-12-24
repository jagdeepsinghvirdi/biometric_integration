from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import socket
import os
from datetime import datetime
import frappe
from biometric_integration.services.ebkn_processor import handle_ebkn

# Determine dynamic paths
bench_path = frappe.utils.get_bench_path()

# Set log file path dynamically
log_file_path = os.path.join(bench_path, "logs", "biometric_listener.log")

# Ensure logs directory exists
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

# Logging setup
logging.basicConfig(
    filename=log_file_path,
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s'
)

def get_raw_data_dir():
    raw_data_dir = os.path.join(bench_path, "sites", "assets", "biometric_assets", "raw_data_logs")
    os.makedirs(raw_data_dir, exist_ok=True)
    return raw_data_dir

class BiometricRequestHandler(BaseHTTPRequestHandler):
    """Middleware to route requests."""

    def do_POST(self):
        try:
            raw_path = self.path
            normalized_path = raw_path.split("://")[-1].split("/", 1)[-1]
            normalized_path = f"/{normalized_path}"

            if normalized_path == "/ebkn":
                dev_id = self.headers.get("dev_id")
                if not dev_id:
                    # Missing device id: respond 400
                    self.simple_response(400)
                    return
                    
                self.pass_to_handler(handle_ebkn)

            else:
                # Unsupported path
                self.simple_response(400)

        except Exception as e:
            logging.error(f"Error processing request: {str(e)}", exc_info=True)
            self.simple_response(400)

    def pass_to_handler(self, handler):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            raw_data = self.rfile.read(content_length)

            # Call handler
            response_body, status, response_headers = handler(self, raw_data, self.headers)
            
            # Check if response_body is already bytes
            if isinstance(response_body, bytes):
                response_body_bytes = response_body
            else:
                response_body_bytes = response_body.encode('utf-8')

            # Send response
            self.send_response(status)
            for header, value in response_headers.items():
                self.send_header(header, value)
            self.send_header("Content-Length", str(len(response_body_bytes)))
            self.end_headers()

            self.wfile.write(response_body_bytes)
            self.wfile.flush()

        except Exception as e:
            logging.error(f"Error in handler: {str(e)}", exc_info=True)
            # On any handler error: respond 400
            self.simple_response(400)

    def simple_response(self, status_code=400):
        """Send a simple minimal response with given status."""
        self.send_response(status_code)
        self.end_headers()

class CustomHTTPServer(HTTPServer):
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()

def start_listener(port=8998):
    server_address = ('', port)
    httpd = CustomHTTPServer(server_address, BiometricRequestHandler)
    logging.info(f"Starting server on port {port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info("Shutting down server gracefully...")
        httpd.shutdown()
        logging.info("Server stopped.")

def save_raw_data(raw_data, request_code, device_id):
    try:
        save_dir = get_raw_data_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        request_code = request_code or "unknown"
        device_id = device_id or "unknown"

        filename = f"{timestamp}_{request_code}_{device_id}.bin"
        file_path = os.path.join(save_dir, filename)
        with open(file_path, "wb") as file:
            file.write(raw_data)

        logging.info(f"Raw data saved to {file_path}")

    except Exception as e:
        logging.error(f"Failed to save raw data: {str(e)}")
