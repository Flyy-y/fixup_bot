"""Pure URL transformation logic for the fixupx bot.

The only public entry points are :func:`transform_text`, :func:`count_matches`
and :func:`has_x_link`. They contain no Discord or I/O dependencies so they can
be exhaustively unit-tested in isolation.

Rules applied to ``x.com`` / ``www.x.com`` links:

1. Rewrite the host to ``fixupx.com`` / ``www.fixupx.com`` so Discord renders a
   working Twitter/X embed.
2. **Strip the query string and fragment.** On X, the query carries only
   tracking/source data (``?s=20``, ``?t=…``, ``?ref_src=twsrc%5Etfw``,
   ``?cxt=…`` …) and the embed never needs it, so we keep only the content
   (scheme + host + optional port + path) and hand X/Elon nothing extra.

Scheme, ``www.`` prefix, port and path are preserved. Any other host
(``max.com``, ``xx.com``, ``x.com.evil.com``, ``fixupx.com`` …) is untouched.
"""

from __future__ import annotations

import re

# Match an ``x.com`` host only when it is the *whole* host (preceded by a
# scheme with an optional ``www.`` label and followed by a host boundary), then
# capture the parts we keep (port, path) and the parts we discard (query,
# fragment). The boundary lookahead deliberately rejects ``x.com.evil.com``
# (followed by ``.``), ``xx.com`` and ``fixupx.com``.
_X_COM_RE = re.compile(
    r"(?P<prefix>https?://(?:www\.)?)x\.com"
    r"(?=$|[/?#:]|\s)"           # host boundary
    r"(?P<port>:\d+)?"          # optional port            -> kept
    r"(?P<path>/[^\s?#<>]*)?"   # optional path (content)  -> kept
    r"(?:\?[^\s#<>]*)?"         # query string (tracking)  -> stripped
    r"(?:#[^\s<>]*)?",          # fragment                 -> stripped
    re.IGNORECASE,
)

_REPLACEMENT_HOST = "fixupx.com"


def _rewrite(match: re.Match) -> str:
    return (
        match.group("prefix")
        + _REPLACEMENT_HOST
        + (match.group("port") or "")
        + (match.group("path") or "")
    )


def transform_text(text: str) -> str:
    """Return *text* with every ``x.com`` link rewritten to a clean ``fixupx.com``.

    The host is rewritten and the tracking query string / fragment removed; the
    scheme, ``www.`` prefix, port and path are preserved. If no qualifying link
    is present the input is returned unchanged.
    """
    if not text:
        return text
    return _X_COM_RE.sub(_rewrite, text)


def count_matches(text: str) -> int:
    """Return how many ``x.com`` links would be rewritten in *text*."""
    if not text:
        return 0
    return sum(1 for _ in _X_COM_RE.finditer(text))


def has_x_link(text: str) -> bool:
    """Return ``True`` if *text* contains at least one rewritable ``x.com`` link."""
    return count_matches(text) > 0
