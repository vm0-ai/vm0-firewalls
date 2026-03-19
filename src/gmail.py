#!/usr/bin/env python3
"""Generate gmail/firewall.yaml from Google's Discovery API.

Usage:
    python3 -m src.gmail
"""

from .google_common import generate_firewall

generate_firewall(
    discovery_url="https://gmail.googleapis.com/$discovery/rest?version=v1",
    base_url="https://gmail.googleapis.com/gmail/v1",
    path_prefix="gmail/v1",
    service_name="gmail",
    service_description="Gmail API",
    placeholder_key="GMAIL_TOKEN",
    placeholder_value="ya29.A0Vm0PlaceHolder-Vm0_PlaceHolder00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
)
