"""Shared logic for generating firewall.yaml from Google Discovery API documents.

All Google APIs (Gmail, Sheets, Docs, Drive, Calendar) use the same Discovery
API format with the same structure: resources → methods → {path, httpMethod, scopes}.

Usage from a service-specific generate.py:

    from google_common import generate_firewall

    generate_firewall(
        discovery_url="https://gmail.googleapis.com/$discovery/rest?version=v1",
        base_url="https://gmail.googleapis.com/gmail/v1",
        path_prefix="gmail/v1",
        service_name="gmail",
        service_description="Gmail API",
        placeholder_key="GMAIL_TOKEN",
        placeholder_value="ya29.Vm0PlaceHolder0...",
    )
"""

import json
import os
import sys
import urllib.request
from collections import defaultdict

# Short scope names: strip the common prefix for readable permission names.
_SCOPE_PREFIX = "https://www.googleapis.com/auth/"

# Some Google APIs use non-standard full-access scope URLs.
# Map them to readable short names.
_SPECIAL_SCOPES = {
    "https://mail.google.com/": "mail.google.com",
    "https://www.googleapis.com/auth/drive": "drive",
    "https://www.googleapis.com/auth/calendar": "calendar",
}


def _short_scope(scope):
    """Convert full scope URL to a short name for the permission group."""
    if scope in _SPECIAL_SCOPES:
        return _SPECIAL_SCOPES[scope]
    if scope.startswith(_SCOPE_PREFIX):
        return scope[len(_SCOPE_PREFIX):]
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


def _build_groups(discovery, path_prefix):
    """Group endpoints by scope.

    path_prefix is stripped from each method path so rules are relative
    to the base URL.  E.g., path_prefix="gmail/v1" turns
    "gmail/v1/users/{userId}/messages" into "/users/{userId}/messages".

    Returns groups: {scope_short_name: set(rules)}.
    """
    groups = defaultdict(set)
    strip = (path_prefix + "/") if path_prefix else ""

    for method in _extract_methods(discovery.get("resources", {})):
        http_method = method.get("httpMethod")
        path = method.get("path")
        scopes = method.get("scopes")

        if not http_method or not path:
            raise ValueError(f"Method missing httpMethod or path: {method.get('id')}")
        if not scopes:
            raise ValueError(f"Method has no scopes: {http_method} /{path}")

        if strip:
            if not path.startswith(strip):
                raise ValueError(
                    f'Method path "{path}" does not start with '
                    f'expected prefix "{strip}" — check path_prefix'
                )
            path = path[len(strip):]

        rule = f"{http_method.upper()} /{path}"
        for scope in scopes:
            groups[_short_scope(scope)].add(rule)

    return groups


# ── YAML generation ───────────────────────────────────────────────────────

_METHOD_ORDER = {"GET": 0, "HEAD": 1, "POST": 2, "PUT": 3, "PATCH": 4, "DELETE": 5}


def _rule_key(rule):
    method, path = rule.split(" ", 1)
    return (path, _METHOD_ORDER.get(method, 9))


def _render_yaml(groups, discovery, base_url, service_name, service_description,
                 placeholder_key, placeholder_value, discovery_url):
    # Get scope descriptions from discovery doc
    scope_descs = {}
    for scope_url, info in (
        discovery.get("auth", {}).get("oauth2", {}).get("scopes", {}).items()
    ):
        scope_descs[_short_scope(scope_url)] = info.get("description", "")

    lines = [
        "# Auto-generated from Google's Discovery API.",
        f"# Source: {discovery_url}",
        f"# Regenerate: python3 {service_name}/generate.py",
        f"name: {service_name}",
        f"description: {service_description}",
        "placeholders:",
        f'  {placeholder_key}: "{placeholder_value}"',
        "apis:",
        f"  - base: {base_url}",
        "    auth:",
        "      headers:",
        f'        Authorization: "Bearer ${{{{ secrets.{placeholder_key} }}}}"',
        "    permissions:",
    ]

    for scope_name in sorted(groups):
        rules = sorted(groups[scope_name], key=_rule_key)
        desc = scope_descs.get(scope_name, "")
        lines.append(f"      - name: {scope_name}")
        if desc:
            lines.append(f"        description: {desc}")
        lines.append("        rules:")
        for r in rules:
            lines.append(f"          - {r}")

    return "\n".join(lines) + "\n"


# ── Public entry point ────────────────────────────────────────────────────


def generate_firewall(
    discovery_url,
    base_url,
    path_prefix,
    service_name,
    service_description,
    placeholder_key,
    placeholder_value,
):
    """Download discovery doc and generate firewall.yaml.

    Args:
        discovery_url: URL to fetch the discovery JSON from.
        base_url: The firewall base URL (includes version, e.g.,
            "https://gmail.googleapis.com/gmail/v1").
        path_prefix: Prefix to strip from discovery method paths so rules
            are relative to base_url (e.g., "gmail/v1").  Use "" if paths
            are already relative (Drive, Calendar).
        service_name: Directory name and firewall name.
        service_description: Human-readable description.
        placeholder_key: Environment variable name for the token.
        placeholder_value: Placeholder token value.
    """
    print(f"Downloading {service_name} discovery document…", file=sys.stderr)
    req = urllib.request.Request(
        discovery_url, headers={"User-Agent": "vm0-firewalls"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        discovery = json.loads(resp.read())

    version = discovery.get("version", "unknown")
    print(f"  API version: {version}", file=sys.stderr)

    groups = _build_groups(discovery, path_prefix)
    yaml_content = _render_yaml(
        groups, discovery, base_url, service_name, service_description,
        placeholder_key, placeholder_value, discovery_url,
    )

    out = os.path.join(
        os.path.dirname(os.path.abspath(sys.argv[0])), "firewall.yaml"
    )
    with open(out, "w") as f:
        f.write(yaml_content)

    total = sum(len(v) for v in groups.values())
    print(f"  {len(groups)} permission groups, {total} rules", file=sys.stderr)
    print(f"  Written to {out}", file=sys.stderr)
