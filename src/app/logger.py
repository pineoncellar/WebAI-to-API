# src/app/logger.py
import logging
import datetime
from pathlib import Path

from app.config import is_debug_mode


DEBUG_MODE = is_debug_mode()
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

handlers: list[logging.Handler] = [logging.StreamHandler()]


def setup_logging_file():
    """Sets up file logging if debug mode is enabled. Should be called once at startup."""
    if not DEBUG_MODE:
        return

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file_path = Path("logs") / f"{timestamp}.log"
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    
    # Add handler to the root logger
    logging.getLogger().addHandler(file_handler)
    
    logger = logging.getLogger("app")
    logger.debug("Debug logging enabled; capturing payloads and responses in %s.", log_file_path)


logging.basicConfig(level=logging.DEBUG if DEBUG_MODE else logging.INFO, format=LOG_FORMAT, handlers=handlers, force=True)

logging.getLogger("hpack.hpack").setLevel(logging.INFO)

logger = logging.getLogger("app")
logger.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)

