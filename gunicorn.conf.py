import multiprocessing
import os


def health_check_filter(resp, req, env, request_time):
    if "kube-probe" in req.headers.get("User-Agent", ""):
        return False
    return True


bind = "0.0.0.0:8080"
workers = multiprocessing.cpu_count() * 2 + 1
if os.environ.get("TOURGUIDE_TMP_DIR") != "None":
    worker_tmp_dir = os.environ.get("TOURGUIDE_TMP_DIR", "/dev/shm")
loglevel = os.environ.get("TOURGUIDE_LOG_LEVEL", "warning")
errorlog = "-"  # stderr
accesslog = "-"  # stdout
graceful_timeout = int(os.environ.get("TOURGUIDE_TIMEOUT", 90))
timeout = int(os.environ.get("TOURGUIDE_TIMEOUT", 90))
keepalive = 10
threads = 4
worker_class = "gthread"
forwarded_allow_ips = "*"
proxy_protocol = os.environ.get("TOURGUIDE_GUNICORN_PROXY_PROTOCOL", False) == "true"
access_log_filter = health_check_filter
