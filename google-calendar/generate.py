#!/usr/bin/env python3
"""Generate google-calendar/firewall.yaml from Google's Discovery API.

Usage:
    python3 google-calendar/generate.py
"""

import sys
sys.path.insert(0, sys.path[0] + "/..")
from google_common import generate_firewall

generate_firewall(
    discovery_url="https://www.googleapis.com/discovery/v1/apis/calendar/v3/rest",
    base_url="https://www.googleapis.com/calendar/v3",
    path_prefix="",
    service_name="google-calendar",
    service_description="Google Calendar API",
    placeholder_key="GOOGLE_CALENDAR_TOKEN",
    placeholder_value="ya29.A0Vm0PlaceHolder-Vm0_PlaceHolder00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
)
