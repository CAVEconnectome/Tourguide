from prometheus_client import multiprocess
import multiprocessing
import os

bind = "0.0.0.0:8080"
workers = 2
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
logger_class = "custom_logger.CustomGunicornLogger"


def child_exit(server, worker):
    multiprocess.mark_process_dead(worker.pid)
