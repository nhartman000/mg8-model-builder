"""Provisional domain-switch parser.

Owner-stated, not approved: a temporary switch opens as ``dom>?<domain>``,
where ``?`` is any variable name. Counting starts when that variable is turned
on. The close ``?=N`` is interlinear where the switch ends, and N is the token
count from open to close. Duration is not known at the opening tag. This is
stop-start. ``dom><global`` stays the global form.

The earlier ``dom>N`` form is still accepted. Whether the variable form
supersedes it is an open owner question, not decided here.

Still rejected or unresolved, and not guessed: (b) automatic reversion at the
close, (c) a domain name on the global tag, (d) nesting or overlap of
different variables, and parentheses.

Implementation choice, not an owner value: N counts tokens strictly between
the opening tag and the closing tag. Neither tag is included. The owner said
counting starts after the variable is turned on and that the number is
recorded when the switch ends, and did not say whether either tag token is
inside N. A variable or domain name is one or more ASCII letters, because the
examples are names such as x and food and no other character class was given.
Whitespace-delimited scanning is used because the B2 tokenizer would split on
``>``.
"""
from __future__ import annotations

import re

GLOBAL_TAG = "dom><global"
COUNT_BOUNDARY = "exclusive-of-open-and-close"
_TEMPORARY = re.compile(r"^dom>([1-9][0-9]*)$")
_OPEN = re.compile(r"^dom>([A-Za-z]+)=([A-Za-z]+)$")
_CLOSE = re.compile(r"^([A-Za-z]+)=(0|[1-9][0-9]*)$")


class DomainSwitchError(ValueError):
    """Raised when a tag is outside a stated form or still open."""


def _name(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.isascii() or not value.isalpha():
        raise DomainSwitchError(f"{label} must be letters")
    return value


def temporary_open(variable: str, domain: str) -> str:
    """Format the stated opening tag. The variable names the switch."""
    return f"dom>{_name(variable, 'variable')}={_name(domain, 'domain')}"


def temporary_close(variable: str, token_count: int) -> str:
    """Format the stated closing tag. N is the recorded token count."""
    _name(variable, "variable")
    if type(token_count) is not int or token_count < 0:
        raise DomainSwitchError("token count must be a non-negative integer")
    return f"{variable}={token_count}"


def global_tag() -> str:
    """Return the unchanged global form. It does not take a domain name."""
    return GLOBAL_TAG


def check_temporary_pair(open_tag: str, close_tag: str) -> None:
    """Accept one stated open/close pair. Nesting and a second pair are refused.

    This check has no token sequence, so it does not validate N. Use
    ``annotate_tokens`` for the count.
    """
    if not isinstance(open_tag, str) or not open_tag.startswith("dom>") or open_tag.count("=") != 1:
        raise DomainSwitchError("opening tag must be dom>variable=domain")
    if open_tag.startswith("dom><"):
        raise DomainSwitchError("dom><global does not name a domain here")
    variable, domain = open_tag.removeprefix("dom>").split("=", 1)
    _name(variable, "variable")
    _name(domain, "domain")
    if not isinstance(close_tag, str) or close_tag.count("=") != 1:
        raise DomainSwitchError("closing tag must be variable=count")
    close_variable, count = close_tag.split("=", 1)
    if close_variable != variable or _canonical_count(count) is None:
        raise DomainSwitchError("closing tag must reuse the opening variable and a recorded count")


def temporary_span(token_count: int) -> str:
    """Format the earlier temporary tag ``dom>N``. Its relation to the variable form is open."""
    if type(token_count) is not int or token_count < 1:
        raise DomainSwitchError("token count must be a positive integer")
    return f"dom>{token_count}"


def _canonical_count(text: str) -> int | None:
    if text == "0" or (text.isdigit() and not text.startswith("0")):
        return int(text)
    return None


def parse_tag(text: str) -> dict:
    """Parse one exact tag. Parentheses and unnamed extensions are rejected."""
    if not isinstance(text, str) or text != text.strip() or not text:
        raise DomainSwitchError("tag must be an exact non-empty string")
    if "(" in text or ")" in text:
        raise DomainSwitchError("unresolved: parentheses")
    if text == GLOBAL_TAG:
        return {
            "count_direction": None,
            "domain": None,
            "form": "global",
            "interpreted": False,
            "placement": "interlinear-where-it-occurs",
            "status": "owner-stated",
            "text": text,
            "unresolved": ["c"],
        }
    if text.startswith("dom><"):
        if text.startswith(GLOBAL_TAG) and text != GLOBAL_TAG:
            raise DomainSwitchError("unresolved: (c) dom><global does not name a domain")
        raise DomainSwitchError("not an owner-stated domain-switch tag")
    temporary = _TEMPORARY.fullmatch(text)
    if temporary:
        return {
            "count_direction": "forward-from-this-point",
            "domain": None,
            "form": "temporary",
            "interpreted": False,
            "placement": "interlinear-where-it-occurs",
            "relationship_to_variable_form": "unresolved",
            "status": "owner-stated",
            "text": text,
            "token_count": int(temporary.group(1)),
            "unresolved": ["b", "dom-n-relationship"],
        }
    opened = _OPEN.fullmatch(text)
    if opened:
        return {
            "count_direction": "after-open-until-close",
            "domain": opened.group(2),
            "duration_known_at_open": False,
            "form": "temporary-open",
            "interpreted": False,
            "placement": "interlinear-where-it-occurs",
            "semantics": "stop-start",
            "status": "owner-stated",
            "text": text,
            "unresolved": ["b"],
            "variable": opened.group(1),
        }
    closed = _CLOSE.fullmatch(text)
    if closed:
        return {
            "count_direction": "from-open-to-close",
            "domain": None,
            "duration_known_at_open": False,
            "form": "temporary-close",
            "interpreted": False,
            "placement": "interlinear-where-the-switch-ends",
            "semantics": "stop-start",
            "status": "owner-stated",
            "text": text,
            "token_count": int(closed.group(2)),
            "unresolved": ["b"],
            "variable": closed.group(1),
        }
    raise DomainSwitchError("not an owner-stated domain-switch tag")


def domain_after_close() -> dict:
    """Question (b) is open. Do not invent the domain that resumes."""
    return {"question": "b", "resumes_previous_domain": "unresolved", "status": "unresolved"}


def annotate_tokens(token_texts: list[str]) -> dict:
    """Recognize tags and check N against tokens strictly between open and close.

    The count boundary is ``COUNT_BOUNDARY`` and is an implementation choice.
    Nesting, overlap, reversion, and a domain on the global tag stay unresolved.
    """
    tags = []
    unresolved: set[str] = set()
    active_until = None
    open_index = None
    open_variable = None
    foreign_inside = False
    for index, token in enumerate(token_texts):
        if "(" in token or ")" in token:
            if "dom>" in token or _CLOSE.fullmatch(token.strip("()")):
                unresolved.add("parentheses")
                tags.append({"index": index, "status": "unresolved", "text": token, "unresolved": ["parentheses"]})
                continue
        try:
            parsed = parse_tag(token)
        except DomainSwitchError as err:
            if token.startswith("dom>"):
                unresolved.update(_question_ids(str(err)))
                tags.append({"index": index, "status": "rejected", "text": token, "unresolved": _question_ids(str(err))})
            continue
        parsed = dict(parsed)
        parsed["index"] = index
        unresolved.update(parsed["unresolved"])
        form = parsed["form"]
        if form == "temporary":
            if active_until is not None and index < active_until:
                unresolved.add("overlap")
                parsed["overlap"] = "unresolved"
            if open_variable is not None:
                foreign_inside = True
                unresolved.add("dom-n-relationship")
            active_until = index + parsed["token_count"]
        elif form == "temporary-open":
            if open_variable is not None:
                unresolved.add("d")
                parsed["overlap"] = "unresolved"
                foreign_inside = True
            else:
                open_variable = parsed["variable"]
                open_index = index
                foreign_inside = False
        elif form == "temporary-close":
            parsed["resumes_previous_domain"] = "unresolved"
            if open_variable != parsed["variable"] or open_index is None:
                parsed["count_match"] = False
                parsed["matched_open"] = False
                parsed["status"] = "rejected"
            elif foreign_inside:
                unresolved.add("d")
                parsed["count_match"] = "unresolved"
                parsed["matched_open"] = True
                parsed["overlap"] = "unresolved"
                open_variable = None
                open_index = None
                foreign_inside = False
            else:
                counted = index - open_index - 1
                parsed["count_boundary"] = COUNT_BOUNDARY
                parsed["count_boundary_status"] = "implementation-choice"
                parsed["counted_tokens"] = counted
                parsed["count_match"] = counted == parsed["token_count"]
                parsed["matched_open"] = True
                if not parsed["count_match"]:
                    parsed["status"] = "rejected"
                open_variable = None
                open_index = None
        tags.append(parsed)
    return {
        "authorizes_domain": False,
        "count_boundary": COUNT_BOUNDARY,
        "count_boundary_status": "implementation-choice",
        "provisional": True,
        "resumes_previous_domain": "unresolved",
        "tags": tags,
        "unresolved": sorted(unresolved),
    }


def scan_interlinear(text: str) -> dict:
    """Scan a whitespace-delimited interlinear string. Not a B2 tokenization."""
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    return annotate_tokens(text.split())


def _question_ids(message: str) -> list[str]:
    found = []
    if "parentheses" in message:
        found.append("parentheses")
    for question in ("a", "b", "c", "d"):
        if f"({question})" in message:
            found.append(question)
    return found or ["rejected"]
