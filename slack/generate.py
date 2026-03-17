#!/usr/bin/env python3
"""Generate slack/firewall.yaml from Slack API method-to-scope mappings.

Data source: slack-ruby/slack-api-ref (community-maintained, auto-synced daily
from docs.slack.dev). This is the only available machine-readable source for
Slack's method → scope mapping — Slack's official OpenAPI spec was archived
in 2024.

Repository: https://github.com/slack-ruby/slack-api-ref
Path:       docs.slack.dev/methods/*.json

Each method JSON file contains:
    { "scope": { "bot": ["chat:write"], "user": ["chat:write"] }, ... }

We group methods by bot scope to generate firewall permission groups.
Methods with no scope (like auth.test, oauth.*) are included in a
"no_scopes_required" group since they still require a valid token.

Usage:
    python3 slack/generate.py
"""

import json
import os
import sys
import tarfile
import urllib.request
from collections import defaultdict
from io import BytesIO

REPO_TARBALL_URL = (
    "https://github.com/slack-ruby/slack-api-ref/archive/refs/heads/master.tar.gz"
)


# ── Data loading ──────────────────────────────────────────────────────────


def download_methods():
    """Download and parse all method JSON files from slack-api-ref."""
    print("Downloading slack-api-ref…", file=sys.stderr)
    req = urllib.request.Request(REPO_TARBALL_URL, headers={"User-Agent": "vm0-firewalls"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        tarball = BytesIO(resp.read())

    methods = {}  # method_name → {scope, ...}
    prefix = "docs.slack.dev/methods/"
    with tarfile.open(fileobj=tarball, mode="r:gz") as tar:
        for member in tar.getmembers():
            # Path: slack-api-ref-master/docs.slack.dev/methods/chat.postMessage.json
            if prefix not in member.name or not member.name.endswith(".json"):
                continue
            fname = member.name.rsplit("/", 1)[-1]
            if fname == "methods.json":  # index file, skip
                continue
            method_name = fname[:-5]  # strip .json
            f = tar.extractfile(member)
            if f is None:
                continue
            data = json.load(f)
            if not isinstance(data, dict):
                continue
            methods[method_name] = data

    print(f"  {len(methods)} methods", file=sys.stderr)
    return methods


# ── Grouping ──────────────────────────────────────────────────────────────


def build_groups(methods):
    """Group methods by official Slack scopes (both bot and user).

    A method may appear in multiple scope groups — this matches Slack's
    model where any of the listed scopes grants access.

    Methods with no scope at all (api.test, oauth.*, etc.) are placed
    in a "no_scopes_required" group.

    Returns groups: {scope_name: set(rules)}.
    """
    groups = defaultdict(set)

    for method_name, data in methods.items():
        scope = data.get("scope", {})
        if not isinstance(scope, dict):
            continue

        bot_scopes = scope.get("bot", [])
        user_scopes = scope.get("user", [])
        all_scopes = set(bot_scopes) | set(user_scopes)
        rule = f"POST /{method_name}"

        if not all_scopes:
            groups["no_scopes_required"].add(rule)
            continue

        for s in all_scopes:
            groups[s].add(rule)

    return groups


# ── YAML generation ───────────────────────────────────────────────────────


def _ordered_names(groups):
    """Order: regular scopes sorted, then no_scopes_required at the end."""
    regular = sorted(k for k in groups if k != "no_scopes_required")
    result = regular
    if "no_scopes_required" in groups:
        result.append("no_scopes_required")
    return result


def render_yaml(groups):
    lines = [
        "# Auto-generated from Slack API method-to-scope mappings.",
        "# Source: slack-ruby/slack-api-ref (auto-synced daily from docs.slack.dev)",
        "# Regenerate: python3 slack/generate.py",
        "name: slack",
        "description: Slack API",
        "placeholders:",
        '  SLACK_TOKEN: "xoxb-000000000000-0000000000000-Vm0PlaceHolder0000000000"',
        "apis:",
        "  - base: https://slack.com/api",
        "    auth:",
        "      headers:",
        '        Authorization: "Bearer ${{ secrets.SLACK_TOKEN }}"',
        "    permissions:",
    ]

    for scope_name in _ordered_names(groups):
        rules = sorted(groups[scope_name])
        name = scope_name
        if scope_name == "no_scopes_required":
            desc = "Methods that require a valid token but no specific scope"
        else:
            desc = f'Slack scope "{scope_name}"'
        lines.append(f"      - name: {name}")
        lines.append(f"        description: {desc}")
        lines.append("        rules:")
        for r in rules:
            lines.append(f"          - {r}")

    # files.slack.com — file downloads use the same token
    lines += [
        "  - base: https://files.slack.com",
        "    auth:",
        "      headers:",
        '        Authorization: "Bearer ${{ secrets.SLACK_TOKEN }}"',
        "    permissions:",
        "      - name: files:read",
        '        description: Download files from Slack',
        "        rules:",
        "          - GET /{path+}",
    ]

    return "\n".join(lines) + "\n"


# ── Main ──────────────────────────────────────────────────────────────────


def main():
    methods = download_methods()
    groups = build_groups(methods)
    yaml = render_yaml(groups)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "firewall.yaml")
    with open(out, "w") as f:
        f.write(yaml)

    total = sum(len(v) for v in groups.values())
    n_groups = len(groups)
    print(f"  {n_groups} permission groups, {total} rules", file=sys.stderr)
    print(f"  Written to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
