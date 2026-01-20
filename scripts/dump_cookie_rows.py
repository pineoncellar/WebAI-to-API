import argparse
import sqlite3
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Dump raw cookie rows for inspection.")
    parser.add_argument("--cookies", default="Cookies", help="Path to the cookies SQLite DB.")
    parser.add_argument(
        "--names",
        default="__Secure-1PSID,__Secure-1PSIDTS",
        help="Comma separated cookie names to dump.",
    )
    args = parser.parse_args()

    cookies_path = Path(args.cookies).resolve()
    if not cookies_path.exists():
        raise SystemExit(f"Cookies file not found: {cookies_path}")

    names = [name.strip() for name in args.names.split(",") if name.strip()]
    if not names:
        raise SystemExit("No cookie names provided.")

    placeholders = ",".join("?" for _ in names)

    conn = sqlite3.connect(f"file:{cookies_path}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute(
        f"SELECT name, host_key, path, length(value), length(encrypted_value), hex(encrypted_value) FROM cookies WHERE name IN ({placeholders})",
        names,
    )

    rows = cur.fetchall()
    if not rows:
        print("No matching cookies.")
    else:
        for row in rows:
            name, host_key, path, value_len, encrypted_len, encrypted_hex = row
            print("-" * 80)
            print(f"Name: {name}")
            print(f"Host: {host_key}")
            print(f"Path: {path}")
            print(f"Value length: {value_len}")
            print(f"Encrypted length: {encrypted_len}")
            print(f"Encrypted hex: {encrypted_hex[:120]}...")

    conn.close()


if __name__ == "__main__":
    main()
