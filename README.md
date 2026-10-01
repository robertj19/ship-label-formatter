# shiplabel

A formatter for shipping labels typed by hand, pasted out of an email,
or copied out of a spreadsheet cell. The input is rarely consistent -
mixed case, a full state name instead of an abbreviation, a missing
zip, a country line nobody bothered to add - and this turns it into a
clean, uppercase, USPS-style block.

Input:

```
jane doe
500 5th ave apt 12
new york ny 10110
```

Output:

```
JANE DOE
500 5TH AVE APT 12
NEW YORK, NY 10110
US
```

## Usage

As a library:

```python
from shiplabel import format_label

text = "jane doe\n500 5th ave apt 12\nnew york ny 10110"
print(format_label(text))
```

From the command line:

```
$ python -m shiplabel.cli < label.txt
JANE DOE
500 5TH AVE APT 12
NEW YORK, NY 10110
US
```

## Batch mode

A file with several labels in it, each one separated from the next by
a blank line, can be normalized in one pass with `--batch`:

```
$ python -m shiplabel.cli --batch < labels.txt
JANE DOE
500 5TH AVE APT 12
NEW YORK, NY 10110
US

JOHN SMITH
1 INFINITE LOOP
CUPERTINO, CA 95014
US
```

The same is available as a library call, `format_batch()`, or
`parse_batch()` if you want the `Label` objects instead of formatted
text. Errors report the line number within the whole file. Note that
in batch mode a blank line always separates labels - it can't also be
used to flag a label that's missing a field the way it can when
formatting a single label, since batch mode has no other way to tell
where one label ends and the next begins.

## Errors point at the exact spot

"Invalid label" is useless when you're fixing a batch of a few
hundred of these by hand. Every error carries a line and column and
shows the offending text:

```
$ printf 'jane doe\n500 5th ave apt 12\nnew york ny 1011' | python -m shiplabel.cli
"1011" is not a valid US zip code (expected 12345 or 12345-6789)
  line 3, column 13
    new york ny 1011
                ^^^^
```

## Input format

Three to five lines, one field per line:

1. Name
2. Street address
3. Second street line, e.g. "Apt 4B" or "Suite 200" (optional)
4. `City, ST ZIP` (the comma is optional)
5. Country code (optional, defaults to `US`)

Blank lines around the block are ignored; a blank line where a field
should be is treated as a missing field, not a separator.

A 4-line label is ambiguous - it could have a second street line and
no country, or a country and no second street line - so a guess is
made based on the last line: a country is short with no digits or
commas, a second street line almost always has a number in it (see
`shiplabel/label.py` for the exact rule). Write the country
explicitly if your second street line happens to have no digits in
it, e.g. "Rear Unit".

## Canadian addresses

When the country line is `CA`, the region must be a province or
territory (`ON`, or a full name like "British Columbia") and the last
part of the line must be a postal code. The space in the middle is
optional on input and always added on output:

```
$ printf 'jane doe\n80 queen st\ntoronto on m5v2t6\nca' | python -m shiplabel.cli
JANE DOE
80 QUEEN ST
TORONTO, ON M5V 2T6
CA
```

Without a country line the label is read as a US one, so `ON` there is
an error. Other country codes are accepted but are still checked
against US states and zip codes.

## Status

Early skeleton. State names can be an abbreviation ("NY") or a full
name, single-word ("Texas") or multi-word ("New York", "North
Carolina"). See `shiplabel/label.py` for the current parsing rules.
