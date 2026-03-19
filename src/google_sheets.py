#!/usr/bin/env python3
"""Generate google-sheets/firewall.yaml from Google's Discovery API.

Usage:
    python3 -m src.google_sheets
"""

from .google_common import generate_firewall

generate_firewall(
    discovery_url="https://sheets.googleapis.com/$discovery/rest?version=v4",
    base_url="https://sheets.googleapis.com/v4",
    path_prefix="v4",
    service_name="google-sheets",
    service_description="Google Sheets API",
    placeholder_key="GOOGLE_SHEETS_TOKEN",
    placeholder_value="ya29.A0Vm0PlaceHolder-Vm0_PlaceHolder00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
)
