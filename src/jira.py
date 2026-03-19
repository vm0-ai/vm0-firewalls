#!/usr/bin/env python3
"""Generate jira/firewall.yaml from Jira Cloud's official OpenAPI spec.

Data source: https://developer.atlassian.com/cloud/jira/platform/swagger-v3.v3.json
(Official OpenAPI 3.0.1 spec from Atlassian.)

Permission groups are derived from OAuth 2.0 (3LO) classic scopes annotated
on each endpoint in the spec's security requirements:
  read:jira-user, read:jira-work, write:jira-work,
  manage:jira-project, manage:jira-configuration, manage:jira-webhook

Endpoints with empty scopes [] or without OAuth2 security are skipped.

Usage:
    python3 -m src.jira
"""

import json
import os
import sys
import urllib.request
from collections import defaultdict

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OPENAPI_URL = (
    "https://developer.atlassian.com/cloud/jira/platform/swagger-v3.v3.json"
)

# Format: ATATT3[A-Za-z0-9_\-=]{186} (192 chars total)
# Source: https://github.com/gitleaks/gitleaks/blob/master/config/gitleaks.toml
PLACEHOLDER_VALUE = "ATATT3xVm0PlaceHolder000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"


# ── Grouping ─────────────────────────────────────────────────────────────

_ALL_METHODS = {"get", "head", "post", "put", "patch", "delete"}

# Non-method keys allowed on OpenAPI path items (OpenAPI 3.0.1 spec)
_OPENAPI_PATH_KEYS = {"summary", "description", "servers", "parameters", "$ref",
                       "options", "trace"}


def _extract_scope_descriptions(spec):
    """Extract scope descriptions from the OpenAPI spec's OAuth2 security scheme."""
    scopes = (spec.get("components", {})
              .get("securitySchemes", {})
              .get("OAuth2", {})
              .get("flows", {})
              .get("authorizationCode", {})
              .get("scopes", {}))
    descs = {k: v for k, v in scopes.items()}
    return descs


def build_groups(spec):
    """Extract endpoints from OpenAPI spec and group by OAuth scope."""
    groups = defaultdict(set)
    if "paths" not in spec:
        raise ValueError("OpenAPI spec has no 'paths'")

    for path, methods in spec["paths"].items():
        for method_lower, op in methods.items():
            if not isinstance(op, dict):
                continue
            if method_lower not in _ALL_METHODS:
                if method_lower in _OPENAPI_PATH_KEYS or method_lower.startswith("x-"):
                    continue
                raise ValueError(f"Unexpected key '{method_lower}' on {path}")

            # Find OAuth2 scopes
            security = op.get("security", [])
            oauth_scopes = None
            for s in security:
                if "OAuth2" in s:
                    oauth_scopes = s["OAuth2"]
                    break

            if oauth_scopes is None:
                # No OAuth2 security (basicAuth-only, Connect/Forge apps) → skip
                continue

            rule = f"{method_lower.upper()} /ex/jira/{{cloudId}}{path}"

            if not oauth_scopes:
                continue
            for scope in oauth_scopes:
                groups[scope].add(rule)

    return groups


# ── YAML generation ──────────────────────────────────────────────────────

_METHOD_ORDER = {"GET": 0, "HEAD": 1, "POST": 2, "PUT": 3, "PATCH": 4, "DELETE": 5}

# Scope display order: read → write → manage
_SCOPE_ORDER = {
    "read:jira-user": 0,
    "read:jira-work": 1,
    "write:jira-work": 2,
    "manage:jira-project": 3,
    "manage:jira-configuration": 4,
    "manage:jira-webhook": 5,
}


def _rule_key(rule):
    method, path = rule.split(" ", 1)
    return (path, _METHOD_ORDER.get(method, 9))


def render_yaml(groups, scope_descriptions):
    lines = [
        "# Auto-generated from Jira Cloud's official OpenAPI spec.",
        "# Source: https://developer.atlassian.com/cloud/jira/platform/swagger-v3.v3.json",
        "# Scopes: OAuth 2.0 (3LO) classic scopes from spec security annotations.",
        "# Regenerate: python3 -m src.jira",
        "name: jira",
        "description: Jira Cloud API",
        "placeholders:",
        f'  JIRA_TOKEN: "{PLACEHOLDER_VALUE}"',
        "apis:",
        "  - base: https://api.atlassian.com",
        "    auth:",
        "      headers:",
        '        Authorization: "Bearer ${{ secrets.JIRA_TOKEN }}"',
        "    permissions:",
    ]

    for scope in sorted(groups, key=lambda s: _SCOPE_ORDER.get(s, 99)):
        if scope not in _SCOPE_ORDER:
            raise ValueError(f'Unknown scope "{scope}" — update _SCOPE_ORDER')
        rules = sorted(groups[scope], key=_rule_key)
        desc = scope_descriptions.get(scope)
        if not desc:
            raise ValueError(f'Unknown scope "{scope}" — not found in OpenAPI spec')
        lines.append(f"      - name: {scope}")
        lines.append(f"        description: {desc}")
        lines.append("        rules:")
        for r in rules:
            lines.append(f"          - {r}")

    return "\n".join(lines) + "\n"


# ── Main ─────────────────────────────────────────────────────────────────


def main():
    print("Downloading Jira OpenAPI spec…", file=sys.stderr)
    req = urllib.request.Request(OPENAPI_URL, headers={"User-Agent": "vm0-firewalls"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        spec = json.loads(resp.read())

    version = spec.get("info", {}).get("version", "?")
    print(f"  Spec version: {version}", file=sys.stderr)

    groups = build_groups(spec)
    scope_descriptions = _extract_scope_descriptions(spec)
    yaml = render_yaml(groups, scope_descriptions)

    out = os.path.join(REPO_ROOT, "jira", "firewall.yaml")
    with open(out, "w") as f:
        f.write(yaml)

    total = sum(len(v) for v in groups.values())
    print(f"  {len(groups)} permission groups, {total} rules", file=sys.stderr)
    print(f"  Written to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
