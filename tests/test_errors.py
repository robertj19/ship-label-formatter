"""Tests for LabelError's line/column/length, the whole point of this
library. Most cases go through the public parsing functions so a
regression here means a user-visible one; a couple of branches (a
blank name line, a blank country line) can't actually be reached that
way, since both entry points always trim blank lines off the ends of
a block before it reaches _normalize_body, so those go straight at
the internal function.
"""

from __future__ import annotations

import unittest

from shiplabel import LabelError, format_label, parse_batch
from shiplabel.label import _normalize_body


def underline(source: str, exc: LabelError) -> str:
    """The exact substring exc's line/column/length points at, so tests
    can assert on the text that's wrong rather than hand-computed
    column numbers.
    """
    line = source.splitlines()[exc.line - 1]
    return line[exc.column - 1 : exc.column - 1 + exc.length]


class TooFewOrManyLinesTests(unittest.TestCase):
    def test_too_few_lines_points_at_last_line(self):
        text = "Jane Doe\n500 5th Ave"
        with self.assertRaises(LabelError) as ctx:
            format_label(text)
        self.assertEqual(ctx.exception.line, 2)
        self.assertEqual(ctx.exception.column, 1)

    def test_too_many_lines_points_at_first_extra_line(self):
        text = "Jane Doe\n500 5th Ave\nApt 4\nExtra Line\nNew York, NY 10110\nUS"
        with self.assertRaises(LabelError) as ctx:
            format_label(text)
        self.assertEqual(ctx.exception.line, 6)
        self.assertEqual(underline(text, ctx.exception), "US")


class BlankLineTests(unittest.TestCase):
    def test_blank_interior_street_line(self):
        text = "Jane Doe\n\n500 5th Ave\nNew York, NY 10110"
        with self.assertRaises(LabelError) as ctx:
            format_label(text)
        self.assertEqual(ctx.exception.line, 2)
        self.assertEqual(ctx.exception.column, 1)
        self.assertIn("blank", ctx.exception.message)

    def test_blank_name_line(self):
        # Unreachable via format_label/parse_batch: both trim blank
        # lines off the front of a block before this point is reached.
        source = "\n500 5th Ave\nNew York, NY 10110"
        with self.assertRaises(LabelError) as ctx:
            _normalize_body(source.splitlines(), source, 1)
        self.assertEqual(ctx.exception.line, 1)
        self.assertEqual(ctx.exception.column, 1)

    def test_blank_country_line(self):
        # Unreachable the same way: a trailing blank line is always
        # trimmed before _normalize_body sees it.
        body = ["Jane Doe", "500 5th Ave", "Apt 4", "New York, NY 10110", ""]
        source = "\n".join(body)
        with self.assertRaises(LabelError) as ctx:
            _normalize_body(body, source, 1)
        self.assertEqual(ctx.exception.line, 5)
        self.assertEqual(ctx.exception.column, 1)


class CityStateZipTests(unittest.TestCase):
    def test_city_missing_before_comma(self):
        text = "Jane Doe\n500 5th Ave\n, NY 10110"
        with self.assertRaises(LabelError) as ctx:
            format_label(text)
        self.assertEqual(ctx.exception.line, 3)
        self.assertEqual(ctx.exception.column, 1)
        self.assertIn("city", ctx.exception.message)

    def test_only_state_after_comma_points_at_state_not_the_comma(self):
        text = "Jane Doe\n500 5th Ave\nNew York, NY"
        with self.assertRaises(LabelError) as ctx:
            format_label(text)
        self.assertEqual(ctx.exception.line, 3)
        self.assertEqual(underline(text, ctx.exception), "NY")

    def test_nothing_after_comma(self):
        text = "Jane Doe\n500 5th Ave\nNew York,"
        with self.assertRaises(LabelError) as ctx:
            format_label(text)
        self.assertEqual(ctx.exception.line, 3)
        self.assertEqual(ctx.exception.length, 1)

    def test_too_few_tokens_without_comma(self):
        text = "Jane Doe\n500 5th Ave\n  New York"
        with self.assertRaises(LabelError) as ctx:
            format_label(text)
        self.assertEqual(ctx.exception.line, 3)
        self.assertEqual(underline(text, ctx.exception), "New York")

    def test_unrecognized_state(self):
        text = "Jane Doe\n500 5th Ave\nNew York, ZZ 10110"
        with self.assertRaises(LabelError) as ctx:
            format_label(text)
        self.assertEqual(ctx.exception.line, 3)
        self.assertEqual(underline(text, ctx.exception), "ZZ")

    def test_invalid_zip(self):
        text = "Jane Doe\n500 5th Ave\nNew York, NY 1011"
        with self.assertRaises(LabelError) as ctx:
            format_label(text)
        self.assertEqual(ctx.exception.line, 3)
        self.assertEqual(underline(text, ctx.exception), "1011")


class CountryTests(unittest.TestCase):
    def test_unrecognized_country(self):
        text = "Jane Doe\n500 5th Ave\nNew York, NY 10110\nZanzibar"
        with self.assertRaises(LabelError) as ctx:
            format_label(text)
        self.assertEqual(ctx.exception.line, 4)
        self.assertEqual(underline(text, ctx.exception), "Zanzibar")


class BatchLineNumberTests(unittest.TestCase):
    def test_error_line_is_relative_to_whole_file(self):
        text = (
            "Jane Doe\n500 5th Ave\nNew York, NY 10110\n"
            "\n"
            "John Smith\n1 Infinite Loop\nCupertino, CA ABCDE"
        )
        with self.assertRaises(LabelError) as ctx:
            parse_batch(text)
        self.assertEqual(ctx.exception.line, 7)
        self.assertEqual(underline(text, ctx.exception), "ABCDE")


if __name__ == "__main__":
    unittest.main()
