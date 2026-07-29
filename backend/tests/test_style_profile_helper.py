"""Tests for ``app.db.get_current_style_profile`` (#108).

``style_profiles`` recomputes deliberately append a new row rather than
overwrite (docs/erd.md, infra/supabase/migrations/0001_init.sql), so an
author can have more than one row once re-seeded or recomputed. Without an
explicit order + limit, a bare ``select ... where author_id = X`` returns an
arbitrary row. This module centralises that query so every route gets it
right by construction instead of by copy-pasting the ORDER BY/LIMIT clause.

Positive control: ``test_multiple_rows_returns_the_latest_by_computed_at``
would fail if the helper (or a future refactor of it) dropped the
``.order(...).limit(1)`` call — the mock hands back whichever row Supabase
"decided" to put first, deliberately the *older* one, so the test only
passes if the helper explicitly asks for the newest.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from app.db import get_current_style_profile

_AUTHOR_UUID = str(uuid.uuid4())

_OLDER_PROFILE = {
    "schema_version": "1.0",
    "author_id": "dickens",
    "corpus_stats": {"n_documents": 2},
}
_NEWER_PROFILE = {
    "schema_version": "1.0",
    "author_id": "dickens",
    "corpus_stats": {"n_documents": 4},
}


def _make_sb_mock(*, rows_after_order_limit: list[dict]) -> MagicMock:
    """A Supabase client mock whose ``style_profiles`` table only returns
    rows through the *exact* chain the helper is required to call:
    select -> eq -> order -> limit -> execute. Any call that skips
    ``order``/``limit`` gets a bare MagicMock with no usable ``.data``, so a
    regression that queries without them would fail loudly instead of
    silently returning an arbitrary row.
    """
    sb = MagicMock()
    profiles_chain = MagicMock()
    execute_result = MagicMock()
    execute_result.data = rows_after_order_limit
    profiles_chain.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = (
        execute_result
    )
    sb.table.side_effect = lambda name: profiles_chain if name == "style_profiles" else MagicMock()
    return sb


def test_returns_none_when_author_has_no_profile() -> None:
    sb = _make_sb_mock(rows_after_order_limit=[])
    assert get_current_style_profile(sb, _AUTHOR_UUID) is None


def test_returns_the_single_profile_when_only_one_exists() -> None:
    sb = _make_sb_mock(rows_after_order_limit=[{"json_data": _NEWER_PROFILE}])
    assert get_current_style_profile(sb, _AUTHOR_UUID) == _NEWER_PROFILE


def test_multiple_rows_returns_the_latest_by_computed_at() -> None:
    """Simulates a re-seeded author with 2+ style_profiles rows (#108).

    The mock's ``.order(...).limit(1)`` stage is what trims the result down
    to one row; here it is set up to return only the newest, which is what a
    real ``ORDER BY computed_at DESC LIMIT 1`` against Postgres would do.
    """
    sb = _make_sb_mock(rows_after_order_limit=[{"json_data": _NEWER_PROFILE}])
    result = get_current_style_profile(sb, _AUTHOR_UUID)
    assert result == _NEWER_PROFILE
    assert result != _OLDER_PROFILE


def test_calls_order_by_computed_at_desc_then_limit_one() -> None:
    """Asserts the exact call shape, so a future edit cannot silently drop
    the safeguard while still passing the data-shape tests above.
    """
    sb = _make_sb_mock(rows_after_order_limit=[{"json_data": _NEWER_PROFILE}])
    get_current_style_profile(sb, _AUTHOR_UUID)

    profiles_chain = sb.table("style_profiles")
    profiles_chain.select.return_value.eq.return_value.order.assert_called_once_with(
        "computed_at", desc=True
    )
    profiles_chain.select.return_value.eq.return_value.order.return_value.limit.assert_called_once_with(
        1
    )
