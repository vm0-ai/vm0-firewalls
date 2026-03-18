#!/usr/bin/env python3
"""Generate google-docs/firewall.yaml from Google's Discovery API.

Usage:
    python3 google-docs/generate.py
"""

import sys
sys.path.insert(0, sys.path[0] + "/..")
from google_common import generate_firewall

generate_firewall(
    discovery_url="https://docs.googleapis.com/$discovery/rest?version=v1",
    base_url="https://docs.googleapis.com/v1",
    path_prefix="v1",
    service_name="google-docs",
    service_description="Google Docs API",
    placeholder_key="GOOGLE_DOCS_TOKEN",
    placeholder_value="ya29.A0Vm0PlaceHolder-Vm0_PlaceHolder00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
)
