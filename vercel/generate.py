#!/usr/bin/env python3
"""Generate vercel/firewall.yaml from Vercel's official OpenAPI spec.

Data source: https://openapi.vercel.sh/
(Official OpenAPI 3.0.3 spec served by Vercel.)

Permission groups are derived from the OpenAPI tags, split into read/write
based on HTTP method:
  - read:  GET, HEAD
  - write: POST, PUT, PATCH, DELETE

Usage:
    python3 vercel/generate.py
"""

import json
import os
import sys
import urllib.request
from collections import defaultdict

OPENAPI_URL = "https://openapi.vercel.sh/"

PLACEHOLDER_VALUE = "vcp_Vm0PlaceHolder000000000000000000000000000000000000000000"

# ── Grouping ─────────────────────────────────────────────────────────────

_READ_METHODS = {"get", "head"}
_WRITE_METHODS = {"post", "put", "patch", "delete"}
_ALL_METHODS = _READ_METHODS | _WRITE_METHODS

# Non-method keys allowed on OpenAPI path items (OpenAPI 3.0.3 spec §4.7.9)
_OPENAPI_PATH_KEYS = {
    "summary", "description", "servers", "parameters",  # path-level fields
    "$ref",                                              # JSON reference
    "options", "trace",                                  # HTTP methods we don't need
}


def build_groups(spec):
    """Extract endpoints from OpenAPI spec and group by tag:read / tag:write."""
    groups = defaultdict(set)
    if "paths" not in spec:
        raise ValueError("OpenAPI spec has no 'paths'")

    for path, methods in spec["paths"].items():
        for method_lower, op in methods.items():
            if method_lower not in _ALL_METHODS:
                if method_lower in _OPENAPI_PATH_KEYS or method_lower.startswith("x-"):
                    continue
                raise ValueError(f"Unexpected key '{method_lower}' on {path}")

            tags = op.get("tags")
            if not tags:
                raise ValueError(f"No tags on {method_lower.upper()} {path}")

            access = "read" if method_lower in _READ_METHODS else "write"
            rule = f"{method_lower.upper()} {path}"
            for tag in tags:
                groups[f"{tag}:{access}"].add(rule)

    return groups


# ── YAML generation ──────────────────────────────────────────────────────

_METHOD_ORDER = {"GET": 0, "HEAD": 1, "POST": 2, "PUT": 3, "PATCH": 4, "DELETE": 5}


def _rule_key(rule):
    method, path = rule.split(" ", 1)
    return (path, _METHOD_ORDER.get(method, 9))


def render_yaml(groups):
    lines = [
        "# Auto-generated from Vercel's official OpenAPI spec.",
        "# Source: https://openapi.vercel.sh/",
        "# Regenerate: python3 vercel/generate.py",
        "name: vercel",
        "description: Vercel API",
        "placeholders:",
        f'  VERCEL_TOKEN: "{PLACEHOLDER_VALUE}"',
        "apis:",
        "  - base: https://api.vercel.com",
        "    auth:",
        "      headers:",
        '        Authorization: "Bearer ${{ secrets.VERCEL_TOKEN }}"',
        "    permissions:",
    ]

    for group_name in sorted(groups):
        rules = sorted(groups[group_name], key=_rule_key)
        lines.append(f"      - name: {group_name}")
        lines.append("        rules:")
        for r in rules:
            lines.append(f"          - {r}")

    return "\n".join(lines) + "\n"


# ── Main ─────────────────────────────────────────────────────────────────


def main():
    print("Downloading Vercel OpenAPI spec…", file=sys.stderr)
    req = urllib.request.Request(OPENAPI_URL, headers={"User-Agent": "vm0-firewalls"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        spec = json.loads(resp.read())

    version = spec.get("info", {}).get("version", "?")
    print(f"  Spec version: {version}", file=sys.stderr)

    groups = build_groups(spec)
    yaml = render_yaml(groups)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "firewall.yaml")
    with open(out, "w") as f:
        f.write(yaml)

    total = sum(len(v) for v in groups.values())
    print(f"  {len(groups)} permission groups, {total} rules", file=sys.stderr)
    print(f"  Written to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
