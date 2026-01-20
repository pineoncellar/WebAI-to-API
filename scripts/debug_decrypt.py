import base64
import json
import sqlite3
from pathlib import Path

import win32crypt
from Cryptodome.Cipher import AES

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    AESGCM = None

COOKIES_DB = Path("Cookies").resolve()
LOCAL_STATE = Path("C:/Users/Administrator/AppData/Local/Microsoft/Edge/User Data/Local State")

def fetch_encrypted_value(name: str, host: str) -> bytes:
    conn = sqlite3.connect(f"file:{COOKIES_DB}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute(
        "SELECT encrypted_value FROM cookies WHERE name = ? AND host_key = ? LIMIT 1",
        (name, host),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        raise RuntimeError(f"Cookie {name} for host {host} not found")
    value = row[0]
    return value.tobytes() if isinstance(value, memoryview) else value

def load_key() -> bytes:
    local_state_data = json.loads(LOCAL_STATE.read_text(encoding="utf-8"))
    encrypted_key = base64.b64decode(local_state_data["os_crypt"]["encrypted_key"])
    if encrypted_key.startswith(b"DPAPI"):
        encrypted_key = encrypted_key[5:]
    key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    return key

def attempt_decrypt(encrypted: bytes, key: bytes) -> None:
    assert encrypted[:3] == b"v20", f"Unexpected prefix: {encrypted[:3]}"
    nonce = encrypted[3:15]
    ciphertext = encrypted[15:-16]
    tag = encrypted[-16:]
    print(f"nonce: {nonce.hex()}")
    print(f"ciphertext len: {len(ciphertext)}")
    print(f"tag: {tag.hex()}")

    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    try:
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)
        print("decrypt_and_verify succeeded")
        print(plaintext.decode("utf-8"))
    except Exception as exc:
        print(f"decrypt_and_verify failed: {exc}")
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        plaintext = cipher.decrypt(ciphertext)
        print(f"decrypt result (no verify): {plaintext[:60]!r}")

    if AESGCM is not None:
        try:
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext + tag, None)
            print("AESGCM decrypt succeeded", plaintext[:60])
        except Exception as exc:
            print("AESGCM decrypt failed", exc)

key = load_key()
print(f"key length: {len(key)}")

def scan_keys():
    local_state_data = json.loads(LOCAL_STATE.read_text(encoding="utf-8"))

    paths = []

    def walk(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_path = f"{path}.{k}" if path else k
                if k == "encrypted_key" and isinstance(v, str):
                    paths.append((new_path, v[:30]))
                walk(v, new_path)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                walk(item, f"{path}[{idx}]")

    walk(local_state_data)

    print("Encrypted key entries found:")
    for p, preview in paths:
        print(f"  {p}: {preview}...")

scan_keys()

enc_psid = fetch_encrypted_value("__Secure-1PSID", ".google.com")
attempt_decrypt(enc_psid, key)

enc_psidts = fetch_encrypted_value("__Secure-1PSIDTS", ".google.com")
attempt_decrypt(enc_psidts, key)
