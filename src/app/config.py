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
    
    if "CustomHeaders" not in config:
        config["CustomHeaders"] = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "X-Same-Domain": "1",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Ch-Ua": '"Not:A-Brand";v="99", "Chromium";v="145", "Google Chrome";v="145"',
            "Sec-Ch-Ua-Arch": '"x86"',
            "Sec-Ch-Ua-Bitness": '"64"',
            "Sec-Ch-Ua-Form-Factors": '"Desktop"',
            "Sec-Ch-Ua-Full-Version": '"145.0.7632.76"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Model": '""',
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Ch-Ua-Platform-Version": '"12.0.0"',
            "Sec-Ch-Ua-Wow64": "?0",
            "X-Browser-Channel": "stable",
            "X-Browser-Year": "1969",
            "X-Goog-Ext-525005358-jspb": '["37CE75D3-5F5D-4E7E-89AB-EE274C4C61A9",1]',
            "X-Goog-Ext-73010989-jspb": "[0]",
            "Origin": "https://gemini.google.com",
            "Referer": "https://gemini.google.com/",
        }

    # Save changes to the configuration file, also with UTF-8 encoding.
    save_config(config, config_file)

    return config


# Load configuration globally
CONFIG = load_config()


def is_debug_mode() -> bool:
    """Return whether debug logging mode is enabled in the configuration."""
    return CONFIG.getboolean("Logging", "debug", fallback=False)
