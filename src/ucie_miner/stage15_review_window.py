"""UCIE Stage15 bounded UTC-hour pending revision selection.

Selection only: no additional API calls, persistence, signing or promotion.
Upstream evidence remains unverified until separate review.
"""
from __future__ import annotations


def select_pending_public_revisions(leads, prior, *, limit: int, hour_index: int):
    """Select at most two pending public revisions without a persistent ignore list."""
    if (type(limit) is not int or not 1 <= limit <= 2
            or type(hour_index) is not int or hour_index < 0):
        raise ValueError("invalid bounded public review selection")
    pending=[item for item in leads
             if (item[0],item[1],item[3]) not in prior]
    count=len(pending)
    if not count:
        return []
    start=(hour_index * limit) % count
    return [pending[(start+index) % count]
            for index in range(min(limit,count))]
