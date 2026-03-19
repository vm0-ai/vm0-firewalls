#!/usr/bin/env python3
"""Generate notion/firewall.yaml from Notion's official OpenAPI spec.

Data sources:
- OpenAPI spec: https://developers.notion.com/openapi.json
  (Official spec served by Notion's docs site, provides endpoints + tags.)
- Endpoint docs: Each endpoint has an x-notion-docs-ref URL pointing to
  its documentation page.  Fetching {url}.md returns markdown that includes
  the required capability (e.g., "requires an integration to have read
  content capabilities").

Notion uses "capabilities" instead of OAuth scopes:
  read_content, update_content, insert_content,
  read_comments, insert_comments, read_users

For endpoints where the docs explicitly state the capability, we use that.
For endpoints where the docs don't mention a capability (newer endpoints),
we fall back to deterministic rules based on tag + HTTP method.

Usage:
    python3 -m src.notion
"""

import json
import os
import re
import sys
import urllib.request
from collections import defaultdict

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OPENAPI_URL = "https://developers.notion.com/openapi.json"

# ── Capability mapping ────────────────────────────────────────────────────
#
# Source: https://developers.notion.com/reference/capabilities

# Tags with their own capability category
_TAG_CATEGORY = {
    "Users": "users",
    "Comments": "comments",
}

# Tags to skip (not behind capabilities)
_SKIP_TAGS = {"OAuth"}

# Default method → access suffix for fallback rules
_METHOD_TO_ACCESS = {
    "GET": "read",
    "POST": "insert",
    "PATCH": "update",
    "PUT": "update",
    "DELETE": "update",
}

# Specific endpoints that don't follow the default method→access rule.
# Only used as fallback when docs don't specify.
_OVERRIDES = {
    ("POST", "/search"): "read",
    ("POST", "/pages/{page_id}/move"): "update",
}

# Normalize doc text → capability name
_DOC_TEXT_TO_CAPABILITY = {
    "read content": "read_content",
    "update content": "update_content",
    "insert content": "insert_content",
    "read comment": "read_comments",
    "read comments": "read_comments",
    "insert comment": "insert_comments",
    "insert comments": "insert_comments",
    "user information": "read_users",
}

# Format: ntn_[0-9]{11}[A-Za-z0-9]{32}[A-Za-z0-9]{3} (50 chars)
# Source: https://github.com/gitleaks/gitleaks/blob/master/config/gitleaks.toml
PLACEHOLDER_VALUE = "ntn_00000000000Vm0PlaceHolder000000000000000000Aaa"

CAPABILITY_DESCRIPTIONS = {
    "read_content": "Read pages, databases, blocks, data sources, and files",
    "update_content": "Update and delete pages, databases, blocks, and data sources",
    "insert_content": "Create pages, databases, blocks, data sources, and upload files",
    "read_comments": "Read comments",
    "insert_comments": "Create comments",
    "read_users": "Read user information",
}


# ── Capability extraction from docs ───────────────────────────────────────


def _fetch_capability_from_docs(docs_url):
    """Fetch endpoint markdown and extract capability requirement.

    Returns capability name (e.g., "read_content") or None if not found.
    """
    try:
        md_url = docs_url + ".md"
        req = urllib.request.Request(md_url, headers={"User-Agent": "vm0-firewalls"})
        content = urllib.request.urlopen(req, timeout=10).read().decode()
        match = re.search(r"requires an integration to have (.+?) capabilit", content)
        if match:
            text = match.group(1).strip()
            cap = _DOC_TEXT_TO_CAPABILITY.get(text)
            if not cap:
                print(f"  Warning: unrecognized capability text '{text}' in {docs_url}", file=sys.stderr)
            return cap
    except Exception:
        pass
    return None


# ── Fallback classification ───────────────────────────────────────────────


def _classify_by_rules(method, path, tag):
    """Fallback: determine capability from tag + HTTP method."""
    if tag in _SKIP_TAGS:
        return None
    access = _OVERRIDES.get((method, path), _METHOD_TO_ACCESS.get(method))
    if not access:
        raise ValueError(f"Unknown HTTP method: {method}")
    category = _TAG_CATEGORY.get(tag, "content")
    return f"{access}_{category}"


# ── Grouping ──────────────────────────────────────────────────────────────


def build_groups(spec):
    """Extract endpoints from OpenAPI spec and classify by capability."""
    groups = defaultdict(set)
    doc_found = 0
    fallback_used = 0

    for spec_path, methods in spec.get("paths", {}).items():
        rel_path = spec_path[len("/v1"):] if spec_path.startswith("/v1") else spec_path

        for method_lower in ("get", "post", "put", "patch", "delete"):
            if method_lower not in methods:
                continue
            method = method_lower.upper()
            op = methods[method_lower]
            tag = op.get("tags", [""])[0]

            if tag in _SKIP_TAGS:
                continue

            # Try docs first
            docs_url = op.get("x-notion-docs-ref", "")
            cap = _fetch_capability_from_docs(docs_url) if docs_url else None

            if cap:
                doc_found += 1
            else:
                # Fallback to rules
                cap = _classify_by_rules(method, rel_path, tag)
                if cap is None:
                    continue
                fallback_used += 1

            groups[cap].add(f"{method} {rel_path}")

    print(f"  Capabilities: {doc_found} from docs, {fallback_used} from rules", file=sys.stderr)
    return groups


# ── YAML generation ───────────────────────────────────────────────────────

_METHOD_ORDER = {"GET": 0, "HEAD": 1, "POST": 2, "PUT": 3, "PATCH": 4, "DELETE": 5}


def _rule_key(rule):
    method, path = rule.split(" ", 1)
    return (path, _METHOD_ORDER.get(method, 9))


def render_yaml(groups):
    lines = [
        "# Auto-generated from Notion's official OpenAPI spec + endpoint docs.",
        "# Source: https://developers.notion.com/openapi.json",
        "# Capability mapping: extracted from endpoint docs (x-notion-docs-ref)",
        "# with rule-based fallback for undocumented endpoints.",
        "# Regenerate: python3 -m src.notion",
        "name: notion",
        "description: Notion API",
        "placeholders:",
        f'  NOTION_TOKEN: "{PLACEHOLDER_VALUE}"',
        "apis:",
        "  - base: https://api.notion.com/v1",
        "    auth:",
        "      headers:",
        '        Authorization: "Bearer ${{ secrets.NOTION_TOKEN }}"',
        "    permissions:",
    ]

    for cap_name in sorted(groups):
        rules = sorted(groups[cap_name], key=_rule_key)
        desc = CAPABILITY_DESCRIPTIONS.get(cap_name)
        if not desc:
            raise ValueError(f'Unknown capability "{cap_name}" — update CAPABILITY_DESCRIPTIONS')
        lines.append(f"      - name: {cap_name}")
        lines.append(f"        description: {desc}")
        lines.append("        rules:")
        for r in rules:
            lines.append(f"          - {r}")

    return "\n".join(lines) + "\n"


# ── Main ──────────────────────────────────────────────────────────────────


def main():
    print("Downloading Notion OpenAPI spec…", file=sys.stderr)
    req = urllib.request.Request(OPENAPI_URL, headers={"User-Agent": "vm0-firewalls"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        spec = json.loads(resp.read())

    print(f"  Spec version: {spec.get('info', {}).get('version', '?')}", file=sys.stderr)

    groups = build_groups(spec)
    yaml = render_yaml(groups)

    out = os.path.join(REPO_ROOT, "notion", "firewall.yaml")
    with open(out, "w") as f:
        f.write(yaml)

    total = sum(len(v) for v in groups.values())
    print(f"  {len(groups)} permission groups, {total} rules", file=sys.stderr)
    print(f"  Written to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
