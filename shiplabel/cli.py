"""Command-line entry point: read a label from stdin (or a file) and
print the normalized form, or a pointed-to error on stderr.
"""

from __future__ import annotations

import sys

from .errors import LabelError
from .label import format_label


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    if argv:
        with open(argv[0], encoding="utf-8") as handle:
            text = handle.read()
    else:
        text = sys.stdin.read()

    try:
        print(format_label(text))
    except LabelError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
