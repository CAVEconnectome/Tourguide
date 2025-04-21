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
