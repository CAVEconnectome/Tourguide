from middle_auth_client import (
    auth_required,
    auth_requires_admin,
    auth_requires_permission,
)
from urllib import parse
import re

import logging
import os

if os.environ.get("GUIDEBOOK_VERBOSE_LOG", "false") == "true":
    logging.getLogger().setLevel(logging.INFO)


def configure_app(app):
    pass


def protect_app(app):
    pages_url = f"{app.config.requests_pathname_prefix}<path:path>"
    view_func = app.server.view_functions[pages_url]
    app.server.view_functions[pages_url] = datastack_specific_auth(view_func)
    return app


def parse_datastack_name(url):
    path = parse.urlparse(url).path
    g = re.search(r"[^\/]?datastack\/(?P<datastack_name>[^\/]+)", path)
    if g:
        return g.groupdict()["datastack_name"]
    else:
        return None


def check_is_already_authed(url):
    return "middle_auth_token" in parse.urlparse(url).query


def datastack_specific_auth(
    view_func,
):
    print(f"Protecting func: {view_func}")

    def view_func_wrapped(*args, **kwargs):
        url = kwargs["path"]
        datastack_name = parse_datastack_name(url)
        is_authed = check_is_already_authed(url)
        print(f"auth datastack: {datastack_name}")
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
