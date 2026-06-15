"""Pure URL transformation logic for the fixupx bot.

The only public entry points are :func:`transform_text` and
:func:`count_matches`. They contain no Discord or I/O dependencies so they can
be exhaustively unit-tested in isolation.

Rule: rewrite the host of ``x.com`` / ``www.x.com`` links to ``fixupx.com`` /
``www.fixupx.com`` while preserving scheme, ``www`` prefix, port, path, query
string and fragment. Any other host (``max.com``, ``xx.com``, ``x.com.evil``,
``fixupx.com`` …) is left untouched.
"""

from __future__ import annotations

import re

# Match an ``x.com`` host only when it is the *whole* host:
#   - preceded by ``http://`` or ``https://`` with an optional ``www.`` label
#   - followed by a host boundary: ``/`` ``?`` ``#`` ``:`` (port), whitespace,
#     or end-of-string.
# This deliberately does NOT match ``x.com.evil.com`` (followed by ``.``),
# ``xx.com`` (no ``://`` boundary before ``x``), ``max.com`` or ``fixupx.com``.
_X_COM_RE = re.compile(
    r"(?P<prefix>https?://(?:www\.)?)x\.com(?=$|[/?#:]|\s)",
    re.IGNORECASE,
)

_REPLACEMENT_HOST = "fixupx.com"


def transform_text(text: str) -> str:
    """Return *text* with every ``x.com`` link rewritten to ``fixupx.com``.

    Only the host is changed; the original scheme and ``www.`` prefix are
    preserved. If no qualifying link is present the input is returned
    unchanged.
    """
    if not text:
        return text
    return _X_COM_RE.sub(lambda m: m.group("prefix") + _REPLACEMENT_HOST, text)


def count_matches(text: str) -> int:
    """Return how many ``x.com`` links would be rewritten in *text*."""
    if not text:
        return 0
    return len(_X_COM_RE.findall(text))


def has_x_link(text: str) -> bool:
    """Return ``True`` if *text* contains at least one rewritable ``x.com`` link."""
    return count_matches(text) > 0
