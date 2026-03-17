#!/usr/bin/env python3
"""Generate github/firewall.yaml from GitHub's official permissions data.

Data source: server-to-server-permissions.json from github/docs
(https://github.com/github/docs/tree/main/src/github-apps/data)

This JSON is the same data that powers the GitHub docs page:
https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens

It provides a definitive (verb, requestPath) → permission mapping with
access level (read/write) for every REST API endpoint.  No heuristics
or manual mapping needed — the classification is entirely data-driven.

Usage:
    python3 github/generate.py
"""

import json
import os
import sys
import urllib.request
from collections import defaultdict

PERMS_URL = (
    "https://raw.githubusercontent.com/github/docs/main/"
    "src/github-apps/data/fpt-2026-03-10/server-to-server-permissions.json"
)

# ── Path conversion ───────────────────────────────────────────────────────

# Parameters that may contain slashes → greedy suffix.
# {param+} = one or more segments, {param*} = zero or more segments.
_CATCH_ALL = [
    ("/contents/{path}", "/contents/{path*}"),
    ("/git/ref/{ref}", "/git/ref/{ref+}"),
    ("/git/refs/{ref}", "/git/refs/{ref+}"),
    ("/git/matching-refs/{ref}", "/git/matching-refs/{ref+}"),
    ("/compare/{basehead}", "/compare/{basehead+}"),
]

def _convert_path(path):
    """Add greedy suffix for parameters that may contain slashes."""
    for old, new in _CATCH_ALL:
        if path.endswith(old):
            return path[: -len(old)] + new
    return path


# ── Grouping ──────────────────────────────────────────────────────────────


def build_groups(perms_data):
    """Group endpoints into {perm-read/perm-write: set(rules)}.

    An endpoint may appear in multiple permission groups — this is correct.
    GitHub's model allows any of the listed permissions to grant access,
    and our firewall takes the union of all selected permissions.

    Returns (groups, descriptions).
    descriptions maps group_name → displayTitle from the source data.
    """
    groups = defaultdict(set)
    descriptions = {}

    for perm_key, entry in perms_data.items():
        display_title = entry.get("displayTitle", "")

        for ep in entry.get("permissions", []):
            verb = ep["verb"]
            path = ep["requestPath"]
            access = ep["access"]
            group_name = f"{perm_key.replace('_', '-')}-{access}"
            fw_path = _convert_path(path)
            rule = f"{verb.upper()} {fw_path}"
            groups[group_name].add(rule)

            if group_name not in descriptions:
                descriptions[group_name] = display_title

    return groups, descriptions


# ── YAML generation ───────────────────────────────────────────────────────

_METHOD_ORDER = {"GET": 0, "HEAD": 1, "POST": 2, "PUT": 3, "PATCH": 4, "DELETE": 5}


def _rule_key(rule):
    method, path = rule.split(" ", 1)
    return (path, _METHOD_ORDER.get(method, 9))


def _ordered_names(groups, perms_data):
    """Return permission group names ordered by source data iteration order."""
    ordered = []
    for perm_key in perms_data:
        for suffix in ("-read", "-write", "-admin"):
            name = f"{perm_key.replace('_', '-')}{suffix}"
            if name in groups and groups[name] and name not in ordered:
                ordered.append(name)
    # Anything missed (shouldn't happen)
    for name in sorted(groups):
        if name not in ordered and groups[name]:
            ordered.append(name)
    return ordered


def _emit_permissions(groups, descriptions, perms_data, lines):
    for name in _ordered_names(groups, perms_data):
        rules = sorted(groups[name], key=_rule_key)
        desc = descriptions.get(name, "")
        lines.append(f"      - name: {name}")
        if desc:
            lines.append(f"        description: {desc}")
        lines.append("        rules:")
        for r in rules:
            lines.append(f"          - {r}")


def render_yaml(groups, descriptions, perms_data):
    lines = [
        "# Auto-generated from GitHub's official permissions data.",
        "# Source: github/docs/src/github-apps/data/fpt-2026-03-10/"
        "server-to-server-permissions.json",
        "# Regenerate: python3 github/generate.py",
        "name: github",
        "description: GitHub API",
        "placeholders:",
        '  GITHUB_TOKEN: "gho_Vm0PlaceHolder0000000000000000000000"',
        '  GH_TOKEN: "gho_Vm0PlaceHolder0000000000000000000000"',
        "apis:",
        "  - base: https://api.github.com",
        "    auth:",
        "      headers:",
        '        Authorization: "Bearer ${{ secrets.GITHUB_TOKEN }}"',
        "    permissions:",
    ]
    _emit_permissions(groups, descriptions, perms_data, lines)

    # uploads.github.com — release asset upload endpoint.
    # Source: OpenAPI spec (api.github.com.json) operation-level servers override.
    # This is the only endpoint in the spec with a non-default base URL.
    lines += [
        "  - base: https://uploads.github.com",
        "    auth:",
        "      headers:",
        '        Authorization: "Bearer ${{ secrets.GITHUB_TOKEN }}"',
        "    permissions:",
        "      - name: contents-write",
        "        description: Upload release assets",
        "        rules:",
        "          - POST /repos/{owner}/{repo}/releases/{release_id}/assets",
    ]

    return "\n".join(lines) + "\n"


# ── Main ──────────────────────────────────────────────────────────────────


def main():
    print("Downloading GitHub permissions data…", file=sys.stderr)
    req = urllib.request.Request(PERMS_URL, headers={"User-Agent": "vm0-firewalls"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        perms_data = json.loads(resp.read())

    print(f"  {len(perms_data)} permissions", file=sys.stderr)

    groups, descriptions = build_groups(perms_data)
    yaml = render_yaml(groups, descriptions, perms_data)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "firewall.yaml")
    with open(out, "w") as f:
        f.write(yaml)

    total = sum(len(v) for v in groups.values())
    n_groups = len([v for v in groups.values() if v])
    print(f"  {n_groups} permission groups, {total} rules", file=sys.stderr)
    print(f"  Written to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
