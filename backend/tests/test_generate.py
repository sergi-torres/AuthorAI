"""Tests for POST /api/generate (generateText).

All external I/O is mocked — no live Watsonx, no live DB, no spaCy/ST load:
  * ``app.routes.generate.get_client``  — Supabase calls
  * ``app.routes.generate._ORCHESTRATE_FN`` — the ai_pipeline orchestrator
  * ``app.services.watsonx_client`` module  — the real module when it imports,
    otherwise a fake installed by a module-scoped fixture (never at collection
    time), so the route's internal
    ``from app.services.watsonx_client import WatsonxError`` resolves even
    without ibm_watsonx_ai installed in this venv

Contract: docs/api_contract.yaml §generateText
  200  happy path → {vanilla:{text,fit_score,latency_ms},
                     autoria:{...}, passport:{jws_token,json_payload}}
  404  unknown author
  404  author exists but no StyleProfile
  503  orchestrator raises WatsonxError
  422  missing prompt / prompt > 4000 chars (Pydantic validation)

Env vars required: SUPABASE_URL, SUPABASE_KEY (stubbed via monkeypatch /
autouse fixture below so no .env file is needed in CI).
"""

from __future__ import annotations

import dataclasses
import sys
import types
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Env-var stub — must run before app.main is imported so Settings is populated.
# Using autouse=True session scope means it fires once for the whole module.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True, scope="module")
def _stub_env(monkeypatch_module):
    """Inject the minimum env vars the app needs to start."""
    monkeypatch_module.setenv("SUPABASE_URL", "http://localhost:54321")
    monkeypatch_module.setenv("SUPABASE_KEY", "test-supabase-key")
    monkeypatch_module.setenv("WATSONX_API_KEY", "test-watsonx-key")
    # Avoid loading spaCy / sentence-transformers during TestClient lifespan.
    monkeypatch_module.setenv("AUTORIA_SKIP_MODEL_WARMUP", "1")


@pytest.fixture(scope="module")
def monkeypatch_module():
    """Module-scoped monkeypatch (pytest's built-in is function-scoped only)."""
    with pytest.MonkeyPatch.context() as mp:
        yield mp


# ---------------------------------------------------------------------------
# WatsonxError stub
#
# ``app.services.watsonx_client`` imports ``ibm_watsonx_ai`` at module level,
# which may be absent from a backend-only dev venv.  Nothing in the app import
# chain pulls that module in eagerly — ``app/routes/generate.py`` imports it
# lazily *inside* the request handler — so a stand-in is only needed while this
# module's own tests execute, never at collection time.
#
# Installing a fake into sys.modules at import time (i.e. during collection) is
# precisely what used to break the whole backend suite: pytest imports every
# test module before running any test, so the fake was still in place when
# tests/test_watsonx_client.py was imported, and its
# ``from app.services.watsonx_client import _RETRY_DELAYS_SECONDS`` failed with
# "(unknown location)" — the signature of a synthetic ModuleType.
#
# So: prefer the real module (which also gives the route the real WatsonxError
# class to catch), and fall back to a fake confined to a module-scoped fixture.
# ---------------------------------------------------------------------------

_WX_KEY = "app.services.watsonx_client"

try:  # real module — available whenever ibm_watsonx_ai is installed
    from app.services.watsonx_client import WatsonxError as _WatsonxError

    _WX_REAL_AVAILABLE = True
except ImportError:  # backend-only venv without ibm_watsonx_ai
    _WX_REAL_AVAILABLE = False

    class _WatsonxError(RuntimeError):  # type: ignore[no-redef]
        """Stand-in for app.services.watsonx_client.WatsonxError."""


@pytest.fixture(autouse=True, scope="module")
def _fake_watsonx_module():
    """Expose ``app.services.watsonx_client`` for the duration of this module.

    No-op when the real module imported cleanly.  Otherwise a minimal fake is
    installed for this module's tests only and removed on teardown, so it is
    never visible while pytest collects (imports) any other test module.
    """
    if _WX_REAL_AVAILABLE:
        yield
        return

    fake = types.ModuleType(_WX_KEY)
    fake.WatsonxError = _WatsonxError  # type: ignore[attr-defined]
    fake.generate = MagicMock()  # type: ignore[attr-defined]
    prior = sys.modules.get(_WX_KEY)
    sys.modules[_WX_KEY] = fake
    try:
        yield
    finally:
        if prior is None:
            sys.modules.pop(_WX_KEY, None)
        else:
            sys.modules[_WX_KEY] = prior


import app.routes.generate as _gen_route  # noqa: E402
from app.main import app  # noqa: E402

# ---------------------------------------------------------------------------
# Constants shared across tests
# ---------------------------------------------------------------------------

_FAKE_AUTHOR_UUID = str(uuid.uuid4())
_FAKE_DOC_UUID = str(uuid.uuid4())
_FAKE_CHUNK_UUID = str(uuid.uuid4())
_EXPECTED_MODEL_ID = "meta-llama/llama-3-3-70b-instruct"

_STUB_STYLE_PROFILE: dict[str, Any] = {
    "schema_version": "1.0",
    "author_id": "dickens",
    "semantic_centroid": [0.0] * 768,
    "syntactic": {"avg_sentence_length_tokens": 20.0, "subordination_ratio": 0.2},
    "lexical": {"mattr_500": 0.7},
    "stylistic": {"pos_distribution": {}},
    "distinctive_vocab": [{"term": "fog", "score": 0.9}],
}

# A PassportPayload with hashed fields (no raw text) — mirrors builder.py output.
_STUB_PASSPORT_PAYLOAD: dict[str, Any] = {
    "schema_version": "1.0",
    "passport_id": str(uuid.uuid4()),
    "generated_at": "2026-01-01T00:00:00Z",
    "author_voice": {
        "id": "dickens",
        "style_profile_hash": "sha256:" + "a" * 64,
        "style_profile_version": "1.0",
    },
    "generation": {
        "model_provider": "ibm/watsonx",
        "model_id": _EXPECTED_MODEL_ID,
        "user_prompt_hash": "sha256:" + "b" * 64,
        "output_hash": "sha256:" + "c" * 64,
        "output_length_tokens": 42,
    },
    "rag_sources": [],
    "contribution": {"human_pct": 0, "ai_pct": 100, "note": "v1: 100% AI-assisted."},
    "fit_score": 72,
    "verifier_url": "https://autoria.app/verify",
}

_STUB_ORCHESTRATE_RESULT: dict[str, Any] = {
    "vanilla": {"text": "A plain London street.", "fit_score": 35, "latency_ms": 1200},
    "autoria": {
        "text": "The fog crept in on little cat feet.",
        "fit_score": 72,
        "latency_ms": 1200,
    },
    "passport": {
        "jws_token": "eyJ.stub.token",
        "json_payload": _STUB_PASSPORT_PAYLOAD,
    },
}


# ---------------------------------------------------------------------------
# Supabase mock helpers
# ---------------------------------------------------------------------------


def _make_sb_mock(
    *,
    author_found: bool = True,
    profile_rows: list[dict] | None = None,
) -> MagicMock:
    """Build a Supabase client mock for the generate route.

    The route calls (in order):
      sb.table("authors").select("id").eq("slug", ...).maybe_single().execute()
      sb.table("style_profiles").select("json_data").eq(...).order(...).limit(1).execute()
      sb.table("passports").insert({...}).execute()
    """
    if profile_rows is None:
        profile_rows = [{"json_data": _STUB_STYLE_PROFILE}]

    sb = MagicMock()

    # ---- authors table ----
    authors_chain = MagicMock()
    author_execute = MagicMock()
    author_execute.data = {"id": _FAKE_AUTHOR_UUID} if author_found else None
    authors_chain.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
        author_execute
    )

    # ---- style_profiles table ----
    profiles_chain = MagicMock()
    profile_execute = MagicMock()
    profile_execute.data = profile_rows
    profiles_chain.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = (
        profile_execute
    )

    # ---- passports table ----
    passports_chain = MagicMock()
    passports_chain.insert.return_value.execute.return_value = MagicMock()

    def _table_router(name: str) -> MagicMock:
        if name == "authors":
            return authors_chain
        if name == "style_profiles":
            return profiles_chain
        if name == "passports":
            return passports_chain
        return MagicMock()

    sb.table.side_effect = _table_router
    return sb


# ---------------------------------------------------------------------------
# Orchestrator patch helper
# ---------------------------------------------------------------------------


def _make_orchestrate_mock(
    result: dict[str, Any] | None = None,
    raises: Exception | None = None,
) -> AsyncMock:
    """Return an AsyncMock that either returns *result* or raises *raises*."""
    mock = AsyncMock()
    if raises is not None:
        mock.side_effect = raises
    else:
        mock.return_value = result or _STUB_ORCHESTRATE_RESULT
    return mock


# ---------------------------------------------------------------------------
# Convenience: run one request with both route patches active
# ---------------------------------------------------------------------------


def _post(
    prompt: str = "Write a dark street scene in Victorian London.",
    author_id: str = "dickens",
    *,
    sb: MagicMock | None = None,
    orchestrate: AsyncMock | None = None,
) -> Any:
    """POST /api/generate with pre-wired mocks; return the Response object."""
    if sb is None:
        sb = _make_sb_mock()
    if orchestrate is None:
        orchestrate = _make_orchestrate_mock()

    # Patch Supabase client at the name imported by the route.
    # Patch the module-level orchestrator cache directly — this is the same
    # technique used in the smoke-test in the implementation review.
    with patch("app.routes.generate.get_client", return_value=sb):
        _gen_route._ORCHESTRATE_FN = orchestrate
        _gen_route._IMPORT_ERROR = None
        client = TestClient(app, raise_server_exceptions=False)
        return client.post(
            "/api/generate",
            json={"author_id": author_id, "prompt": prompt},
        )


# ===========================================================================
# 1. Happy-path shape
# ===========================================================================


def test_happy_path_returns_200():
    """A valid request with all mocks succeeds with HTTP 200."""
    resp = _post()
    assert resp.status_code == 200


def test_happy_path_top_level_keys():
    """Response body has exactly the three required top-level keys."""
    body = _post().json()
    assert set(body.keys()) == {"vanilla", "autoria", "passport"}


def test_happy_path_vanilla_shape():
    """vanilla branch has text (str), fit_score (int 0-100), latency_ms (int >= 0)."""
    vanilla = _post().json()["vanilla"]
    assert isinstance(vanilla["text"], str) and vanilla["text"]
    assert isinstance(vanilla["fit_score"], int)
    assert 0 <= vanilla["fit_score"] <= 100
    assert isinstance(vanilla["latency_ms"], int)
    assert vanilla["latency_ms"] >= 0


def test_happy_path_autoria_shape():
    """autoria branch has the same required shape as vanilla."""
    autoria = _post().json()["autoria"]
    assert isinstance(autoria["text"], str) and autoria["text"]
    assert isinstance(autoria["fit_score"], int)
    assert 0 <= autoria["fit_score"] <= 100
    assert isinstance(autoria["latency_ms"], int)
    assert autoria["latency_ms"] >= 0


def test_happy_path_passport_shape():
    """passport has jws_token (str) and json_payload (dict)."""
    passport = _post().json()["passport"]
    assert isinstance(passport["jws_token"], str) and passport["jws_token"]
    assert isinstance(passport["json_payload"], dict)


def test_happy_path_passport_payload_schema_version():
    """passport.json_payload.schema_version == '1.0'."""
    payload = _post().json()["passport"]["json_payload"]
    assert payload["schema_version"] == "1.0"


# ===========================================================================
# 2. 404 — unknown author slug
# ===========================================================================


def test_unknown_author_returns_404():
    resp = _post(author_id="nobody", sb=_make_sb_mock(author_found=False))
    assert resp.status_code == 404


def test_unknown_author_error_code():
    body = _post(author_id="nobody", sb=_make_sb_mock(author_found=False)).json()
    assert body["detail"]["error"] == "not_found"


def test_unknown_author_message_contains_slug():
    body = _post(author_id="nobody", sb=_make_sb_mock(author_found=False)).json()
    assert "nobody" in body["detail"]["message"]


# ===========================================================================
# 3. 404 — author exists but no StyleProfile
# ===========================================================================


def test_no_style_profile_returns_404():
    resp = _post(sb=_make_sb_mock(author_found=True, profile_rows=[]))
    assert resp.status_code == 404


def test_no_style_profile_error_code():
    body = _post(sb=_make_sb_mock(author_found=True, profile_rows=[])).json()
    assert body["detail"]["error"] == "not_found"


def test_no_style_profile_message_contains_author():
    body = _post(author_id="poe", sb=_make_sb_mock(author_found=True, profile_rows=[])).json()
    assert "poe" in body["detail"]["message"]


# ===========================================================================
# 4. 503 — WatsonxError
# ===========================================================================


def test_watsonx_error_returns_503():
    resp = _post(orchestrate=_make_orchestrate_mock(raises=_WatsonxError("timeout")))
    assert resp.status_code == 503


def test_watsonx_error_code():
    body = _post(orchestrate=_make_orchestrate_mock(raises=_WatsonxError("timeout"))).json()
    assert body["detail"]["error"] == "service_unavailable"


def test_watsonx_error_message_non_empty():
    body = _post(orchestrate=_make_orchestrate_mock(raises=_WatsonxError("timeout"))).json()
    assert body["detail"]["message"]


# ===========================================================================
# 5. 422 — Pydantic validation (prompt constraints)
# ===========================================================================


def test_422_missing_prompt():
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/generate", json={"author_id": "dickens"})
    assert resp.status_code == 422


def test_422_empty_prompt():
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/generate", json={"author_id": "dickens", "prompt": ""})
    assert resp.status_code == 422


def test_422_prompt_too_long():
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/generate", json={"author_id": "dickens", "prompt": "x" * 4001})
    assert resp.status_code == 422


def test_422_missing_author_id():
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/generate", json={"prompt": "Write something."})
    assert resp.status_code == 422


def test_422_empty_body():
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/generate", json={})
    assert resp.status_code == 422


def test_prompt_at_max_length_is_accepted():
    """A prompt of exactly 4000 chars must pass validation (boundary check)."""
    resp = _post(prompt="x" * 4000)
    # Orchestrator is mocked → we only care that the route accepted the body.
    assert resp.status_code == 200


# ===========================================================================
# 6. Same model_id for both branches; vanilla gets system_prompt=None
# ===========================================================================


def test_orchestrate_called_once_with_correct_args():
    """The orchestrator is called exactly once per request."""
    orchestrate = _make_orchestrate_mock()
    sb = _make_sb_mock()

    with patch("app.routes.generate.get_client", return_value=sb):
        _gen_route._ORCHESTRATE_FN = orchestrate
        _gen_route._IMPORT_ERROR = None
        client = TestClient(app, raise_server_exceptions=False)
        client.post(
            "/api/generate",
            json={"author_id": "dickens", "prompt": "A foggy night."},
        )

    orchestrate.assert_awaited_once()


def test_orchestrate_receives_expected_model_id():
    """model_id passed to orchestrate equals WATSONX_MODEL_ID constant."""
    orchestrate = _make_orchestrate_mock()
    sb = _make_sb_mock()

    with patch("app.routes.generate.get_client", return_value=sb):
        _gen_route._ORCHESTRATE_FN = orchestrate
        _gen_route._IMPORT_ERROR = None
        TestClient(app, raise_server_exceptions=False).post(
            "/api/generate",
            json={"author_id": "dickens", "prompt": "A foggy night."},
        )

    _, kwargs = orchestrate.call_args
    assert kwargs["model_id"] == _EXPECTED_MODEL_ID


def test_orchestrate_receives_author_uuid():
    """author_uuid (resolved from slug) is forwarded so RAG can filter by author."""
    orchestrate = _make_orchestrate_mock()
    sb = _make_sb_mock()

    with patch("app.routes.generate.get_client", return_value=sb):
        _gen_route._ORCHESTRATE_FN = orchestrate
        _gen_route._IMPORT_ERROR = None
        TestClient(app, raise_server_exceptions=False).post(
            "/api/generate",
            json={"author_id": "dickens", "prompt": "A foggy night."},
        )

    _, kwargs = orchestrate.call_args
    assert kwargs["author_uuid"] == _FAKE_AUTHOR_UUID


def test_orchestrate_receives_correct_prompt():
    """The raw prompt string is forwarded to the orchestrator unchanged."""
    orchestrate = _make_orchestrate_mock()
    sb = _make_sb_mock()
    prompt = "Describe a Victorian workhouse at midnight."

    with patch("app.routes.generate.get_client", return_value=sb):
        _gen_route._ORCHESTRATE_FN = orchestrate
        _gen_route._IMPORT_ERROR = None
        TestClient(app, raise_server_exceptions=False).post(
            "/api/generate",
            json={"author_id": "dickens", "prompt": prompt},
        )

    _, kwargs = orchestrate.call_args
    assert kwargs["prompt"] == prompt


def test_orchestrate_receives_style_profile_from_db():
    """The style_profile dict passed to orchestrate is the one fetched from Supabase."""
    orchestrate = _make_orchestrate_mock()
    custom_profile = {**_STUB_STYLE_PROFILE, "author_id": "custom-author"}
    sb = _make_sb_mock(profile_rows=[{"json_data": custom_profile}])

    with patch("app.routes.generate.get_client", return_value=sb):
        _gen_route._ORCHESTRATE_FN = orchestrate
        _gen_route._IMPORT_ERROR = None
        TestClient(app, raise_server_exceptions=False).post(
            "/api/generate",
            json={"author_id": "dickens", "prompt": "A foggy night."},
        )

    _, kwargs = orchestrate.call_args
    assert kwargs["style_profile"] == custom_profile


# ---------------------------------------------------------------------------
# system_prompt behaviour: vanilla=None, autoria=non-empty
#
# The orchestrator is a black-box at the route layer — the route only passes
# prompt+style_profile+author_id+model_id to it.  The internal Watsonx calls
# with system_prompt=None (vanilla) vs system_prompt=<conditioned> (autoria)
# are tested in the orchestrator unit tests (ai_pipeline/tests/).
#
# What we CAN assert here is that the orchestrate mock was called with a
# model_id that matches both branches (the route passes one model_id; the
# orchestrator is responsible for using it for both calls).
# ---------------------------------------------------------------------------


def test_model_id_forwarded_to_orchestrate_is_the_llama_constant():
    """The route always forwards meta-llama/llama-3-3-70b-instruct."""
    orchestrate = _make_orchestrate_mock()
    sb = _make_sb_mock()

    with patch("app.routes.generate.get_client", return_value=sb):
        _gen_route._ORCHESTRATE_FN = orchestrate
        _gen_route._IMPORT_ERROR = None
        TestClient(app, raise_server_exceptions=False).post(
            "/api/generate",
            json={"author_id": "dickens", "prompt": "A foggy night."},
        )

    _, kwargs = orchestrate.call_args
    assert kwargs["model_id"] == "meta-llama/llama-3-3-70b-instruct"


# ===========================================================================
# 7. Passport persistence — no raw prompt in json_payload
# ===========================================================================


def test_passports_insert_called_once():
    """sb.table('passports').insert is called exactly once on the happy path."""
    orchestrate = _make_orchestrate_mock()
    sb = _make_sb_mock()

    with patch("app.routes.generate.get_client", return_value=sb):
        _gen_route._ORCHESTRATE_FN = orchestrate
        _gen_route._IMPORT_ERROR = None
        resp = TestClient(app, raise_server_exceptions=False).post(
            "/api/generate",
            json={"author_id": "dickens", "prompt": "A foggy night."},
        )

    assert resp.status_code == 200
    sb.table("passports").insert.assert_called_once()


def test_passports_insert_contains_author_uuid():
    """The inserted passport row carries the resolved author UUID."""
    orchestrate = _make_orchestrate_mock()
    sb = _make_sb_mock()

    with patch("app.routes.generate.get_client", return_value=sb):
        _gen_route._ORCHESTRATE_FN = orchestrate
        _gen_route._IMPORT_ERROR = None
        TestClient(app, raise_server_exceptions=False).post(
            "/api/generate",
            json={"author_id": "dickens", "prompt": "A foggy night."},
        )

    inserted: dict = sb.table("passports").insert.call_args[0][0]
    assert inserted["author_id"] == _FAKE_AUTHOR_UUID


def test_passports_insert_contains_jws_token():
    """The inserted row has a jws_token string (from the passport envelope)."""
    orchestrate = _make_orchestrate_mock()
    sb = _make_sb_mock()

    with patch("app.routes.generate.get_client", return_value=sb):
        _gen_route._ORCHESTRATE_FN = orchestrate
        _gen_route._IMPORT_ERROR = None
        TestClient(app, raise_server_exceptions=False).post(
            "/api/generate",
            json={"author_id": "dickens", "prompt": "A foggy night."},
        )

    inserted: dict = sb.table("passports").insert.call_args[0][0]
    assert isinstance(inserted["jws_token"], str) and inserted["jws_token"]


def test_passport_json_payload_has_no_raw_prompt():
    """json_payload must not contain the raw prompt string under any key."""
    raw_prompt = "A foggy night on Baker Street."
    orchestrate = _make_orchestrate_mock()
    sb = _make_sb_mock()

    with patch("app.routes.generate.get_client", return_value=sb):
        _gen_route._ORCHESTRATE_FN = orchestrate
        _gen_route._IMPORT_ERROR = None
        TestClient(app, raise_server_exceptions=False).post(
            "/api/generate",
            json={"author_id": "dickens", "prompt": raw_prompt},
        )

    # Inspect the json_payload that was persisted to DB (same object returned
    # in the response and stored in passports).
    inserted: dict = sb.table("passports").insert.call_args[0][0]
    payload: dict = inserted["json_data"]

    # Recursively flatten all string values in the payload and assert the raw
    # prompt does not appear verbatim in any of them.
    def _all_strings(obj: Any) -> list[str]:
        if isinstance(obj, str):
            return [obj]
        if isinstance(obj, dict):
            return [s for v in obj.values() for s in _all_strings(v)]
        if isinstance(obj, list):
            return [s for item in obj for s in _all_strings(item)]
        return []

    assert raw_prompt not in _all_strings(
        payload
    ), "Raw prompt must not appear verbatim in the passport json_payload"


def test_passport_json_payload_has_user_prompt_hash():
    """json_payload.generation.user_prompt_hash must be present (privacy contract)."""
    inserted: dict = _get_inserted_passport()
    payload: dict = inserted["json_data"]
    assert "user_prompt_hash" in payload["generation"]


def test_passport_json_payload_user_prompt_hash_format():
    """user_prompt_hash follows the sha256:<hex> format."""
    inserted: dict = _get_inserted_passport()
    h = inserted["json_data"]["generation"]["user_prompt_hash"]
    assert h.startswith("sha256:") and len(h) == len("sha256:") + 64


def test_passport_json_payload_has_output_hash():
    """json_payload.generation.output_hash must be present."""
    inserted: dict = _get_inserted_passport()
    assert "output_hash" in inserted["json_data"]["generation"]


def test_passport_json_payload_output_hash_format():
    """output_hash follows the sha256:<hex> format."""
    inserted: dict = _get_inserted_passport()
    h = inserted["json_data"]["generation"]["output_hash"]
    assert h.startswith("sha256:") and len(h) == len("sha256:") + 64


def _get_inserted_passport() -> dict:
    """Helper: run a happy-path request and return the inserted passports row."""
    orchestrate = _make_orchestrate_mock()
    sb = _make_sb_mock()

    with patch("app.routes.generate.get_client", return_value=sb):
        _gen_route._ORCHESTRATE_FN = orchestrate
        _gen_route._IMPORT_ERROR = None
        TestClient(app, raise_server_exceptions=False).post(
            "/api/generate",
            json={"author_id": "dickens", "prompt": "A foggy night on Baker Street."},
        )

    return sb.table("passports").insert.call_args[0][0]


# ===========================================================================
# 8. Passport persistence failure does not abort the response
# ===========================================================================


def test_passport_db_failure_still_returns_200():
    """If passports.insert raises, the HTTP response is still 200.

    The passport was already issued; the client must receive it regardless of
    the persistence outcome.
    """
    orchestrate = _make_orchestrate_mock()
    sb = _make_sb_mock()
    # Make the passports insert blow up.
    sb.table("passports").insert.side_effect = RuntimeError("DB write failed")

    with patch("app.routes.generate.get_client", return_value=sb):
        _gen_route._ORCHESTRATE_FN = orchestrate
        _gen_route._IMPORT_ERROR = None
        resp = TestClient(app, raise_server_exceptions=False).post(
            "/api/generate",
            json={"author_id": "dickens", "prompt": "A foggy night."},
        )

    assert resp.status_code == 200


def test_passport_db_failure_response_still_contains_passport():
    """Even when DB persistence fails, the passport envelope is in the body."""
    orchestrate = _make_orchestrate_mock()
    sb = _make_sb_mock()
    sb.table("passports").insert.side_effect = RuntimeError("DB write failed")

    with patch("app.routes.generate.get_client", return_value=sb):
        _gen_route._ORCHESTRATE_FN = orchestrate
        _gen_route._IMPORT_ERROR = None
        body = (
            TestClient(app, raise_server_exceptions=False)
            .post(
                "/api/generate",
                json={"author_id": "dickens", "prompt": "A foggy night."},
            )
            .json()
        )

    assert "passport" in body
    assert body["passport"]["jws_token"]


# ===========================================================================
# 9. DATABASE_URL is propagated to the orchestrator (issue #87 / WO-06)
#
# The orchestrator hands this kwarg straight to
# autoria_ai.db.retrieve_top_k(database_url=...).  When the route omitted it,
# autoria_ai.db fell back to os.environ["DATABASE_URL"], the KeyError was
# swallowed by generator.py's `except Exception`, and every generation
# returned 200 with an unconditioned prompt and rag_sources: [].
# ===========================================================================

_TEST_DSN = "postgresql+asyncpg://user:pw@db.example.com:5432/postgres"


def _orchestrate_kwargs_with_settings(db_url: str | None) -> dict[str, Any]:
    """Run one happy-path request with ``settings.database_url = db_url``.

    Returns the kwargs the route passed to the orchestrator.
    """
    orchestrate = _make_orchestrate_mock()
    sb = _make_sb_mock()
    patched_settings = dataclasses.replace(_gen_route.settings, database_url=db_url)

    with (
        patch("app.routes.generate.get_client", return_value=sb),
        patch("app.routes.generate.settings", patched_settings),
    ):
        _gen_route._ORCHESTRATE_FN = orchestrate
        _gen_route._IMPORT_ERROR = None
        TestClient(app, raise_server_exceptions=False).post(
            "/api/generate",
            json={"author_id": "dickens", "prompt": "A foggy night."},
        )

    _, kwargs = orchestrate.call_args
    return kwargs


def test_orchestrate_receives_database_url_kwarg():
    """The route must pass ``database_url`` — its absence is the #87 bug."""
    kwargs = _orchestrate_kwargs_with_settings(_TEST_DSN)
    assert "database_url" in kwargs


def test_orchestrate_receives_configured_dsn():
    """The DSN forwarded is exactly the one resolved by app.config."""
    kwargs = _orchestrate_kwargs_with_settings(_TEST_DSN)
    assert kwargs["database_url"] == _TEST_DSN


def test_orchestrate_receives_none_when_database_url_unset():
    """An unset DATABASE_URL forwards None — RAG degrades, request still 200.

    The explicit one-time startup log (app.config) is what surfaces the
    misconfiguration; the request path keeps its documented degradation.
    """
    kwargs = _orchestrate_kwargs_with_settings(None)
    assert kwargs["database_url"] is None


def test_route_reads_dsn_from_settings_not_os_environ(monkeypatch):
    """The DSN comes from app.config.settings, not a direct os.getenv call.

    Guards the WO-06 contract: config.py owns DATABASE_URL (including the
    +asyncpg normalisation), so a raw env var that config never saw must not
    reach the orchestrator.
    """
    monkeypatch.setenv("DATABASE_URL", "postgresql://raw:env@bypass.example.com:5432/postgres")
    kwargs = _orchestrate_kwargs_with_settings(_TEST_DSN)
    assert kwargs["database_url"] == _TEST_DSN
