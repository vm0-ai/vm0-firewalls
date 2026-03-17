#!/usr/bin/env python3
"""Generate gmail/firewall.yaml from Google's Discovery API.

Usage:
    python3 gmail/generate.py
"""

import sys
sys.path.insert(0, sys.path[0] + "/..")
from google_common import generate_firewall

generate_firewall(
    discovery_url="https://gmail.googleapis.com/$discovery/rest?version=v1",
    base_url="https://gmail.googleapis.com/gmail/v1",
    path_prefix="gmail/v1",
    service_name="gmail",
    service_description="Gmail API",
    placeholder_key="GMAIL_TOKEN",
    placeholder_value="ya29.Vm0PlaceHolder000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
)
