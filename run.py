from guidebook.flask_app import create_app
from werkzeug.serving import WSGIRequestHandler
import os

app = create_app()

if __name__ == "__main__":
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    app.run(
        host="0.0.0.0",
        port=8008,
        debug=True,
        threaded=True,
        # ssl_context="adhoc",
    )
