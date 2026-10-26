"""Bounded, deterministic UCIE-only public PR-list rotation.

No network or disk access. Existing approved source and PR-file request limits
remain unchanged; an unreviewable PR is eligible for later reinspection.
"""
from __future__ import annotations


def rotating_public_pr_rows(rows, *, hour_index: int, limit: int):
    """Rotate an already validated <=20 entry public PR page by UTC hour."""
    if (type(rows) is not list or len(rows) > 20
            or type(hour_index) is not int or hour_index < 0
            or type(limit) is not int or not 1 <= limit <= 5):
        raise ValueError("invalid bounded public PR rotation")
    if len(rows) <= limit:
        return list(rows)
    offset = (hour_index * limit) % len(rows)
    return rows[offset:] + rows[:offset]
