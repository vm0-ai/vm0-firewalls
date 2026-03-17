#!/usr/bin/env python3
"""Generate gmail/firewall.yaml from Google's Discovery API.

Data source: Gmail API v1 discovery document
https://gmail.googleapis.com/$discovery/rest?version=v1

This is Google's official, publicly-accessible JSON describing every
Gmail REST endpoint with its path, HTTP method, and required OAuth scopes.

Each method's `scopes` array lists alternative scopes — any one of them
grants access. We place each endpoint in every scope group it belongs to
(same approach as GitHub and Slack firewalls).

Usage:
    python3 gmail/generate.py
"""

import json
import os
import sys
import urllib.request
from collections import defaultdict

DISCOVERY_URL = "https://gmail.googleapis.com/$discovery/rest?version=v1"

# Short scope names: strip the common prefix for readable permission names.
_SCOPE_PREFIX = "https://www.googleapis.com/auth/"
_FULL_ACCESS_SCOPE = "https://mail.google.com/"


def _short_scope(scope):
    """Convert full scope URL to a short name for the permission group."""
    if scope == _FULL_ACCESS_SCOPE:
        return "mail.google.com"
    if scope.startswith(_SCOPE_PREFIX):
        return scope[len(_SCOPE_PREFIX) :]
    return scope


# ── Discovery document parsing ────────────────────────────────────────────


def _extract_methods(resources):
    """Recursively extract all methods from the discovery document."""
    methods = []
    for resource in resources.values():
        for method in resource.get("methods", {}).values():
            methods.append(method)
        if "resources" in resource:
            methods.extend(_extract_methods(resource["resources"]))
    return methods


# ── Grouping ──────────────────────────────────────────────────────────────


def build_groups(discovery):
    """Group endpoints by scope.

    Returns groups: {scope_short_name: set(rules)}.
    """
    groups = defaultdict(set)

    for method in _extract_methods(discovery.get("resources", {})):
        http_method = method.get("httpMethod")
        path = method.get("path")
        scopes = method.get("scopes")

        if not http_method or not path:
            raise ValueError(f"Method missing httpMethod or path: {method.get('id')}")
        if not scopes:
            raise ValueError(f"Method has no scopes: {http_method} /{path}")

        rule = f"{http_method.upper()} /{path}"
        for scope in scopes:
            groups[_short_scope(scope)].add(rule)

    return groups


# ── YAML generation ───────────────────────────────────────────────────────

_METHOD_ORDER = {"GET": 0, "HEAD": 1, "POST": 2, "PUT": 3, "PATCH": 4, "DELETE": 5}


def _rule_key(rule):
    method, path = rule.split(" ", 1)
    return (path, _METHOD_ORDER.get(method, 9))


def render_yaml(groups, discovery):
    # Get scope descriptions from discovery doc
    scope_descs = {}
    for scope_url, info in (
        discovery.get("auth", {}).get("oauth2", {}).get("scopes", {}).items()
    ):
        scope_descs[_short_scope(scope_url)] = info.get("description", "")

    lines = [
        "# Auto-generated from Google's Discovery API.",
        "# Source: https://gmail.googleapis.com/$discovery/rest?version=v1",
        "# Regenerate: python3 gmail/generate.py",
        "name: gmail",
        "description: Gmail API",
        "placeholders:",
        '  GMAIL_TOKEN: "ya29.Vm0PlaceHolder000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"',
        "apis:",
        "  - base: https://gmail.googleapis.com",
        "    auth:",
        "      headers:",
        '        Authorization: "Bearer ${{ secrets.GMAIL_TOKEN }}"',
        "    permissions:",
    ]

    # Order: mail.google.com first (full access), then sorted by scope name
    ordered = []
    if "mail.google.com" in groups:
        ordered.append("mail.google.com")
    for name in sorted(groups):
        if name != "mail.google.com":
            ordered.append(name)

    for scope_name in ordered:
        rules = sorted(groups[scope_name], key=_rule_key)
        desc = scope_descs.get(scope_name, "")
        lines.append(f"      - name: {scope_name}")
        if desc:
            lines.append(f"        description: {desc}")
        lines.append("        rules:")
        for r in rules:
            lines.append(f"          - {r}")

    return "\n".join(lines) + "\n"


# ── Main ──────────────────────────────────────────────────────────────────


def main():
    print("Downloading Gmail discovery document…", file=sys.stderr)
    req = urllib.request.Request(
        DISCOVERY_URL, headers={"User-Agent": "vm0-firewalls"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        discovery = json.loads(resp.read())

    version = discovery.get("version", "unknown")
    print(f"  API version: {version}", file=sys.stderr)

    groups = build_groups(discovery)
    yaml = render_yaml(groups, discovery)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "firewall.yaml")
    with open(out, "w") as f:
        f.write(yaml)

    total = sum(len(v) for v in groups.values())
    print(f"  {len(groups)} permission groups, {total} rules", file=sys.stderr)
    print(f"  Written to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
