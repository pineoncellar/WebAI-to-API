import base64
import json
from pathlib import Path

import win32crypt

local_state_path = Path("C:/Users/Administrator/AppData/Local/Microsoft/Edge/User Data/Local State")
local_state = json.loads(local_state_path.read_text())
enc = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
print("raw prefix:", enc[:10])
if enc.startswith(b"DPAPI"):
    enc = enc[5:]
key = win32crypt.CryptUnprotectData(enc, None, None, None, 0)[1]
print("key bytes:", key.hex())
