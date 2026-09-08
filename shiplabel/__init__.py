"""shiplabel: normalize messy, hand-typed shipping labels into a
consistent form, with error messages that point at the exact spot
that needs fixing.
"""

from .errors import LabelError
from .label import Label, format_label

__all__ = ["Label", "LabelError", "format_label"]
__version__ = "0.1.0"
