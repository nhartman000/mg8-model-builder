"""One-sided 95% Clopper-Pearson lower bound.

The bound is the approved gate. Automatic correction is allowed only when it
is at least 0.99. Category names are the approved report groups. No smoothing
method is chosen here.
"""
from __future__ import annotations

import math

ALPHA = 0.05
MINIMUM = 0.99
CATEGORIES = ("proper_names", "scientific_terms", "coherent_rare_words", "ambiguous_candidates")
LAYOUTS = ("us-qwerty", "uk-qwerty", "azerty", "qwertz")


def _betacf(a: float, b: float, x: float) -> float:
    max_iter = 200
    eps = 3e-14
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            return h
    raise RuntimeError("incomplete beta continued fraction did not converge")


def _regularized_beta(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(a * math.log(x) + b * math.log(1.0 - x) - log_beta)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def _beta_ppf(probability: float, a: float, b: float) -> float:
    if probability <= 0.0:
        return 0.0
    if probability >= 1.0:
        return 1.0
    lo = 0.0
    hi = 1.0
    for _ in range(80):
        mid = (lo + hi) / 2.0
        if _regularized_beta(a, b, mid) < probability:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def lower_bound(correct: int, evaluated: int) -> float:
    """Return the one-sided 95% Clopper-Pearson lower bound on precision."""
    if not isinstance(correct, int) or isinstance(correct, bool):
        raise TypeError("correct must be an integer")
    if not isinstance(evaluated, int) or isinstance(evaluated, bool):
        raise TypeError("evaluated must be an integer")
    if evaluated < 1 or correct < 0 or correct > evaluated:
        raise ValueError("correct and evaluated must satisfy 0 <= correct <= evaluated and evaluated >= 1")
    if correct == 0:
        return 0.0
    if correct == evaluated:
        return ALPHA ** (1.0 / evaluated)
    return _beta_ppf(ALPHA, correct, evaluated - correct + 1)


def automatic_correction_allowed(correct: int, evaluated: int) -> bool:
    return lower_bound(correct, evaluated) >= MINIMUM


def category_report(cases: list[dict]) -> dict:
    """Report precision and false corrections for labeled held-out cases.

    Categories and layouts are not inferred. A group with no labeled cases is
    reported as absent.
    """
    groups = {name: [] for name in CATEGORIES}
    layouts = {name: [] for name in LAYOUTS}
    for case in cases:
        category = case.get("category")
        layout = case.get("layout")
        if category not in groups or layout not in layouts:
            raise ValueError("held-out case is missing an approved category or layout")
        groups[category].append(case)
        layouts[layout].append(case)

    def summarize(rows: list[dict]) -> dict:
        if not rows:
            return {"evidence": "absent"}
        evaluated = len(rows)
        false_corrections = sum(1 for row in rows if row.get("false_correction") is True)
        corrections = sum(1 for row in rows if row.get("corrected") is True)
        correct_corrections = sum(
            1 for row in rows if row.get("corrected") is True and row.get("false_correction") is False
        )
        precision = None if corrections == 0 else correct_corrections / corrections
        return {
            "evaluated": evaluated,
            "false_correction_rate": false_corrections / evaluated,
            "precision": precision,
        }

    return {
        "categories": {name: summarize(rows) for name, rows in groups.items()},
        "layouts": {name: summarize(rows) for name, rows in layouts.items()},
    }
