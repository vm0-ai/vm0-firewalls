#!/usr/bin/env python3
"""Generate google-drive/firewall.yaml from Google's Discovery API.

Usage:
    python3 google-drive/generate.py
"""

import sys
sys.path.insert(0, sys.path[0] + "/..")
from google_common import generate_firewall

generate_firewall(
    discovery_url="https://www.googleapis.com/discovery/v1/apis/drive/v3/rest",
    base_url="https://www.googleapis.com/drive/v3",
    path_prefix="",
    service_name="google-drive",
    service_description="Google Drive API",
    placeholder_key="GOOGLE_DRIVE_TOKEN",
    placeholder_value="ya29.A0Vm0PlaceHolder-Vm0_PlaceHolder00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
)
