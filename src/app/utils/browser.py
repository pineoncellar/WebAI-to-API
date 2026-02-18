# src/app/utils/browser.py
import logging
import browser_cookie3
import platform
import os
import sqlite3
import json
import base64
import tempfile
import shutil
import socket
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Optional, Literal, Dict, Any

import httpx

from app.config import CONFIG

# Windows-specific imports for cookie decryption
try:
    from websocket import create_connection  # type: ignore
    HAS_WEBSOCKET = True
except ImportError:
    HAS_WEBSOCKET = False


if platform.system().lower() == "windows":
    try:
        import win32crypt
        from Crypto.Cipher import AES
        HAS_CRYPTO = True
    except ImportError:
        HAS_CRYPTO = False
        logging.warning("Windows crypto libraries not available. Install with: pip install pywin32 pycryptodome")
else:
    HAS_CRYPTO = False

logger = logging.getLogger(__name__)

class CrossPlatformCookieExtractor:
    """Cross-platform cookie extractor with Windows compatibility fixes"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.is_windows = self.system == "windows"
        logger.info(f"Initialized cookie extractor for {self.system}")
    
    def _get_browser_profile_paths(self, browser_name: str, profile: str = "Default") -> Dict[str, Any]:
        """Get browser profile paths for different operating systems"""
        paths = {}
        
        if self.is_windows:
            user_data = os.path.expanduser("~")
            if browser_name == "chrome":
                base_path = os.path.join(user_data, "AppData", "Local", "Google", "Chrome", "User Data")
                # Check multiple possible locations for Chrome cookies
                possible_paths = [
                    os.path.join(base_path, profile, "Network", "Cookies"),  # New Chrome location
                    os.path.join(base_path, profile, "Cookies"),  # Old Chrome location
                ]
                cookies_path = None
                for path in possible_paths:
                    if os.path.exists(path):
                        cookies_path = path
                        logger.info(f"Found Chrome cookies in profile '{profile}' at: {path}")
                        break
                
                paths = {
                    "cookies_db": cookies_path,
                    "local_state": os.path.join(base_path, "Local State"),
                    "user_data_dir": base_path,
                    "profile_directory": profile,
                }
                
            elif browser_name == "brave":
                base_path = os.path.join(user_data, "AppData", "Local", "BraveSoftware", "Brave-Browser", "User Data")
                # Check multiple possible locations for Brave cookies
                possible_paths = [
                    os.path.join(base_path, profile, "Network", "Cookies"),  # New Brave location
                    os.path.join(base_path, profile, "Cookies"),  # Old Brave location
                ]
                cookies_path = None
                for path in possible_paths:
                    if os.path.exists(path):
                        cookies_path = path
                        logger.info(f"Found Brave cookies in profile '{profile}' at: {path}")
                        break
                
                paths = {
                    "cookies_db": cookies_path,
                    "local_state": os.path.join(base_path, "Local State"),
                    "user_data_dir": base_path,
                    "profile_directory": profile,
                }
                
            elif browser_name == "edge":
                base_path = os.path.join(user_data, "AppData", "Local", "Microsoft", "Edge", "User Data")
                # Check multiple possible locations for Edge cookies
                possible_paths = [
                    os.path.join(base_path, profile, "Network", "Cookies"),  # New Edge location
                    os.path.join(base_path, profile, "Cookies"),  # Old Edge location
                ]
                cookies_path = None
                for path in possible_paths:
                    if os.path.exists(path):
                        cookies_path = path
                        logger.info(f"Found Edge cookies in profile '{profile}' at: {path}")
                        break
                
                paths = {
                    "cookies_db": cookies_path,
                    "local_state": os.path.join(base_path, "Local State"),
                    "user_data_dir": base_path,
                    "profile_directory": profile,
                }
                
            elif browser_name == "firefox":
                firefox_path = os.path.join(user_data, "AppData", "Roaming", "Mozilla", "Firefox", "Profiles")
                if os.path.exists(firefox_path):
                    profiles = [d for d in os.listdir(firefox_path) if os.path.isdir(os.path.join(firefox_path, d))]
                    if profiles:
                        profile_path = os.path.join(firefox_path, profiles[0])
                        paths = {"cookies_db": os.path.join(profile_path, "cookies.sqlite")}

        # Linux Support
        elif self.system == "linux":
            home = os.path.expanduser("~")
            if browser_name == "chrome":
                base_path = os.path.join(home, ".config", "google-chrome")
                paths = {
                    "cookies_db": os.path.join(base_path, profile, "Cookies"), # Often in Default/Cookies
                    "user_data_dir": base_path,
                    "profile_directory": profile,
                }
            elif browser_name == "brave":
                 base_path = os.path.join(home, ".config", "BraveSoftware", "Brave-Browser")
                 paths = {
                    "cookies_db": os.path.join(base_path, profile, "Cookies"),
                    "user_data_dir": base_path,
                    "profile_directory": profile,
                }
            elif browser_name == "firefox":
                 # Firefox is trickier as profiles have random strings in names
                 base_path = os.path.join(home, ".mozilla", "firefox")
                 pass 
        
        return paths

    def _get_free_port(self) -> int:
        """Allocate an ephemeral port on localhost."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]

    def _find_browser_executable(self, browser_name: str) -> Optional[str]:
        """Locate the browser executable on Windows and Linux."""
        if not self.is_windows:
            # Linux executable names mapping
            linux_names = {
                "chrome": ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"],
                "edge": ["microsoft-edge", "microsoft-edge-stable", "microsoft-edge-dev"],
                "brave": ["brave-browser", "brave"],
                "firefox": ["firefox"]
            }
            
            # Check mapped names first
            if browser_name in linux_names:
                for name in linux_names[browser_name]:
                    path = shutil.which(name)
                    if path:
                        return path
            
            # Fallback to direct name check
            return shutil.which(browser_name)

        candidates = []
        pf = os.environ.get("ProgramFiles", "")
        pf86 = os.environ.get("ProgramFiles(x86)", "")
        local_app_data = os.environ.get("LOCALAPPDATA", "")

        if browser_name == "edge":
            candidates.extend(
                [
                    os.path.join(pf86, "Microsoft", "Edge", "Application", "msedge.exe"),
                    os.path.join(pf, "Microsoft", "Edge", "Application", "msedge.exe"),
                ]
            )
        elif browser_name == "chrome":
            candidates.extend(
                [
                    os.path.join(pf, "Google", "Chrome", "Application", "chrome.exe"),
                    os.path.join(pf86, "Google", "Chrome", "Application", "chrome.exe"),
                    os.path.join(local_app_data, "Google", "Chrome", "Application", "chrome.exe"),
                ]
            )
        elif browser_name == "brave":
            candidates.extend(
                [
                    os.path.join(pf, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
                    os.path.join(pf86, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
                ]
            )

        # Fallback to PATH lookup
        candidates.append(shutil.which(browser_name))

        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate

        logger.warning(f"Executable for {browser_name} not found in standard locations")
        return None

    def _get_chromium_cookies_via_devtools(self, browser_name: str, profile: str = "Default") -> Optional[list]:
        """Leverage Chromium DevTools protocol to fetch decrypted cookies."""
        if not (self.is_windows and HAS_WEBSOCKET):
            if self.is_windows and not HAS_WEBSOCKET:
                logger.debug("websocket-client not available; skipping DevTools extraction")
            return None

        browser_paths = self._get_browser_profile_paths(browser_name, profile=profile)
        user_data_dir = browser_paths.get("user_data_dir")
        profile_directory = browser_paths.get("profile_directory", profile)
        executable_path = self._find_browser_executable(browser_name)

        if not executable_path or not user_data_dir:
            logger.warning(f"Insufficient data for DevTools extraction for {browser_name}")
            return None

        if not os.path.exists(user_data_dir):
            logger.warning(f"User data directory not found for {browser_name}: {user_data_dir}")
            return None

        port = self._get_free_port()
        command = [
            executable_path,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={user_data_dir}",
            f"--profile-directory={profile_directory}",
            f"--remote-allow-origins=http://127.0.0.1:{port}",
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "about:blank",
        ]

        logger.info(f"Launching {browser_name} for DevTools cookie extraction (port {port})")

        creationflags = 0
        if self.is_windows:
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
        except Exception as exc:
            logger.error(f"Failed to launch {browser_name} for DevTools extraction: {exc}")
            return None

        ws_url = None
        try:
            for _ in range(40):  # Allow up to ~10 seconds
                time.sleep(0.25)
                try:
                    response = httpx.get(f"http://127.0.0.1:{port}/json/version", timeout=1.0)
                    if response.status_code == 200:
                        ws_url = response.json().get("webSocketDebuggerUrl")
                        if ws_url:
                            break
                except Exception:
                    continue

            if not ws_url:
                logger.error("DevTools endpoint not reachable; ensure the browser profile is not already running.")
                return None

            logger.info("Connecting to DevTools websocket for cookie retrieval")

            cookies = []
            ws = None
            try:
                ws = create_connection(ws_url, timeout=5)

                message_id = 0

                def send_command(method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
                    nonlocal message_id
                    message_id += 1
                    ws.send(json.dumps({"id": message_id, "method": method, "params": params or {}}))
                    while True:
                        reply = json.loads(ws.recv())
                        if reply.get("id") == message_id:
                            return reply

                send_command("Network.enable")

                url_candidates = [
                    "https://gemini.google.com",
                    "https://www.google.com",
                    "https://accounts.google.com",
                ]

                cookie_reply = send_command("Network.getCookies", {"urls": url_candidates})
                cookies = cookie_reply.get("result", {}).get("cookies", [])

                if not cookies:
                    storage_reply = send_command("Storage.getCookies")
                    cookies = storage_reply.get("result", {}).get("cookies", [])

            finally:
                if ws:
                    ws.close()

            result = []
            for cookie in cookies:
                result.append(
                    SimpleNamespace(
                        name=cookie.get("name", ""),
                        value=cookie.get("value", ""),
                        domain=cookie.get("domain", ""),
                        path=cookie.get("path", ""),
                        expires=cookie.get("expires", 0),
                        secure=cookie.get("secure", False),
                        httponly=cookie.get("httpOnly", False),
                    )
                )

            if result:
                logger.info("Successfully retrieved cookies via DevTools protocol")
            else:
                logger.warning("DevTools cookie retrieval returned no entries")

            return result if result else None

        except Exception as exc:
            logger.error(f"DevTools cookie extraction failed: {exc}")
            return None
        finally:
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
    
    def _try_browser_cookie3(self, browser_name: str) -> Optional[Any]:
        """Try to get cookies using browser_cookie3 library"""
        try:
            if browser_name == "firefox":
                return browser_cookie3.firefox()
            elif browser_name == "chrome":
                return browser_cookie3.chrome()
            elif browser_name == "brave":
                return browser_cookie3.brave()
            elif browser_name == "edge":
                return browser_cookie3.edge()
            elif browser_name == "safari":
                return browser_cookie3.safari()
            else:
                raise ValueError(f"Unsupported browser: {browser_name}")
        except Exception as e:
            logger.warning(f"browser_cookie3 failed for {browser_name}: {e}")
            return None
    
    def _decrypt_chrome_cookie_value(self, encrypted_value: bytes, local_state_path: str) -> Optional[str]:
        """Decrypt Chrome cookie value on Windows"""
        if not self.is_windows or not HAS_CRYPTO:
            logger.warning("Decryption not available: not Windows or crypto libraries missing")
            return None
            
        try:
            logger.info(f"Attempting decryption with Local State: {local_state_path}")
            logger.info(f"Encrypted value length: {len(encrypted_value)}")
            
            # Read the local state file to get the encryption key
            if not os.path.exists(local_state_path):
                logger.warning(f"Local State file not found: {local_state_path}")
                return None
                
            with open(local_state_path, 'r', encoding='utf-8') as f:
                local_state = json.load(f)
            
            # Get the encrypted key
            if 'os_crypt' not in local_state or 'encrypted_key' not in local_state['os_crypt']:
                logger.warning("os_crypt.encrypted_key not found in Local State")
                return None
                
            encrypted_key = base64.b64decode(local_state['os_crypt']['encrypted_key'])
            logger.info(f"Encrypted key length: {len(encrypted_key)}")
            
            # Remove the 'DPAPI' prefix (first 5 bytes)
            encrypted_key = encrypted_key[5:]
            
            # Decrypt the key using Windows DPAPI
            key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
            logger.info(f"Decrypted key length: {len(key)}")
            
            # The cookie value format: version (3 bytes) + nonce (12 bytes) + encrypted_data + tag (16 bytes)
            if len(encrypted_value) < 31:  # 3 + 12 + 1 + 16 = minimum length
                logger.warning(f"Encrypted value too short: {len(encrypted_value)} bytes")
                return None
                
            # Extract components
            version = encrypted_value[:3]
            logger.info(f"Cookie encryption version: {version}")

            if not version.startswith(b"v1") and not version.startswith(b"v2"):
                logger.info("Trying DPAPI decryption for legacy Chromium cookie format")
                try:
                    decrypted = win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1]
                    result = decrypted.decode("utf-8")
                    logger.info(f"DPAPI decryption successful, result length: {len(result)}")
                    return result
                except Exception as e:
                    logger.warning(f"DPAPI decryption failed: {e}")
                    return None

            nonce = encrypted_value[3:15]
            ciphertext = encrypted_value[15:-16]
            tag = encrypted_value[-16:]

            logger.info(f"AES-GCM components - nonce: {len(nonce)}, ciphertext: {len(ciphertext)}, tag: {len(tag)}")

            try:
                cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
                decrypted = cipher.decrypt_and_verify(ciphertext, tag)
                result = decrypted.decode('utf-8')
                logger.info(f"AES-GCM decryption successful, result length: {len(result)}")
                return result
            except ValueError as aes_error:
                logger.warning(f"AES-GCM decryption failed ({aes_error}). Attempting DPAPI fallback.")
                try:
                    decrypted = win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1]
                    result = decrypted.decode('utf-8')
                    logger.info(f"DPAPI fallback successful, result length: {len(result)}")
                    return result
                except Exception as dpapi_error:
                    logger.warning(f"DPAPI fallback failed: {dpapi_error}")
                    return None
            
        except Exception as e:
            logger.error(f"Failed to decrypt Chrome cookie: {e}", exc_info=True)
            return None

    def _get_firefox_cookies_direct(self, cookies_db_path: str) -> Optional[list]:
        """Direct Firefox cookie extraction from SQLite database"""
        try:
            if not os.path.exists(cookies_db_path):
                logger.warning(f"Firefox cookies database not found: {cookies_db_path}")
                return None

            # Copy the database to avoid lock issues
            import tempfile
            import shutil

            with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as temp_file:
                temp_db_path = temp_file.name
                shutil.copy2(cookies_db_path, temp_db_path)

            try:
                conn = sqlite3.connect(temp_db_path)
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT name, value, host, path, expiry, isSecure, isHttpOnly
                    FROM moz_cookies
                    WHERE host LIKE '%google%' AND (name = '__Secure-1PSID' OR name = '__Secure-1PSIDTS')
                    """
                )

                cookies = []
                for row in cursor.fetchall():
                    cookie_obj = type(
                        "Cookie",
                        (),
                        {
                            "name": row[0],
                            "value": row[1],
                            "domain": row[2],
                            "path": row[3],
                            "expires": row[4],
                            "secure": bool(row[5]),
                            "httponly": bool(row[6]),
                        },
                    )()
                    cookies.append(cookie_obj)

                conn.close()
                return cookies
            finally:
                # Clean up temp file copy if present
                try:
                    os.unlink(temp_db_path)
                except OSError:
                    pass

        except Exception as e:
            logger.error(f"Failed to extract Firefox cookies directly: {e}")
            return None
    
    def _get_chromium_cookies_direct(self, cookies_db_path: str, local_state_path: str = None) -> Optional[list]:
        """Direct Chromium-based browser cookie extraction with decryption support"""
        temp_db_path = None
        connection = None

        try:
            if not os.path.exists(cookies_db_path):
                logger.warning(f"Chromium cookies database not found: {cookies_db_path}")
                return None

            try:
                temp_fd, temp_db_path = tempfile.mkstemp(suffix=".db")
                os.close(temp_fd)
                shutil.copy2(cookies_db_path, temp_db_path)
                connection = sqlite3.connect(temp_db_path)
            except OSError as copy_error:
                if getattr(copy_error, "winerror", None) == 32:
                    logger.warning("Chromium cookies database is locked. Using read-only SQLite connection.")
                    if temp_db_path and os.path.exists(temp_db_path):
                        try:
                            os.unlink(temp_db_path)
                        except OSError:
                            pass
                    temp_db_path = None

                    resolved_path = Path(cookies_db_path).resolve()
                    readonly_base_uri = resolved_path.as_uri()

                    readonly_uri_attempts = [
                        f"{readonly_base_uri}?mode=ro&immutable=1",
                        f"{readonly_base_uri}?mode=ro",
                    ]

                    last_error = None
                    for readonly_uri in readonly_uri_attempts:
                        try:
                            connection = sqlite3.connect(readonly_uri, uri=True)
                            last_error = None
                            break
                        except sqlite3.OperationalError as sqlite_error:
                            last_error = sqlite_error
                            logger.warning(
                                "Read-only SQLite connection failed with URI %s: %s",
                                readonly_uri,
                                sqlite_error,
                            )

                    if not connection:
                        raise last_error if last_error else sqlite3.OperationalError(
                            "Unable to open Chromium cookies database in read-only mode"
                        )
                else:
                    raise

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT name, value, encrypted_value, host_key, path, expires_utc, is_secure, is_httponly
                FROM cookies
                WHERE host_key LIKE '%google%' AND (name = '__Secure-1PSID' OR name = '__Secure-1PSIDTS')
                """
            )

            cookies = []
            for row in cursor.fetchall():
                name, value, encrypted_value, host_key, path, expires_utc, is_secure, is_httponly = row

                if isinstance(value, memoryview):
                    value = value.tobytes().decode("utf-8", errors="ignore")
                if isinstance(encrypted_value, memoryview):
                    encrypted_value = encrypted_value.tobytes()

                final_value = value
                if not value and encrypted_value and self.is_windows and local_state_path:
                    decrypted_value = self._decrypt_chrome_cookie_value(encrypted_value, local_state_path)
                    if decrypted_value:
                        final_value = decrypted_value
                    else:
                        logger.warning(f"Failed to decrypt cookie: {name}")
                elif not value:
                    logger.warning(f"No value found for {name} (neither plain nor encrypted)")

                cookie_obj = type(
                    "Cookie",
                    (),
                    {
                        "name": name,
                        "value": final_value or "",
                        "domain": host_key,
                        "path": path,
                        "expires": expires_utc,
                        "secure": bool(is_secure),
                        "httponly": bool(is_httponly),
                    },
                )()
                cookies.append(cookie_obj)

            if cookies and all(not getattr(cookie, "value", "") for cookie in cookies):
                logger.warning("Chromium cookies extraction yielded empty values; will fallback to alternative methods.")
                return None

            return cookies
        except Exception as e:
            logger.error(f"Failed to extract Chromium cookies directly: {e}")
            return None
        finally:
            if connection:
                connection.close()
            if temp_db_path:
                try:
                    os.unlink(temp_db_path)
                except OSError:
                    pass
    
    def get_cookies_with_fallback(self, browser_name: str, profile: str = "Default") -> Optional[Any]:
        """Get cookies with multiple fallback methods"""
        logger.info(f"Attempting to get cookies from {browser_name} (profile: {profile}) with fallback methods")
        
        # Method 1: Try browser_cookie3 first (works well on Linux, but doesn't support profiles easily)
        if profile == "Default":
            cookies = self._try_browser_cookie3(browser_name)
            if cookies:
                logger.info(f"Successfully retrieved cookies using browser_cookie3 for {browser_name}")
                return cookies
        
        # Method 2: Try direct database access (fallback for Windows)
        if self.is_windows:
            logger.info(f"Trying direct database access for {browser_name} profile '{profile}' on Windows")
            
            browser_paths = self._get_browser_profile_paths(browser_name, profile=profile)
            
            if browser_name == "firefox" and "cookies_db" in browser_paths:
                cookies = self._get_firefox_cookies_direct(browser_paths["cookies_db"])
                if cookies:
                    logger.info(f"Successfully retrieved Firefox cookies via direct access")
                    return cookies
            
            elif browser_name in ["chrome", "brave", "edge"] and "cookies_db" in browser_paths:
                cookies_db_path = browser_paths["cookies_db"]
                local_state_path = browser_paths.get("local_state")
                
                if cookies_db_path and os.path.exists(cookies_db_path):
                    cookies = self._get_chromium_cookies_direct(cookies_db_path, local_state_path)
                    if cookies:
                        logger.info(f"Successfully retrieved {browser_name} cookies via direct access")
                        return cookies
                else:
                    logger.warning(f"Cookies database not found for {browser_name} profile '{profile}' at {cookies_db_path}")

                logger.info(f"Attempting DevTools-based extraction for {browser_name} profile '{profile}'")
                cookies = self._get_chromium_cookies_via_devtools(browser_name, profile=profile)
                if cookies:
                    logger.info(f"Successfully retrieved {browser_name} cookies via DevTools protocol")
                    return cookies
                else:
                    logger.warning(f"DevTools extraction failed for {browser_name} profile '{profile}'")
        
        logger.warning(f"All cookie extraction methods failed for {browser_name}")
        return None


def get_cookie_from_browser(service: Literal["gemini"]) -> Optional[tuple]:
    """Enhanced cookie extraction with cross-platform support"""
    browser_name = CONFIG["Browser"].get("name", "firefox").lower()
    profile = CONFIG["Browser"].get("profile", "Default")
    logger.info(f"Attempting to get cookies from browser: {browser_name} (profile: {profile}) for service: {service}")
    
    extractor = CrossPlatformCookieExtractor()
    
    try:
        cookies = extractor.get_cookies_with_fallback(browser_name, profile=profile)
        
        if not cookies:
            logger.error(f"Failed to retrieve cookies from {browser_name} (profile: {profile})")
            return None
        
        logger.info(f"Successfully retrieved cookies from {browser_name} (profile: {profile})")
        
    except Exception as e:
        logger.error(f"An unexpected error occurred while retrieving cookies from {browser_name}: {e}", exc_info=True)
        return None
    
    # Process cookies for the requested service
    if service == "gemini":
        logger.info("Looking for Gemini cookies (__Secure-1PSID and __Secure-1PSIDTS)...")
        secure_1psid = None
        secure_1psidts = None
        
        try:
            for cookie in cookies:
                if hasattr(cookie, 'name') and hasattr(cookie, 'value') and hasattr(cookie, 'domain'):
                    if cookie.name == "__Secure-1PSID" and "google" in cookie.domain:
                        secure_1psid = cookie.value
                        logger.info(f"Found __Secure-1PSID: {secure_1psid[:20]}..." if secure_1psid else "Found __Secure-1PSID (empty value)")
                    elif cookie.name == "__Secure-1PSIDTS" and "google" in cookie.domain:
                        secure_1psidts = cookie.value
                        logger.info(f"Found __Secure-1PSIDTS: {secure_1psidts[:20]}..." if secure_1psidts else "Found __Secure-1PSIDTS (empty value)")
        except Exception as e:
            logger.error(f"Error processing cookies: {e}")
            return None
        
        if secure_1psid and secure_1psidts:
            # Check if values are not empty (they might be encrypted on Windows)
            if len(secure_1psid.strip()) == 0 or len(secure_1psidts.strip()) == 0:
                logger.warning("Gemini cookies found but appear to be empty (possibly encrypted). Manual cookie extraction may be required on Windows.")
                return None
            
            logger.info("Both Gemini cookies found and appear valid.")
            return secure_1psid, secure_1psidts
        else:
            logger.warning("Gemini cookies not found or incomplete.")
            return None
    else:
        logger.warning(f"Unsupported service: {service}")
        return None