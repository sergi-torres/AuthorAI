"""Walk the whole demo path against a running AutorIA backend and report.

Runs the same sequence a judge would: list authors, read a Style DNA profile,
generate side by side, download the Passport, verify it, and confirm that a
tampered Passport is rejected. Prints a timing for each step and exits non-zero
if any check fails.

Usage
-----
    python scripts/smoke_demo.py                          # http://localhost:8000
    python scripts/smoke_demo.py --base-url https://autoria-api.up.railway.app
    python scripts/smoke_demo.py --author austen --repeat 3

Nothing here is a unit test: it hits the real database and real Watsonx, and
therefore costs a generation per run. That is the point — it is the only check
that exercises the deployed shape end to end.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_PROMPT = "A foggy London evening in the 1840s, seen from a hansom cab."

PASS = "PASS"
FAIL = "FAIL"


class Report:
    """Collects step outcomes so one failure does not hide the rest."""

    def __init__(self) -> None:
        self.rows: list[tuple[str, str, float, str]] = []

    def add(self, step: str, ok: bool, seconds: float, detail: str = "") -> None:
        self.rows.append((step, PASS if ok else FAIL, seconds, detail))
        mark = "OK " if ok else "XX "
        print(f"  {mark} {step:38} {seconds:6.2f}s  {detail}")

    def info(self, step: str, seconds: float, detail: str = "") -> None:
        """Record an observation that must never fail the run.

        The <8s SLA lives here rather than in `add`: the team decided on
        2026-07-28 that the demo is a recorded video, so a slow generation is
        worth knowing about but is not a broken build. A check that cries wolf
        on every production run stops being read.
        """
        print(f"  ·· {step:38} {seconds:6.2f}s  {detail}")

    @property
    def failed(self) -> list[tuple[str, str, float, str]]:
        return [r for r in self.rows if r[1] == FAIL]


def _request(url: str, payload: dict | None = None, timeout: float = 60.0):
    """GET, or POST when *payload* is given. Returns (status, parsed_body)."""
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as exc:
        body = exc.read()
        try:
            return exc.code, json.loads(body or b"null")
        except json.JSONDecodeError:
            return exc.code, {"raw": body[:400].decode(errors="replace")}


def _timed(fn, *args, **kwargs):
    t0 = time.monotonic()
    result = fn(*args, **kwargs)
    return result, time.monotonic() - t0


def run(base_url: str, author: str, prompt: str, report: Report) -> None:
    base = base_url.rstrip("/")

    (status, _), dt = _timed(_request, f"{base}/health", timeout=15)
    report.add("GET /health", status == 200, dt, f"status {status}")

    (status, authors), dt = _timed(_request, f"{base}/api/authors", timeout=20)
    ok = status == 200 and isinstance(authors, list) and len(authors) >= 3
    names = ", ".join(a.get("id", "?") for a in authors) if isinstance(authors, list) else "-"
    report.add("GET /api/authors", ok, dt, f"{names}")

    with_profile = (
        [a["id"] for a in authors if a.get("has_style_profile")]
        if isinstance(authors, list)
        else []
    )
    report.add(
        "authors have a StyleProfile",
        len(with_profile) >= 3,
        0.0,
        f"{len(with_profile)}/3 — a 0 here means the DB was never seeded with profiles",
    )

    (status, profile), dt = _timed(
        _request, f"{base}/api/authors/{author}/style-profile", timeout=20
    )
    ok = status == 200 and isinstance(profile, dict)
    vocab: list[str] = []
    if ok:
        raw_vocab = profile.get("distinctive_vocab") or []
        vocab = [t["term"] if isinstance(t, dict) else str(t) for t in raw_vocab][:6]
    report.add(f"GET style-profile ({author})", ok, dt, f"vocab: {', '.join(vocab) or '-'}")

    # The vocabulary is the one signal a viewer can judge without any tooling:
    # if these are common English words, TF-IDF ran without comparison corpora.
    generic = {"say", "know", "look", "come", "make", "time", "think", "good", "little"}
    if vocab:
        overlap = len(set(vocab) & generic)
        report.add(
            "distinctive vocab looks distinctive",
            overlap <= 2,
            0.0,
            f"{overlap}/6 are among the commonest English words",
        )

    (status, gen), dt = _timed(
        _request,
        f"{base}/api/generate",
        {"author_id": author, "prompt": prompt},
        timeout=90,
    )
    ok = status == 200 and isinstance(gen, dict) and {"vanilla", "autoria", "passport"} <= set(gen)
    detail = f"status {status}"
    token = ""
    if ok:
        van, aut = gen["vanilla"], gen["autoria"]
        passport = gen["passport"]
        payload = passport.get("json_payload", passport)
        rag = len(payload.get("rag_sources", []))
        token = passport.get("jws_token", "")
        detail = (
            f"vanilla fit={van['fit_score']} ({len(van['text'].split())}w) · "
            f"autoria fit={aut['fit_score']} ({len(aut['text'].split())}w) · rag={rag}"
        )
    report.add("POST /api/generate", ok, dt, detail)

    if ok:
        payload = gen["passport"].get("json_payload", gen["passport"])
        report.add(
            "Passport carries RAG sources",
            len(payload.get("rag_sources", [])) > 0,
            0.0,
            "empty means retrieval silently failed",
        )
        report.info(
            "latency vs the <8s SLA",
            dt,
            "within budget" if dt < 8.0 else "over the MVP SLA — recorded demo, so not fatal",
        )

    if not token:
        report.add("POST /api/passports/verify", False, 0.0, "no token to verify")
        return

    (status, ver), dt = _timed(
        _request, f"{base}/api/passports/verify", {"jws_token": token}, timeout=30
    )
    ok = status == 200 and bool(ver.get("valid"))
    report.add("verify a real Passport", ok, dt, f"valid={ver.get('valid')}")

    # Negative control: without this, a verifier that always says "valid" and a
    # correct one are indistinguishable.
    flipped = "a" if token[-6] != "a" else "b"
    tampered = token[:-6] + flipped + token[-5:]
    (status, ver2), dt = _timed(
        _request, f"{base}/api/passports/verify", {"jws_token": tampered}, timeout=30
    )
    codes = [e.get("code") for e in (ver2.get("errors") or [])]
    ok = status == 200 and ver2.get("valid") is False and "invalid_signature" in codes
    report.add("reject a tampered Passport", ok, dt, f"errors: {codes or '-'}")

    (status, jwks), dt = _timed(_request, f"{base}/.well-known/jwks.json", timeout=15)
    keys = jwks.get("keys", []) if isinstance(jwks, dict) else []
    ok = status == 200 and len(keys) == 1 and keys[0].get("alg") == "ES256" and "d" not in keys[0]
    kid = keys[0].get("kid") if keys else "-"
    report.add("GET /.well-known/jwks.json", ok, dt, f"kid={kid}, no private scalar")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--author", default="dickens")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="run the generate+verify loop N times to see latency spread",
    )
    args = parser.parse_args()

    print(f"\nAutorIA smoke test → {args.base_url}\n")
    report = Report()
    for i in range(args.repeat):
        if args.repeat > 1:
            print(f"--- run {i + 1}/{args.repeat}")
        run(args.base_url, args.author, args.prompt, report)

    failed = report.failed
    print()
    if failed:
        print(f"{len(failed)} check(s) FAILED:")
        for step, _, _, detail in failed:
            print(f"  - {step}: {detail}")
        return 1
    print(f"All {len(report.rows)} checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
