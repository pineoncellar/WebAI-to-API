import argparse
import os
from pathlib import Path

from app.utils.browser import CrossPlatformCookieExtractor


def main() -> None:
    parser = argparse.ArgumentParser(description="Test decrypting Chromium cookies for Gemini.")
    parser.add_argument(
        "--cookies",
        default="Cookies",
        help="Path to the Chromium cookies SQLite file (copied file or original).",
    )
    parser.add_argument(
        "--local-state",
        default=None,
        help="Path to the Chromium Local State file. Defaults to the standard Edge path.",
    )
    args = parser.parse_args()

    cookies_path = Path(args.cookies).resolve()
    if not cookies_path.exists():
        raise SystemExit(f"Cookies file not found: {cookies_path}")

    if args.local_state:
        local_state_path = Path(args.local_state).resolve()
    else:
        local_state_path = Path(os.path.expanduser("~")) / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data" / "Local State"

    if not local_state_path.exists():
        raise SystemExit(f"Local State file not found: {local_state_path}")

    extractor = CrossPlatformCookieExtractor()
    cookies = extractor._get_chromium_cookies_direct(str(cookies_path), str(local_state_path))

    if not cookies:
        print("No cookies decoded.")
        return

    for cookie in cookies:
        value_preview = (cookie.value[:60] + "...") if cookie.value and len(cookie.value) > 60 else cookie.value
        print(f"{cookie.name}: {value_preview}")


if __name__ == "__main__":
    main()
