import multiprocessing

bind = "0.0.0.0:8080"
workers = multiprocessing.cpu_count() * 2 + 1
worker_tmp_dir = "/dev/shm"
loglevel = "warn"
errorlog = "-"  # stderr
accesslog = "-"  # stdout
graceful_timeout = 120
timeout = 120
keepalive = 5
threads = 4
worker_class = "gthread"
