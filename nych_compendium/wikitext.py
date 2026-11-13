"""Strip MediaWiki markup before counting. Owner instruction: get rid of markup.

Interpreted plumbing: mwparserfromhell 0.6.6 ``strip_code(normalize=True,
collapse=True)`` does the stripping. Templates, comments, references, math and
other invisible tags are dropped; link text, bold/italic text, headings and
table cell text are kept, and HTML entities are decoded. Before stripping,
file, image, media and category links are removed, because their options and
captions would otherwise leak into the text, and so are bare URLs. Links that
start with a colon, such as ``[[:Category:X]]``, are visible links and keep
their text. A redirect page is excluded from counting.
"""
from __future__ import annotations

import mwparserfromhell
from mwparserfromhell.nodes import ExternalLink, Wikilink

EXTRACTION_VERSION = "nych-compendium-mwparserfromhell-0.6.6-strip-v1"
DROPPED_LINK_NAMESPACES = frozenset({"file", "image", "media", "category"})


def _dropped(node) -> bool:
    if isinstance(node, ExternalLink):
        return not node.brackets
    if isinstance(node, Wikilink):
        title = str(node.title).strip()
        if title.startswith(":") or ":" not in title:
            return False
        return title.split(":", 1)[0].strip().lower() in DROPPED_LINK_NAMESPACES
    return False


def plain_text(wikitext: str) -> str:
    """Return the readable text of one page's wikitext."""
    code = mwparserfromhell.parse(wikitext)
    for node in code.filter(recursive=True, matches=None, forcetype=(Wikilink, ExternalLink)):
        if _dropped(node):
            try:
                code.remove(node)
            except ValueError:
                pass  # already removed with an enclosing dropped link
    return code.strip_code(normalize=True, collapse=True)
