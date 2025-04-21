from werkzeug.middleware.proxy_fix import ProxyFix
from middle_auth_client import (
    auth_required,
    auth_requires_permission,
)
from urllib import parse
import re
from prometheus_client import Gauge

from loguru import logger
import os

import sys

if os.environ.get("TOURGUIDE_VERBOSE_LOG", "false") == "true":
    log_level = "DEBUG"
else:
    log_level = "WARNING"

logger.remove()
logger.add(sys.stderr, colorize=True, level=log_level)

TOURGUIDE_PREFIX = "/tourguide"
ACTIVE_REQUESTS = Gauge(
    "tourguide_active_requests",
    "Number of active requests being processed",
    multiprocess_mode="livesum",
)

prom_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
if prom_dir:
    os.makedirs(prom_dir, exist_ok=True)
    # Initialize the multiprocess collector
    from prometheus_client import multiprocess
    from prometheus_client.core import CollectorRegistry

    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)


def configure_app(app):
    app.config["APPLICATION_ROOT"] = TOURGUIDE_PREFIX
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    @app.before_request
    def before_request():
        ACTIVE_REQUESTS.inc()

    @app.teardown_request
    def teardown_request(exception=None):
        ACTIVE_REQUESTS.dec()
        if exception:
            logger.error(f"Request failed: {exception}")


def protect_app(app):
    pages_url = f"{app.config.requests_pathname_prefix}<path:path>"
    view_func = app.server.view_functions[pages_url]
    app.server.view_functions[pages_url] = datastack_specific_auth(view_func)

    # Pass the update component view function through the auth_required decorator
    # in order to make auth token available to callbacks.
    update_url = f"{app.config.requests_pathname_prefix}_dash-update-component"
    app.server.view_functions[update_url] = auth_required_(
        app.server.view_functions[update_url]
    )
    return app


def parse_datastack_name(url):
    path = parse.urlparse(url).path
    g = re.search(r"[^\/]?datastack\/(?P<datastack_name>[^\/]+)", path)
    if g:
        return g.groupdict()["datastack_name"]
    else:
        return None


def check_is_already_authed(url):
    logger.debug("keys: ", parse.urlparse(url).query)
    return "middle_auth_token" in parse.urlparse(url).query


def datastack_specific_auth(
    view_func,
):
    logger.debug(f"Protecting func: {view_func}")

    def view_func_wrapped(*args, **kwargs):
        url = kwargs["path"]
        datastack_name = parse_datastack_name(url)
        is_authed = check_is_already_authed(url)
        logger.debug(f"auth datastack: {datastack_name}")
        if datastack_name and not is_authed:
            return auth_requires_permission(
                "view",
                table_id=datastack_name,
                resource_namespace="datastack",
            )(view_func)(*args, **kwargs)
        else:
            return view_func(*args, **kwargs)

    view_func_wrapped.__name__ = view_func.__name__ + "_wrapped"
    return view_func_wrapped


def auth_required_(
    view_func,
):
    logger.debug(f"Protecting func: {view_func}")

    def view_func_wrapped(*args, **kwargs):
        url = kwargs.get("path", "")
        if not check_is_already_authed(url):
            return auth_required(view_func)(*args, **kwargs)
        else:
            return view_func(*args, **kwargs)

    view_func_wrapped.__name__ = view_func.__name__ + "_wrapped"
    return view_func_wrapped
