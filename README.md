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

Four lines, one field per line:

1. Name
2. Street address
3. `City, ST ZIP` (the comma is optional)
4. Country code (optional, defaults to `US`)

Blank lines around the block are ignored; a blank line where a field
should be is treated as a missing field, not a separator.

## Status

Early skeleton. State names can be an abbreviation ("NY") or a full
name, single-word ("Texas") or multi-word ("New York", "North
Carolina"). Street addresses are still limited to a single line. See
`shiplabel/label.py` for the current parsing rules.
