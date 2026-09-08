"""Error type used across the package.

All parsing and normalization failures raise LabelError, which carries
enough information to point back at the exact spot in the input that
caused the problem instead of just saying "invalid label".
"""

from __future__ import annotations


class LabelError(ValueError):
    """A problem with a label, tied to a specific line and column.

    Columns are 1-based, matching how editors and `grep -n` report
    positions, so a user can jump straight to the offending character.
    """

    def __init__(
        self,
        message: str,
        source: str,
        line: int,
        column: int,
        length: int = 1,
    ) -> None:
        self.message = message
        self.source = source
        self.line = line
        self.column = column
        self.length = max(length, 1)
        super().__init__(self._render())

    def _render(self) -> str:
        lines = self.source.splitlines() or [""]
        index = self.line - 1
        line_text = lines[index] if 0 <= index < len(lines) else ""
        # Expand tabs before measuring so the caret lines up visually;
        # otherwise a single tab throws the column off by up to 7 chars.
        expanded = line_text.expandtabs()
        prefix_len = len(line_text[: self.column - 1].expandtabs())
        pointer = " " * prefix_len + "^" * self.length
        return (
            f"{self.message}\n"
            f"  line {self.line}, column {self.column}\n"
            f"    {expanded}\n"
            f"    {pointer}"
        )
