#!/usr/bin/env python3
"""Generate figma/firewall.yaml from Figma's official OpenAPI spec.

Data source: https://github.com/figma/rest-api-spec
Spec file: openapi/openapi.yaml (OpenAPI 3.1.0)

Permission groups are derived from OAuth 2.0 scopes annotated on each
endpoint in the spec's security requirements.

Endpoints without OAuth2 security (PAT-only) are skipped.

Usage:
    python3 figma/generate.py
"""

import os
import sys
import urllib.request
from collections import defaultdict

import yaml

OPENAPI_URL = (
    "https://raw.githubusercontent.com/figma/rest-api-spec/main/openapi/openapi.yaml"
)

# Figma PAT prefix: figd_ (not officially documented, may change).
# Source: https://forum.figma.com/ask-the-community-7/is-it-guaranteed-that-all-personal-access-tokens-start-with-figd-33218
PLACEHOLDER_VALUE = "figd_Vm0PlaceHolder00000000000000000000000000"

# OAuth security scheme keys in the spec
_OAUTH_KEYS = {"OAuth2", "OrgOAuth2"}

# ── Grouping ─────────────────────────────────────────────────────────────

_ALL_METHODS = {"get", "head", "post", "put", "patch", "delete"}

_OPENAPI_PATH_KEYS = {"summary", "description", "servers", "parameters", "$ref",
                       "options", "trace"}

# Scopes used on endpoints in the current spec.
_KNOWN_SCOPES = {
    "current_user:read",
    "file_comments:read",
    "file_comments:write",
    "file_content:read",
    "file_dev_resources:read",
    "file_dev_resources:write",
    "file_metadata:read",
    "file_variables:read",
    "file_variables:write",
    "file_versions:read",
    "files:read",
    "library_analytics:read",
    "library_assets:read",
    "library_content:read",
    "org:activity_log_read",
    "projects:read",
    "team_library_content:read",
    "webhooks:read",
    "webhooks:write",
}


def _extract_scope_descriptions(spec):
    """Extract scope descriptions from the OpenAPI spec's OAuth2 security schemes."""
    descs = {}
    for scheme_key in _OAUTH_KEYS:
        scheme = (spec.get("components", {})
                  .get("securitySchemes", {})
                  .get(scheme_key, {}))
        for flow in scheme.get("flows", {}).values():
            descs.update(flow.get("scopes", {}))
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

            # Find OAuth scopes from any OAuth scheme
            security = op.get("security", [])
            oauth_scopes = None
            for s in security:
                for key in _OAUTH_KEYS:
                    if key in s:
                        oauth_scopes = s[key]
                        break
                if oauth_scopes is not None:
                    break

            if oauth_scopes is None or not oauth_scopes:
                continue

            rule = f"{method_lower.upper()} {path}"
            for scope in oauth_scopes:
                if scope not in _KNOWN_SCOPES:
                    raise ValueError(f'Unknown scope "{scope}" — update _KNOWN_SCOPES')
                groups[scope].add(rule)

    return groups


# ── YAML generation ──────────────────────────────────────────────────────

_METHOD_ORDER = {"GET": 0, "HEAD": 1, "POST": 2, "PUT": 3, "PATCH": 4, "DELETE": 5}


def _rule_key(rule):
    method, path = rule.split(" ", 1)
    return (path, _METHOD_ORDER.get(method, 9))


def render_yaml(groups, scope_descriptions):
    lines = [
        "# Auto-generated from Figma's official OpenAPI spec.",
        "# Source: https://github.com/figma/rest-api-spec",
        "# Scopes: OAuth 2.0 scopes from spec security annotations.",
        "# Regenerate: python3 figma/generate.py",
        "name: figma",
        "description: Figma API",
        "placeholders:",
        f'  FIGMA_TOKEN: "{PLACEHOLDER_VALUE}"',
        "apis:",
        "  - base: https://api.figma.com",
        "    auth:",
        "      headers:",
        '        Authorization: "Bearer ${{ secrets.FIGMA_TOKEN }}"',
        "    permissions:",
    ]

    for scope in sorted(groups):
        if scope not in scope_descriptions:
            raise ValueError(f'Unknown scope "{scope}" — not found in OpenAPI spec')
        rules = sorted(groups[scope], key=_rule_key)
        desc = scope_descriptions[scope]
        lines.append(f"      - name: {scope}")
        # Quote description to avoid YAML parsing issues with colons
        escaped_desc = desc.replace('"', '\\"')
        lines.append(f'        description: "{escaped_desc}"')
        lines.append("        rules:")
        for r in rules:
            lines.append(f"          - {r}")

    return "\n".join(lines) + "\n"


# ── Main ─────────────────────────────────────────────────────────────────


def main():
    print("Downloading Figma OpenAPI spec…", file=sys.stderr)
    req = urllib.request.Request(OPENAPI_URL, headers={"User-Agent": "vm0-firewalls"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        spec = yaml.safe_load(resp.read())

    version = spec.get("info", {}).get("version", "?")
    print(f"  Spec version: {version}", file=sys.stderr)

    groups = build_groups(spec)
    scope_descriptions = _extract_scope_descriptions(spec)
    yaml_out = render_yaml(groups, scope_descriptions)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "firewall.yaml")
    with open(out, "w") as f:
        f.write(yaml_out)

    total = sum(len(v) for v in groups.values())
    print(f"  {len(groups)} permission groups, {total} rules", file=sys.stderr)
    print(f"  Written to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
