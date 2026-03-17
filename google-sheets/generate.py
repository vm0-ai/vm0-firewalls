#!/usr/bin/env python3
"""Generate google-sheets/firewall.yaml from Google's Discovery API.

Usage:
    python3 google-sheets/generate.py
"""

import sys
sys.path.insert(0, sys.path[0] + "/..")
from google_common import generate_firewall

generate_firewall(
    discovery_url="https://sheets.googleapis.com/$discovery/rest?version=v4",
    base_url="https://sheets.googleapis.com/v4",
    path_prefix="v4",
    service_name="google-sheets",
    service_description="Google Sheets API",
    placeholder_key="GOOGLE_SHEETS_TOKEN",
    placeholder_value="ya29.Vm0PlaceHolder000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
)
