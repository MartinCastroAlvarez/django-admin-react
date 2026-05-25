#!/usr/bin/env python
"""Django's command-line utility for administrative tasks (demo project)."""
import os
import sys
from pathlib import Path


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "examples.project.settings")
    # Make the repo root importable so `examples.*` apps resolve.
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you in the right virtualenv? "
            "Run `poetry install` from the repo root."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
