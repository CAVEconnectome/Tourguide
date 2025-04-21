# custom_logger.py
import logging
import re

import statsd
from gunicorn import glogging


class KubeProbeFilter(logging.Filter):
    def __init__(self):
        # Pattern to match kube-probe requests to version endpoint
        self.health_check_pattern = re.compile(r"GET.*kube-probe")

    def filter(self, record):
        # Return False (don't log) if this is a health check
        log_message = record.getMessage()
        return not bool(self.health_check_pattern.search(log_message))


class DashFilter(logging.Filter):
    def __init__(self):
        # Pattern to match kube-probe requests to version endpoint
        self.dash_update_pattern = re.compile(
            r"POST.*_dash-update-component|GET.*_dash-layout|GET.*_dash-component-suites|GET.*_dash-dependencies|GET.*_favicon.ico"
        )

    def filter(self, record):
        # Return False (don't log) if this is a health check
        log_message = record.getMessage()
        return not bool(self.dash_update_pattern.search(log_message))


class StatsDClient:
    _instance = None

    @classmethod
    def get_instance(cls, host, port=8125, prefix=None):
        # Create a unique instance key based on all parameters
        instance_key = f"{host}:{port}:{prefix}"

        if cls._instance is None or cls._instance.get("key") != instance_key:
            host_parts = host.split(":") if host else ["localhost"]
            if len(host_parts) > 1:
                host, port = host_parts[0], int(host_parts[1])

            logger = logging.getLogger("statsd.client")
            logger.setLevel(logging.DEBUG)
            logger.debug(
                f"Initializing StatsD client: host={host}, port={port}, prefix={prefix}"
            )

            try:
                client = statsd.StatsClient(host=host, port=port, prefix=prefix)
                logger.debug("StatsD client initialized successfully")
                cls._instance = {"client": client, "key": instance_key}
            except Exception as e:
                logger.error(f"Failed to initialize StatsD client: {e}")
                cls._instance = None

        return cls._instance["client"] if cls._instance else None


# Now enhance the CustomGunicornLogger to use this tracker
class CustomGunicornLogger(glogging.Logger):
    def __init__(self, cfg):
        super().__init__(cfg)

    def setup(self, cfg):
        # Call the parent setup
        super().setup(cfg)

        # Add our filters to the access log
        print("Setting up custom filters")
        access_logger = logging.getLogger("gunicorn.access")
        access_logger.addFilter(KubeProbeFilter())
        access_logger.addFilter(DashFilter())
        access_logger.debug("Custom filters added to access logger")
