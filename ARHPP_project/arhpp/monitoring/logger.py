"""Structured logging setup."""

import logging
import json
import sys
from datetime import datetime
from pathlib import Path


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)
        return json.dumps(log, default=str)


def setup_logging(level: str = "INFO",
                    log_file: str = None,
                    json_format: bool = False) -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    if json_format:
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(JSONFormatter())
    else:
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)-7s] %(name)-25s %(message)s"))
    root.addHandler(console)

    if log_file:
        p = Path(log_file)
        p.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(p)
        fh.setFormatter(JSONFormatter())
        root.addHandler(fh)
