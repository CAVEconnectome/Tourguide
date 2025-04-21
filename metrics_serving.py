import os
import time
from flask import Flask
from prometheus_client import make_wsgi_app, multiprocess, CollectorRegistry
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple

app = Flask(__name__)

# Check if prometheus multiproc directory is set
prom_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
if not prom_dir:
    raise ValueError("prometheus_multiproc_dir environment variable must be set")

# Set up the registry with the multiprocess collector
registry = CollectorRegistry()
multiprocess.MultiProcessCollector(registry)

# Add prometheus wsgi middleware
app_dispatch = DispatcherMiddleware(app, {"/metrics": make_wsgi_app(registry)})


@app.route("/health")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    # Run the app on port 9090 (standard Prometheus port)
    run_simple("0.0.0.0", 9090, app_dispatch)
