FROM python:3.12-slim

WORKDIR /app

EXPOSE 8080

RUN useradd \
    --create-home \
    --shell /usr/sbin/nologin \
    appuser

RUN cat > /app/server.py <<'PY'
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer


HOST = os.getenv("APP_HOST")
PORT_VALUE = os.getenv("APP_PORT")


def startup_error(message):
    print(f"ERROR: {message}", file=sys.stderr, flush=True)
    sys.exit(1)


if not HOST:
    startup_error("APP_HOST is required")

if HOST != "0.0.0.0":
    startup_error("APP_HOST must be 0.0.0.0")

if not PORT_VALUE:
    startup_error("APP_PORT is required")

try:
    PORT = int(PORT_VALUE)
except ValueError:
    startup_error("APP_PORT must be a valid integer")

if PORT < 1 or PORT > 65535:
    startup_error("APP_PORT must be between 1 and 65535")


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"healthy")
            return

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Container Ghost is running")

    def log_message(self, fmt, *args):
        print(fmt % args, flush=True)


server = HTTPServer((HOST, PORT), Handler)

print(
    f"Server listening on {HOST}:{PORT}",
    flush=True
)

try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()
PY

RUN chown -R appuser:appuser /app

HEALTHCHECK \
    --interval=5s \
    --timeout=3s \
    --start-period=2s \
    --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health')"

USER appuser

CMD ["python", "/app/server.py"]
