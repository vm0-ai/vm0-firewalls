#!/usr/bin/env python3
"""Validate all firewall.yaml files in the repository.

Mirrors the validation logic from firewall-expander.ts in vm0/turbo.
Run this in CI to catch errors before merge.

Usage:
    python3 validate.py
"""

import glob
import sys
import yaml


VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "ANY"}


def validate_rule(rule, perm_name, service_name):
    """Validate a single firewall rule string."""
    parts = rule.split(" ", 1)
    if len(parts) != 2 or not parts[1]:
        raise ValueError(
            f'Invalid rule "{rule}" in permission "{perm_name}" of firewall '
            f'"{service_name}": must be "METHOD /path"'
        )
    method, path = parts
    if method not in VALID_METHODS:
        raise ValueError(
            f'Invalid rule "{rule}" in permission "{perm_name}" of firewall '
            f'"{service_name}": unknown method "{method}" (must be uppercase)'
        )
    if not path.startswith("/"):
        raise ValueError(
            f'Invalid rule "{rule}" in permission "{perm_name}" of firewall '
            f'"{service_name}": path must start with "/"'
        )
    if "?" in path or "#" in path:
        raise ValueError(
            f'Invalid rule "{rule}" in permission "{perm_name}" of firewall '
            f'"{service_name}": path must not contain query string or fragment'
        )
    segments = [s for s in path.split("/") if s]
    param_names = set()
    for i, seg in enumerate(segments):
        if seg.startswith("{") and seg.endswith("}"):
            name = seg[1:-1]
            is_greedy = name.endswith("+") or name.endswith("*")
            base_name = name[:-1] if is_greedy else name
            if not base_name:
                raise ValueError(
                    f'Invalid rule "{rule}" in permission "{perm_name}" of firewall '
                    f'"{service_name}": empty parameter name'
                )
            if base_name in param_names:
                raise ValueError(
                    f'Invalid rule "{rule}" in permission "{perm_name}" of firewall '
                    f'"{service_name}": duplicate parameter name "{{{base_name}}}"'
                )
            param_names.add(base_name)
            if is_greedy and i != len(segments) - 1:
                raise ValueError(
                    f'Invalid rule "{rule}" in permission "{perm_name}" of firewall '
                    f'"{service_name}": {{{name}}} must be the last segment'
                )


def validate_base_url(base, service_name):
    """Validate a base URL."""
    from urllib.parse import urlparse

    parsed = urlparse(base)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(
            f'Invalid base URL "{base}" in firewall "{service_name}": not a valid URL'
        )
    if parsed.query:
        raise ValueError(
            f'Invalid base URL "{base}" in firewall "{service_name}": must not contain query string'
        )
    if parsed.fragment:
        raise ValueError(
            f'Invalid base URL "{base}" in firewall "{service_name}": must not contain fragment'
        )


def validate_firewall(filepath):
    """Validate a single firewall.yaml file."""
    with open(filepath) as f:
        config = yaml.safe_load(f)

    name = config.get("name", "")
    if not name:
        raise ValueError(f"{filepath}: firewall name is required")

    apis = config.get("apis", [])
    if not apis:
        raise ValueError(f'{filepath}: firewall "{name}" has no api entries')

    for api in apis:
        base = api.get("base", "")
        validate_base_url(base, name)

        permissions = api.get("permissions", [])
        if not permissions:
            raise ValueError(
                f'{filepath}: API entry "{base}" in firewall "{name}" has no permissions'
            )

        seen = set()
        for perm in permissions:
            perm_name = perm.get("name", "")
            if not perm_name:
                raise ValueError(
                    f'{filepath}: firewall "{name}" has a permission with empty name'
                )
            if perm_name == "all":
                raise ValueError(
                    f'{filepath}: firewall "{name}" has a permission named "all" '
                    "(reserved keyword)"
                )
            if perm_name in seen:
                raise ValueError(
                    f'{filepath}: duplicate permission name "{perm_name}" in API entry '
                    f'"{base}" of firewall "{name}"'
                )
            seen.add(perm_name)

            rules = perm.get("rules", [])
            if not rules:
                raise ValueError(
                    f'{filepath}: permission "{perm_name}" in firewall "{name}" has no rules'
                )
            for rule in rules:
                validate_rule(rule, perm_name, name)


def main():
    files = sorted(glob.glob("*/firewall.yaml"))
    if not files:
        print("No firewall.yaml files found", file=sys.stderr)
        sys.exit(1)

    errors = 0
    for filepath in files:
        try:
            validate_firewall(filepath)
            print(f"  ✓ {filepath}", file=sys.stderr)
        except Exception as e:
            print(f"  ✗ {filepath}: {e}", file=sys.stderr)
            errors += 1

    print(f"\n{len(files)} files checked, {errors} errors", file=sys.stderr)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
