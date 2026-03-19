#!/usr/bin/env python3
"""Run all firewall generators.

Usage:
    python3 -m src.all
"""

import glob
import os
import subprocess
import sys

# Modules to exclude (not generators)
_EXCLUDE = {"__init__", "all", "validate", "google_common"}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _discover_generators():
    """Find all generator modules in src/ by scanning .py files."""
    modules = []
    for path in sorted(glob.glob(os.path.join(REPO_ROOT, "src", "*.py"))):
        name = os.path.basename(path)[:-3]  # strip .py
        if name not in _EXCLUDE:
            modules.append(f"src.{name}")
    return modules


def main():
    generators = _discover_generators()
    if not generators:
        print("No generators found", file=sys.stderr)
        sys.exit(1)

    failed = []
    for module in generators:
        result = subprocess.run([sys.executable, "-m", module])
        if result.returncode != 0:
            failed.append(module)

    print(file=sys.stderr)
    if failed:
        print(f"{len(failed)} generators failed: {', '.join(failed)}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"All {len(generators)} generators completed successfully.", file=sys.stderr)


if __name__ == "__main__":
    main()
