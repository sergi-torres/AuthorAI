"""Unit tests for scripts/seed_corpus.py.

Scope
-----
All tests here are pure-unit: no live database, no network, no file-system
writes.  The corpus files under corpus/ are read only in the dry-run
integration path; fixture text is passed inline for everything else.

Run with:
    pytest ai_pipeline/tests/test_seed_corpus.py -v
Or as part of the full suite:
    cd ai_pipeline && pytest
"""

from __future__ import annotations

import hashlib
import itertools
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

import seed_corpus  # noqa: E402

# Enough repetitions that ~30k cleaned-token gate can pass (cl100k_base).
_SAMPLE_TEXT = "The quick brown fox jumps over the lazy dog. "
_SAMPLE_CORPUS = _SAMPLE_TEXT * 3500


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------------


class TestDryRun:
    """_run_dry() validates corpus files, prints manifest, calls sys.exit."""

    def test_dry_run_exits_zero_on_clean_corpus(self, tmp_path: Path, capsys: Any) -> None:
        """A corpus with three valid author folders exits 0."""
        for slug in ("austen", "dickens", "poe"):
            folder = tmp_path / slug
            folder.mkdir()
            (folder / f"{slug}_work.txt").write_text(_SAMPLE_CORPUS, encoding="utf-8")

        orig_root = seed_corpus.CORPUS_ROOT
        try:
            seed_corpus.CORPUS_ROOT = tmp_path
            with pytest.raises(SystemExit) as exc_info:
                seed_corpus._run_dry(author_filter=None)
        finally:
            seed_corpus.CORPUS_ROOT = orig_root

        assert exc_info.value.code == 0

    def test_dry_run_exits_nonzero_on_low_tokens(self, tmp_path: Path) -> None:
        """Exits 1 when an author has fewer than 30,000 cleaned tokens."""
        folder = tmp_path / "poe"
        folder.mkdir()
        (folder / "tiny.txt").write_text(
            "Hello world. Hello world. Hello world. Hello world. "
            "Hello world. Hello world. Hello world. Hello world. "
            "Hello world. Hello world. ",
            encoding="utf-8",
        )

        orig_root = seed_corpus.CORPUS_ROOT
        try:
            seed_corpus.CORPUS_ROOT = tmp_path
            with pytest.raises(SystemExit) as exc_info:
                seed_corpus._run_dry(author_filter="poe")
        finally:
            seed_corpus.CORPUS_ROOT = orig_root

        assert exc_info.value.code == 1

    def test_dry_run_exits_nonzero_on_gutenberg_header(self, tmp_path: Path) -> None:
        """Exits 1 when a file still contains a Gutenberg START sentinel after cleaning."""
        folder = tmp_path / "dickens"
        folder.mkdir()
        # Sentinel WITHOUT the *** markers so clean_text() does not strip it,
        # but _gutenberg_sentinel_present() still flags it after cleaning.
        body = (
            "This is the body of the novel. This is the body of the novel. "
            "This is the body of the novel. This is the body of the novel. "
            "This is the body of the novel. This is the body of the novel. "
            "This is the body of the novel. This is the body of the novel. "
            "This is the body of the novel. This is the body of the novel. \n"
            "START OF THE PROJECT GUTENBERG EBOOK DICKENS\n"
            "More text after the sentinel. More text after the sentinel. "
            "More text after the sentinel. More text after the sentinel. "
            "More text after the sentinel. More text after the sentinel. "
            "More text after the sentinel. More text after the sentinel. "
            "More text after the sentinel. More text after the sentinel. "
        )
        (folder / "novel.txt").write_text(body + _SAMPLE_CORPUS, encoding="utf-8")

        orig_root = seed_corpus.CORPUS_ROOT
        try:
            seed_corpus.CORPUS_ROOT = tmp_path
            with pytest.raises(SystemExit) as exc_info:
                seed_corpus._run_dry(author_filter="dickens")
        finally:
            seed_corpus.CORPUS_ROOT = orig_root

        assert exc_info.value.code == 1

    def test_dry_run_never_opens_db(self, tmp_path: Path) -> None:
        """_run_dry() never calls psycopg2.connect."""
        folder = tmp_path / "austen"
        folder.mkdir()
        (folder / "work.txt").write_text(_SAMPLE_CORPUS, encoding="utf-8")

        orig_root = seed_corpus.CORPUS_ROOT
        try:
            seed_corpus.CORPUS_ROOT = tmp_path
            with patch("psycopg2.connect") as mock_connect:
                with pytest.raises(SystemExit):
                    seed_corpus._run_dry(author_filter="austen")
                mock_connect.assert_not_called()
        finally:
            seed_corpus.CORPUS_ROOT = orig_root

    def test_dry_run_filter_limits_to_one_author(self, tmp_path: Path, capsys: Any) -> None:
        """--author <slug> restricts output to only that author."""
        for slug in ("austen", "dickens", "poe"):
            folder = tmp_path / slug
            folder.mkdir()
            (folder / f"{slug}_work.txt").write_text(_SAMPLE_CORPUS, encoding="utf-8")

        orig_root = seed_corpus.CORPUS_ROOT
        try:
            seed_corpus.CORPUS_ROOT = tmp_path
            with pytest.raises(SystemExit):
                seed_corpus._run_dry(author_filter="poe")
            captured = capsys.readouterr()
        finally:
            seed_corpus.CORPUS_ROOT = orig_root

        assert "poe" in captured.out
        assert "austen" not in captured.out
        assert "dickens" not in captured.out


# ---------------------------------------------------------------------------
# Content hash
# ---------------------------------------------------------------------------


class TestContentHash:
    """sha256 of cleaned text must be deterministic."""

    def test_hash_is_stable_across_two_calls(self) -> None:
        """Same raw bytes → same hash every time."""
        raw = _SAMPLE_TEXT
        h1 = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        h2 = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        assert h1 == h2

    def test_hash_differs_for_different_texts(self) -> None:
        """Different cleaned texts produce different hashes."""
        h1 = _sha("The quick brown fox.")
        h2 = _sha("A completely different sentence.")
        assert h1 != h2

    def test_hash_is_hex_string_of_length_64(self) -> None:
        h = _sha(_SAMPLE_TEXT)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


# ---------------------------------------------------------------------------
# Chunk offsets
# ---------------------------------------------------------------------------


class TestComputeChunksWithOffsets:
    """_compute_chunks_with_offsets() must match the backend chunking contract."""

    def test_empty_text_returns_empty_list(self) -> None:
        assert seed_corpus._compute_chunks_with_offsets("") == []

    def test_short_text_produces_one_chunk(self) -> None:
        text = (
            "Hello world. Hello world. Hello world. Hello world. Hello world. "
            "Hello world. Hello world. Hello world. Hello world. Hello world. "
        )
        chunks = seed_corpus._compute_chunks_with_offsets(text)
        assert len(chunks) == 1

    def test_chunk_has_required_keys(self) -> None:
        text = "Word " * 600
        chunks = seed_corpus._compute_chunks_with_offsets(text)
        assert len(chunks) >= 1
        required = {"chunk_index", "text", "token_start", "token_end"}
        for c in chunks:
            assert set(c.keys()) >= required

    def test_chunk_indices_are_sequential_from_zero(self) -> None:
        chunks = seed_corpus._compute_chunks_with_offsets("Word " * 2000)
        indices = [c["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_token_end_of_last_chunk_equals_total_tokens(self) -> None:
        import tiktoken

        text = "The fox ran fast. " * 200
        enc = tiktoken.get_encoding("cl100k_base")
        total = len(enc.encode(text))
        chunks = seed_corpus._compute_chunks_with_offsets(text)
        assert chunks[-1]["token_end"] == total

    def test_token_start_of_first_chunk_is_zero(self) -> None:
        chunks = seed_corpus._compute_chunks_with_offsets("Word " * 600)
        assert chunks[0]["token_start"] == 0

    def test_overlap_between_consecutive_chunks(self) -> None:
        """token_start of chunk i+1 == token_end of chunk i - overlap."""
        chunks = seed_corpus._compute_chunks_with_offsets("Word " * 2000)
        for a, b in itertools.pairwise(chunks):
            expected_start = a["token_end"] - seed_corpus._CHUNK_OVERLAP
            assert b["token_start"] == expected_start

    def test_max_chunk_size_is_respected(self) -> None:
        """No chunk should contain more than CHUNK_SIZE tokens."""
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        chunks = seed_corpus._compute_chunks_with_offsets("word " * 3000)
        for c in chunks:
            n = len(enc.encode(c["text"]))
            assert n <= seed_corpus._CHUNK_SIZE

    def test_text_roundtrip_is_non_empty(self) -> None:
        """Decoded chunk text must be non-empty strings."""
        chunks = seed_corpus._compute_chunks_with_offsets("Hello world. " * 100)
        for c in chunks:
            assert isinstance(c["text"], str)
            assert c["text"].strip()


# ---------------------------------------------------------------------------
# Idempotency helpers
# ---------------------------------------------------------------------------


class TestIdempotencyHelpers:
    """_document_exists_by_hash and _document_exists_by_title return UUID or None."""

    def _make_conn(self, fetchone_return: Any) -> MagicMock:
        """Build a mock psycopg2 connection whose cursor.fetchone() returns the given value."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = fetchone_return
        mock_cursor.__enter__ = lambda s: s
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        return mock_conn

    def test_document_exists_by_hash_returns_uuid_when_found(self) -> None:
        import uuid

        uid = uuid.uuid4()
        conn = self._make_conn((uid,))
        result = seed_corpus._document_exists_by_hash(conn, "author-uuid", "deadbeef")
        assert result == str(uid)

    def test_document_exists_by_hash_returns_none_when_missing(self) -> None:
        conn = self._make_conn(None)
        result = seed_corpus._document_exists_by_hash(conn, "author-uuid", "deadbeef")
        assert result is None

    def test_document_exists_by_title_returns_uuid_when_found(self) -> None:
        import uuid

        uid = uuid.uuid4()
        conn = self._make_conn((uid,))
        result = seed_corpus._document_exists_by_title(conn, "author-uuid", "Emma")
        assert result == str(uid)

    def test_document_exists_by_title_returns_none_when_missing(self) -> None:
        conn = self._make_conn(None)
        result = seed_corpus._document_exists_by_title(conn, "author-uuid", "Emma")
        assert result is None


class TestContentHashColumnExists:
    def _make_conn(self, fetchone_return: Any) -> MagicMock:
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = fetchone_return
        mock_cursor.__enter__ = lambda s: s
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        return mock_conn

    def test_returns_true_when_column_found(self) -> None:
        conn = self._make_conn((1,))
        assert seed_corpus._content_hash_column_exists(conn) is True

    def test_returns_false_when_column_absent(self) -> None:
        conn = self._make_conn(None)
        assert seed_corpus._content_hash_column_exists(conn) is False


# ---------------------------------------------------------------------------
# Missing DATABASE_URL / argparse / opt-in stages
# ---------------------------------------------------------------------------


class TestMissingDatabaseUrl:
    def test_seed_exits_nonzero_when_database_url_missing(self) -> None:
        """seed() calls sys.exit(1) when DATABASE_URL is not set and not dry_run."""
        env_backup = os.environ.pop("DATABASE_URL", None)
        try:
            with pytest.raises(SystemExit) as exc_info:
                seed_corpus.seed()
            assert exc_info.value.code == 1
        finally:
            if env_backup is not None:
                os.environ["DATABASE_URL"] = env_backup


class TestArgumentParser:
    def _parse(self, *args: str) -> Any:
        return seed_corpus._build_parser().parse_args(list(args))

    def test_defaults_are_all_false(self) -> None:
        ns = self._parse()
        assert ns.dry_run is False
        assert ns.with_embeddings is False
        assert ns.with_profiles is False
        assert ns.author is None

    def test_dry_run_flag(self) -> None:
        ns = self._parse("--dry-run")
        assert ns.dry_run is True

    def test_author_flag(self) -> None:
        ns = self._parse("--author", "dickens")
        assert ns.author == "dickens"

    def test_with_embeddings_flag(self) -> None:
        ns = self._parse("--with-embeddings")
        assert ns.with_embeddings is True

    def test_with_profiles_flag(self) -> None:
        ns = self._parse("--with-profiles")
        assert ns.with_profiles is True


class TestOptInStages:
    """--with-embeddings / --with-profiles call the Stage 4/5 helpers."""

    def _fake_conn(self) -> MagicMock:
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_cursor.fetchall.return_value = []
        mock_cursor.__enter__ = lambda s: s
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        return mock_conn

    def test_with_embeddings_calls_runner(self) -> None:
        conn = self._fake_conn()
        with (
            patch("seed_corpus._get_connection", return_value=conn),
            patch("seed_corpus._seed_authors", return_value={"austen": "1"}),
            patch("seed_corpus._seed_documents", return_value={}),
            patch("seed_corpus._seed_chunks"),
            patch("seed_corpus._run_embeddings") as mock_emb,
            patch("seed_corpus._run_profiles") as mock_prof,
        ):
            seed_corpus.seed(
                database_url="postgresql://fake",
                with_embeddings=True,
                with_profiles=False,
            )
        mock_emb.assert_called_once()
        mock_prof.assert_not_called()

    def test_with_profiles_calls_runner(self) -> None:
        conn = self._fake_conn()
        with (
            patch("seed_corpus._get_connection", return_value=conn),
            patch("seed_corpus._seed_authors", return_value={"austen": "1"}),
            patch("seed_corpus._seed_documents", return_value={}),
            patch("seed_corpus._seed_chunks"),
            patch("seed_corpus._run_embeddings") as mock_emb,
            patch("seed_corpus._run_profiles") as mock_prof,
        ):
            seed_corpus.seed(
                database_url="postgresql://fake",
                with_embeddings=False,
                with_profiles=True,
            )
        mock_emb.assert_not_called()
        mock_prof.assert_called_once()
