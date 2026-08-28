from wsgiref.simple_server import make_server

from api_server import app


if __name__ == "__main__":
    host = "0.0.0.0"
    port = 5000
    print(f"Serving SignTranslator API on http://{host}:{port}")
    make_server(host, port, app).serve_forever()
