import multiprocessing
import os

bind = "0.0.0.0:8080"
workers = multiprocessing.cpu_count() * 2 + 1
if os.environ.get("GUIDEBOOK_TMP_DIR") != "None":
    worker_tmp_dir = os.environ.get("GUIDEBOOK_TMP_DIR", "/dev/shm")
loglevel = os.environ.get("GUIDEBOOK_LOG_LEVEL", "warning")
errorlog = "-"  # stderr
accesslog = "-"  # stdout
graceful_timeout = int(os.environ.get("GUIDEBOOK_TIMEOUT", 90))
timeout = int(os.environ.get("GUIDEBOOK_TIMEOUT", 90))
keepalive = 10
threads = 4
worker_class = "gthread"
