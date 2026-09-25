"""Parsing and normalization of a single shipping label.

A label is plain text, one field per line:

    Jane Doe
    500 5th Ave
    Apt 12
    New York, NY 10110
    US

The second street line and the country line are both optional and
independently omittable, which makes a 4-line label ambiguous: it
could be (name, street, street2, city/state/zip) or (name, street,
city/state/zip, country). We resolve that by looking at the last
line - a country is short and has no digits or commas in it, while a
second street line ("Apt 4B", "Suite 200") almost always has a
number in it. A country-less label with a purely-alphabetic second
street line (e.g. "Rear Unit") will be misread as having a country;
write the country explicitly to avoid that.

Blank lines around the block are ignored; blank lines inside it are
not, since a missing field is exactly the kind of mistake this module
exists to catch.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .errors import LabelError

_STATE_ABBREVIATIONS = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "PR", "VI", "GU",
}

_STATE_NAMES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT",
    "delaware": "DE", "florida": "FL", "georgia": "GA", "hawaii": "HI",
    "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME",
    "maryland": "MD", "massachusetts": "MA", "michigan": "MI",
    "minnesota": "MN", "mississippi": "MS", "missouri": "MO",
    "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND",
    "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY",
}

# The subset of _STATE_NAMES keys that are two words, used to decide how
# many trailing tokens to treat as the state when there's no comma to
# mark the city/state boundary.
_TWO_WORD_STATE_NAMES = {name for name in _STATE_NAMES if " " in name}

_COUNTRY_CODES = {"US", "CA", "MX", "GB", "AU", "DE", "FR", "JP"}

_ZIP_RE = re.compile(r"^\d{5}(-\d{4})?$")


@dataclass
class Label:
    name: str
    street: str
    city: str
    state: str
    zip: str
    country: str
    street2: str | None = None

    def format(self) -> str:
        lines = [self.name.upper(), self.street.upper()]
        if self.street2:
            lines.append(self.street2.upper())
        lines.append(f"{self.city.upper()}, {self.state} {self.zip}")
        lines.append(self.country)
        return "\n".join(lines)


def format_label(text: str) -> str:
    """Parse and normalize a single label, returning the clean text form."""
    return _normalize(text).format()


def parse_batch(text: str) -> list[Label]:
    """Parse a file containing many labels, one per block of non-blank
    lines, blocks separated by one or more blank lines.

    Because blocks are delimited by blank lines, a label can't use an
    internal blank line to signal a missing field the way a single
    label passed to format_label() can - in batch mode that blank line
    is a block boundary instead, so a label short a field just shows
    up as an undersized block with its own error.

    Raises on the first invalid block, with the error's line number
    relative to the whole file, not the block.
    """
    return [
        _normalize_body(body, text, first_line_no)
        for body, first_line_no in _iter_blocks(text)
    ]


def format_batch(text: str) -> str:
    """Parse and normalize a batch of labels, returning them as clean
    text blocks separated by a blank line, in the original order.
    """
    return "\n\n".join(label.format() for label in parse_batch(text))


def _iter_blocks(text: str):
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        block_start = i
        while i < len(lines) and lines[i].strip():
            i += 1
        yield lines[block_start:i], block_start + 1


def _normalize(text: str) -> Label:
    lines = text.splitlines()

    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    end = len(lines)
    while end > start and not lines[end - 1].strip():
        end -= 1
    body = lines[start:end]

    return _normalize_body(body, text, start + 1)


def _normalize_body(body: list[str], source: str, first_line_no: int) -> Label:
    if len(body) < 3:
        raise LabelError(
            "a label needs at least a name, a street, and a city/state/zip line",
            source,
            first_line_no + len(body) - 1 or 1,
            1,
        )
    if len(body) > 5:
        extra_line_no = first_line_no + 5
        extra_text = body[5]
        raise LabelError(
            "too many lines for a label (expected name, one or two street "
            "lines, city/state/zip, and an optional country)",
            source,
            extra_line_no,
            1,
            len(extra_text) or 1,
        )

    has_country = len(body) == 5 or (
        len(body) == 4 and _looks_like_country_line(body[-1])
    )
    csz_index = len(body) - 2 if has_country else len(body) - 1
    street_lines = body[1:csz_index]

    name_line_no = first_line_no
    csz_line_no = first_line_no + csz_index
    country_line_no = first_line_no + len(body) - 1 if has_country else None

    name = _require_nonblank(body[0], source, name_line_no, "name")
    street_parts = [
        _require_nonblank(line, source, first_line_no + 1 + i, "street address")
        for i, line in enumerate(street_lines)
    ]
    city, state, zip_code = _parse_city_state_zip(body[csz_index], source, csz_line_no)
    country = (
        _parse_country(body[-1], source, country_line_no) if has_country else "US"
    )

    return Label(
        name=_collapse_whitespace(name),
        street=_collapse_whitespace(street_parts[0]),
        street2=_collapse_whitespace(street_parts[1])
        if len(street_parts) > 1
        else None,
        city=city,
        state=state,
        zip=zip_code,
        country=country,
    )


def _require_nonblank(line: str, source: str, line_no: int, field_name: str) -> str:
    if not line.strip():
        raise LabelError(f"{field_name} line is blank", source, line_no, 1)
    return line


def _collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _parse_city_state_zip(line: str, source: str, line_no: int):
    comma_at = line.find(",")
    if comma_at != -1:
        city_part = line[:comma_at]
        remainder = line[comma_at + 1 :]
        offset = comma_at + 1

        if not city_part.strip():
            raise LabelError("city is missing", source, line_no, 1)
        city = _collapse_whitespace(city_part).title()

        remainder_tokens = list(re.finditer(r"\S+", remainder))
        if len(remainder_tokens) < 2:
            # Point at whatever's actually there (e.g. a lone state with
            # no zip), not at the whitespace right after the comma.
            if remainder_tokens:
                error_start = offset + remainder_tokens[0].start()
                error_length = remainder_tokens[0].end() - remainder_tokens[0].start()
            else:
                error_start = offset
                error_length = 1
            raise LabelError(
                "expected a state and a zip code after the city",
                source,
                line_no,
                error_start + 1,
                error_length,
            )
        # The comma already marks where the city ends, so everything
        # between it and the zip is the state, however many words that
        # takes ("NY", "New York", "North Carolina").
        zip_token = remainder_tokens[-1]
        state_tokens = remainder_tokens[:-1]
    else:
        # No comma: the last token is the zip. Check whether the two
        # tokens before it spell a known two-word state name; if not,
        # fall back to treating just the last one as the state. Either
        # way, everything before that is the city.
        tokens = list(re.finditer(r"\S+", line))
        if len(tokens) < 3:
            stripped = line.strip()
            leading_ws = len(line) - len(line.lstrip())
            raise LabelError(
                'expected "City, ST ZIP" (state and zip not found)',
                source,
                line_no,
                leading_ws + 1,
                len(stripped) or 1,
            )
        offset = 0
        zip_token = tokens[-1]
        state_word_count = 1
        if len(tokens) >= 4:
            two_words = " ".join(t.group() for t in tokens[-3:-1]).lower()
            if two_words in _TWO_WORD_STATE_NAMES:
                state_word_count = 2
        state_tokens = tokens[-1 - state_word_count : -1]
        city_tokens = tokens[: -1 - state_word_count]

        city_part = line[city_tokens[0].start() : city_tokens[-1].end()]
        if not city_part.strip():
            raise LabelError("city is missing", source, line_no, 1)
        city = _collapse_whitespace(city_part).title()

    source_text = remainder if comma_at != -1 else line
    state_start = state_tokens[0].start()
    state_end = state_tokens[-1].end()
    state_text = source_text[state_start:state_end]
    state = _normalize_state(state_text, source, line_no, offset + state_start + 1)
    zip_code = _normalize_zip(
        zip_token.group(),
        source,
        line_no,
        offset + zip_token.start() + 1,
    )

    return city, state, zip_code


def _normalize_state(token: str, source: str, line_no: int, column: int) -> str:
    cleaned = _collapse_whitespace(token.strip(","))
    lowered = cleaned.lower()
    if lowered in _STATE_NAMES:
        return _STATE_NAMES[lowered]
    upper = cleaned.upper()
    if upper in _STATE_ABBREVIATIONS:
        return upper
    raise LabelError(
        f'"{token.strip()}" is not a recognized state or territory',
        source,
        line_no,
        column,
        len(token),
    )


def _normalize_zip(token: str, source: str, line_no: int, column: int) -> str:
    cleaned = token.rstrip(",.")
    if not _ZIP_RE.match(cleaned):
        raise LabelError(
            f'"{token}" is not a valid US zip code (expected 12345 or 12345-6789)',
            source,
            line_no,
            column,
            len(token),
        )
    return cleaned


def _looks_like_country_line(line: str) -> bool:
    """Guess whether a trailing line is a country rather than a second
    street line. See the module docstring for why this is a guess and
    not an exact check.
    """
    stripped = line.strip()
    if not stripped or "," in stripped:
        return False
    return not any(ch.isdigit() for ch in stripped)


def _parse_country(line: str, source: str, line_no: int) -> str:
    stripped = line.strip()
    if not stripped:
        raise LabelError(
            "country line is blank; omit it entirely to default to US",
            source,
            line_no,
            1,
        )
    leading_ws = len(line) - len(line.lstrip())
    code = stripped.upper()
    if code not in _COUNTRY_CODES:
        raise LabelError(
            f'"{stripped}" is not a recognized country code',
            source,
            line_no,
            leading_ws + 1,
            len(stripped),
        )
    return code
