"""Canadian addresses: provinces and postal codes when the country line
says CA.
"""

from __future__ import annotations

import unittest

from shiplabel import LabelError, format_label, parse_batch


def underline(source: str, exc: LabelError) -> str:
    line = source.splitlines()[exc.line - 1]
    return line[exc.column - 1 : exc.column - 1 + exc.length]


class CanadianLabelTests(unittest.TestCase):
    def test_basic_label_with_comma(self):
        text = "Jane Doe\n80 Queen St\nToronto, ON M5V 2T6\nCA"
        self.assertEqual(
            format_label(text),
            "JANE DOE\n80 QUEEN ST\nTORONTO, ON M5V 2T6\nCA",
        )

    def test_postal_code_without_space_is_normalized(self):
        text = "Jane Doe\n80 Queen St\ntoronto on m5v2t6\nca"
        self.assertEqual(
            format_label(text),
            "JANE DOE\n80 QUEEN ST\nTORONTO, ON M5V 2T6\nCA",
        )

    def test_full_province_name(self):
        text = "Jane Doe\n80 Queen St\nVancouver, British Columbia V6B 1A1\nCA"
        self.assertIn("VANCOUVER, BC V6B 1A1", format_label(text))

    def test_three_word_province_without_comma(self):
        text = "Jane Doe\n1 Water St\nSt Johns Newfoundland and Labrador A1C 5X4\nCA"
        self.assertIn("ST JOHNS, NL A1C 5X4", format_label(text))

    def test_two_word_province_without_comma(self):
        text = "Jane Doe\n1 Main St\nHalifax Nova Scotia B3H 1A1\nCA"
        self.assertIn("HALIFAX, NS B3H 1A1", format_label(text))

    def test_second_street_line_and_country(self):
        text = "Jane Doe\n80 Queen St\nUnit 4\nOttawa, ON K1A 0B1\nCA"
        self.assertEqual(
            format_label(text),
            "JANE DOE\n80 QUEEN ST\nUNIT 4\nOTTAWA, ON K1A 0B1\nCA",
        )

    def test_batch_mixes_countries(self):
        text = (
            "Jane Doe\n500 5th Ave\nNew York, NY 10110\n"
            "\n"
            "John Smith\n80 Queen St\nToronto, ON M5V 2T6\nCA"
        )
        labels = parse_batch(text)
        self.assertEqual([label.country for label in labels], ["US", "CA"])
        self.assertEqual(labels[1].zip, "M5V 2T6")


class CanadianErrorTests(unittest.TestCase):
    def test_us_zip_rejected_for_canada(self):
        text = "Jane Doe\n80 Queen St\nToronto, ON 10110\nCA"
        with self.assertRaises(LabelError) as ctx:
            format_label(text)
        self.assertEqual(ctx.exception.line, 3)
        self.assertEqual(underline(text, ctx.exception), "10110")
        self.assertIn("postal code", ctx.exception.message)

    def test_postal_code_error_covers_both_halves(self):
        # D is never used in a Canadian postal code.
        text = "Jane Doe\n80 Queen St\nToronto, ON M5D 2T6\nCA"
        with self.assertRaises(LabelError) as ctx:
            format_label(text)
        self.assertEqual(underline(text, ctx.exception), "M5D 2T6")

    def test_us_state_rejected_for_canada(self):
        text = "Jane Doe\n80 Queen St\nToronto, NY M5V 2T6\nCA"
        with self.assertRaises(LabelError) as ctx:
            format_label(text)
        self.assertEqual(underline(text, ctx.exception), "NY")
        self.assertIn("province", ctx.exception.message)

    def test_province_rejected_without_canada(self):
        text = "Jane Doe\n80 Queen St\nToronto, ON 10110"
        with self.assertRaises(LabelError) as ctx:
            format_label(text)
        self.assertEqual(underline(text, ctx.exception), "ON")

    def test_canadian_postal_code_rejected_for_us(self):
        text = "Jane Doe\n80 Queen St\nBuffalo, NY M5V 2T6"
        with self.assertRaises(LabelError) as ctx:
            format_label(text)
        self.assertEqual(ctx.exception.line, 3)


if __name__ == "__main__":
    unittest.main()
