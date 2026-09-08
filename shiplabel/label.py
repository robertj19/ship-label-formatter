"""Parsing and normalization of a single shipping label.

A label is plain text, one field per line:

    Jane Doe
    500 5th Ave Apt 12
    New York, NY 10110
    US

The country line is optional and defaults to US. Blank lines around
the block are ignored; blank lines inside it are not, since a missing
field is exactly the kind of mistake this module exists to catch.

Limitation: the city/state/zip line is split by looking for the last
one or two whitespace-separated tokens as the state and zip, so only
single-word state names ("Texas") and two-letter abbreviations are
recognized. Multi-word names ("New York", "North Carolina") aren't
yet, because they can't be told apart from a two-word city name using
this rule alone.
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

# Only the single-word full names; see the module docstring.
_STATE_NAMES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT",
    "delaware": "DE", "florida": "FL", "georgia": "GA", "hawaii": "HI",
    "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME",
    "maryland": "MD", "massachusetts": "MA", "michigan": "MI",
    "minnesota": "MN", "mississippi": "MS", "missouri": "MO",
    "montana": "MT", "nebraska": "NE", "nevada": "NV", "ohio": "OH",
    "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "wisconsin": "WI",
    "wyoming": "WY",
}

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

    def format(self) -> str:
        return "\n".join(
            [
                self.name.upper(),
                self.street.upper(),
                f"{self.city.upper()}, {self.state} {self.zip}",
                self.country,
            ]
        )


def format_label(text: str) -> str:
    """Parse and normalize a single label, returning the clean text form."""
    return _normalize(text).format()


def _normalize(text: str) -> Label:
    lines = text.splitlines()

    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    end = len(lines)
    while end > start and not lines[end - 1].strip():
        end -= 1
    body = lines[start:end]

    if len(body) < 3:
        raise LabelError(
            "a label needs at least a name, a street, and a city/state/zip line",
            text,
            start + len(body) or 1,
            1,
        )
    if len(body) > 4:
        extra_line_no = start + 5
        extra_text = lines[extra_line_no - 1]
        raise LabelError(
            "too many lines for a label (expected name, street, city/state/zip, "
            "and an optional country)",
            text,
            extra_line_no,
            1,
            len(extra_text) or 1,
        )

    name_line_no = start + 1
    street_line_no = start + 2
    csz_line_no = start + 3
    country_line_no = start + 4 if len(body) == 4 else None

    name = _require_nonblank(body[0], text, name_line_no, "name")
    street = _require_nonblank(body[1], text, street_line_no, "street address")
    city, state, zip_code = _parse_city_state_zip(body[2], text, csz_line_no)
    country = (
        _parse_country(body[3], text, country_line_no)
        if country_line_no
        else "US"
    )

    return Label(
        name=_collapse_whitespace(name),
        street=_collapse_whitespace(street),
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
        remainder_offset = comma_at + 1
    else:
        # No comma: assume the last two whitespace-separated tokens are
        # the state and zip, and everything before them is the city.
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
        state_token = tokens[-2]
        city_part = line[: state_token.start()]
        remainder = line[state_token.start() :]
        remainder_offset = state_token.start()

    if not city_part.strip():
        raise LabelError("city is missing", source, line_no, 1)
    city = _collapse_whitespace(city_part).title()

    remainder_tokens = list(re.finditer(r"\S+", remainder))
    if len(remainder_tokens) < 2:
        raise LabelError(
            "expected a state and a zip code after the city",
            source,
            line_no,
            remainder_offset + 1,
            len(remainder.strip()) or 1,
        )
    if len(remainder_tokens) > 2:
        extra = remainder_tokens[2]
        raise LabelError(
            "unexpected extra text after the zip code",
            source,
            line_no,
            remainder_offset + extra.start() + 1,
            len(extra.group()),
        )

    state_token, zip_token = remainder_tokens
    state = _normalize_state(
        state_token.group(),
        source,
        line_no,
        remainder_offset + state_token.start() + 1,
    )
    zip_code = _normalize_zip(
        zip_token.group(),
        source,
        line_no,
        remainder_offset + zip_token.start() + 1,
    )

    return city, state, zip_code


def _normalize_state(token: str, source: str, line_no: int, column: int) -> str:
    cleaned = token.strip(",")
    lowered = cleaned.lower()
    if lowered in _STATE_NAMES:
        return _STATE_NAMES[lowered]
    upper = cleaned.upper()
    if upper in _STATE_ABBREVIATIONS:
        return upper
    raise LabelError(
        f'"{token}" is not a recognized state or territory',
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
