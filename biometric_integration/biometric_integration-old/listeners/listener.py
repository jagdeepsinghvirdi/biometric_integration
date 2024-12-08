from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
from ebkn import handle_ebkn

# Logging setup
logging.basicConfig(
    filename='/home/zima/frappe-bench/logs/biometric_listener.log',
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s'
)

class BiometricRequestHandler(BaseHTTPRequestHandler):
    """Middleware to route requests directly to brand-specific handlers."""

    def do_POST(self):
        """Handle POST requests and pass them directly to handlers."""
        try:
            # Normalize the request path
            raw_path = self.path
            normalized_path = raw_path.split("://")[-1].split("/", 1)[-1]
            normalized_path = f"/{normalized_path}"
            logging.info(f"Request Path: {raw_path} (Normalized: {normalized_path})")

            # Log headers for debugging
            logging.info("Headers:")
            for key, value in self.headers.items():
                logging.info(f"{key}: {value}")

            # Route the request based on the normalized path
            if normalized_path == "/ebkn":
                self.pass_to_handler(handle_ebkn)
            else:
                logging.warning(f"Unsupported path: {raw_path}")
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error": "Unsupported brand path"}')

        except Exception as e:
            logging.error(f"Error processing request: {str(e)}", exc_info=True)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'{"error": "Internal server error"}')

    def pass_to_handler(self, handler):
        """Pass the raw request to the specified handler."""
        try:
            # Read raw request body
            content_length = int(self.headers.get('Content-Length', 0))
            raw_data = self.rfile.read(content_length)

            # Call the handler and get response
            response_body, status = handler(self, raw_data)

            # Send the response back to the client
            self.send_response(status)
            self.end_headers()
            self.wfile.write(response_body.encode('utf-8'))

        except Exception as e:
            logging.error(f"Error in handler: {str(e)}", exc_info=True)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'{"error": "Internal server error"}')


def run(server_class=HTTPServer, handler_class=BiometricRequestHandler, port=8998):
    """Run the HTTP server."""
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info(f"Starting server on port {port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
