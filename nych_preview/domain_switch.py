"""Interpreted temporary domain-switch tags. Not owner-confirmed.

A temporary switch opens as dom>x=food and closes as x=12. The global
form stays the literal dom><global. This only checks those strings.
Placement, automatic reversion, a domain on the global tag, and nesting
are open, so this module refuses them. Not wired into any Builder.
"""
from __future__ import annotations

GLOBAL_TAG = "dom><global"


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
