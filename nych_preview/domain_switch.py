"""Domain-switch tags.

Owner-stated forms are the global tag ``dom><global`` and the temporary tag
``dom>N`` (N tokens from that point, on the interlinear line where it occurs).
``dom>x=food`` and ``x=12`` are the interpreted reading and stay labeled
interpreted. They do not remove the owner-stated ``dom>N`` form.

Open questions fail closed: (a) closing-tag placement and count direction,
(b) automatic reversion, (c) a domain name on the global tag, (d) nesting or
overlap of different variables, and parentheses. This module does not guess
those answers.

Interpreted plumbing: a variable is one or more lowercase letters, as in the
owner's x and z examples, and a domain value is lowercase letters, as in the
owner's food example. Whitespace-delimited scanning is used because the B2
tokenizer would split on ``>``.
"""
from __future__ import annotations

import re

GLOBAL_TAG = "dom><global"
_TEMPORARY = re.compile(r"^dom>([1-9][0-9]*)$")
_OPEN = re.compile(r"^dom>([a-z]+)=([a-z]+)$")
_CLOSE = re.compile(r"^([a-z]+)=([1-9][0-9]*)$")


class DomainSwitchError(ValueError):
    """Raised when a tag is outside the interpreted form or still open."""


def _name(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.isalpha() or not value.islower():
        raise DomainSwitchError(f"{label} must be lowercase letters")
    return value


def temporary_open(variable: str, domain: str) -> str:
    """Format an opening tag. The variable names the switch, not a position."""
    return f"dom>{_name(variable, 'variable')}={_name(domain, 'domain')}"


def temporary_close(variable: str, token_count: int) -> str:
    """Format a closing tag. token_count is the interpreted duration."""
    _name(variable, "variable")
    if type(token_count) is not int or token_count < 1:
        raise DomainSwitchError("token count must be a positive integer")
    return f"{variable}={token_count}"


def global_tag() -> str:
    """Return the unchanged global form. It does not take a domain name."""
    return GLOBAL_TAG


def check_temporary_pair(open_tag: str, close_tag: str) -> None:
    """Accept one interpreted pair. Nesting and a second pair are refused."""
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
    if close_variable != variable or not count.isdigit() or int(count) < 1:
        raise DomainSwitchError("closing tag must reuse the opening variable and a positive count")


def temporary_span(token_count: int) -> str:
    """Format the owner-stated temporary tag ``dom>N``."""
    if type(token_count) is not int or token_count < 1:
        raise DomainSwitchError("token count must be a positive integer")
    return f"dom>{token_count}"


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
        raise DomainSwitchError("not an owner-stated or interpreted domain-switch tag")
    temporary = _TEMPORARY.fullmatch(text)
    if temporary:
        return {
            "count_direction": "forward-from-this-point",
            "domain": None,
            "form": "temporary",
            "interpreted": False,
            "placement": "interlinear-where-it-occurs",
            "status": "owner-stated",
            "text": text,
            "token_count": int(temporary.group(1)),
            "unresolved": ["b"],
        }
    opened = _OPEN.fullmatch(text)
    if opened:
        return {
            "count_direction": "unresolved",
            "domain": opened.group(2),
            "form": "temporary-open",
            "interpreted": True,
            "placement": "unresolved",
            "status": "interpreted",
            "text": text,
            "unresolved": ["a", "b", "d"],
            "variable": opened.group(1),
        }
    closed = _CLOSE.fullmatch(text)
    if closed:
        return {
            "count_direction": "unresolved",
            "domain": None,
            "form": "temporary-close",
            "interpreted": True,
            "placement": "unresolved",
            "status": "interpreted",
            "text": text,
            "token_count": int(closed.group(2)),
            "unresolved": ["a", "b"],
            "variable": closed.group(1),
        }
    raise DomainSwitchError("not an owner-stated or interpreted domain-switch tag")


def domain_after_close() -> dict:
    """Question (b) is open. Do not invent the domain that resumes."""
    return {"question": "b", "resumes_previous_domain": "unresolved", "status": "unresolved"}


def annotate_tokens(token_texts: list[str]) -> dict:
    """Recognize tags in whitespace-delimited interlinear tokens.

    Overlapping windows and two different variables are marked unresolved.
    Nothing in the result chooses a resumed domain.
    """
    tags = []
    unresolved: set[str] = set()
    active_until = None
    open_variable = None
    for index, token in enumerate(token_texts):
        if "(" in token or ")" in token:
            if "dom>" in token or _CLOSE.fullmatch(token.strip("()")):
                unresolved.add("parentheses")
                tags.append({"index": index, "status": "unresolved", "text": token, "unresolved": ["parentheses"]})
                continue
        try:
            parsed = parse_tag(token)
        except DomainSwitchError as err:
            if token.startswith("dom>") or token.startswith("dom><"):
                unresolved.update(_question_ids(str(err)))
                tags.append({"index": index, "status": "rejected", "text": token, "unresolved": _question_ids(str(err))})
            continue
        parsed = dict(parsed)
        parsed["index"] = index
        unresolved.update(parsed["unresolved"])
        if parsed["form"] == "temporary":
            if active_until is not None and index < active_until:
                unresolved.add("overlap")
                parsed["overlap"] = "unresolved"
            active_until = index + parsed["token_count"]
        elif parsed["form"] == "temporary-open":
            if open_variable is not None and open_variable != parsed["variable"]:
                unresolved.add("d")
                parsed["overlap"] = "unresolved"
            elif open_variable == parsed["variable"]:
                unresolved.add("d")
                parsed["overlap"] = "unresolved"
            open_variable = parsed["variable"]
        elif parsed["form"] == "temporary-close":
            if open_variable != parsed["variable"]:
                unresolved.add("a")
                parsed["matched_open"] = False
            else:
                parsed["matched_open"] = True
                open_variable = None
            parsed["resumes_previous_domain"] = "unresolved"
        tags.append(parsed)
    return {
        "authorizes_domain": False,
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
