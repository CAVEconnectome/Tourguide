# custom_logger.py
import logging
import re
from gunicorn import glogging


class KubeProbeFilter(logging.Filter):
    def __init__(self):
        # Pattern to match kube-probe requests to version endpoint
        self.health_check_pattern = re.compile(r"GET.*kube-probe")

    def filter(self, record):
        # Return False (don't log) if this is a health check
        log_message = record.getMessage()
        return not bool(self.health_check_pattern.search(log_message))


class CustomGunicornLogger(glogging.Logger):
    def setup(self, cfg):
        # Call the parent setup
        super().setup(cfg)

        # Add our filter to the access log
        logger = logging.getLogger("gunicorn.access")
        logger.addFilter(KubeProbeFilter())
        logger.debug("Added KubeProbeFilter")
