# src/app/config.py
import configparser
import logging

logger = logging.getLogger(__name__)


def save_config(config: configparser.ConfigParser, config_file: str = "config.conf") -> None:
    """Persist the current in-memory configuration to disk."""
    try:
        with open(config_file, "w", encoding="utf-8") as config_file_handle:
            config.write(config_file_handle)
    except Exception as exc:
        logger.error(f"Error writing to config file: {exc}")


def load_config(config_file: str = "config.conf") -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    try:
        # FIX: Explicitly specify UTF-8 encoding to prevent UnicodeDecodeError on Windows.
        # This is the standard and most compatible way to handle text files across platforms.
        config.read(config_file, encoding="utf-8")
    except FileNotFoundError:
        logger.warning(
            f"Config file '{config_file}' not found. Creating a default one."
        )
    except Exception as e:
        logger.error(f"Error reading config file: {e}")

    # Set default sections and values if they don't exist
    if "Browser" not in config:
        config["Browser"] = {"name": "chrome"}
    if "Cookies" not in config:
        config["Cookies"] = {}
    if "AI" not in config:
        config["AI"] = {"default_model_gemini": "gemini-3.0-pro"}
    if "Proxy" not in config:
        config["Proxy"] = {"http_proxy": ""}
    if "Auth" not in config:
        config["Auth"] = {"api_key": ""}
    if "Logging" not in config:
        config["Logging"] = {"debug": "false"}

    # Save changes to the configuration file, also with UTF-8 encoding.
    save_config(config, config_file)

    return config


# Load configuration globally
CONFIG = load_config()


def is_debug_mode() -> bool:
    """Return whether debug logging mode is enabled in the configuration."""
    return CONFIG.getboolean("Logging", "debug", fallback=False)
