---
mode: GenerationConductor
sprint: 2
date: 2026-07-21
task: Implement backend Watsonx client (IAM, backoff 1/2/4, 8s timeout) + integration test
outcome: Landed app/services/watsonx_client.py; unit tests green; live call blocked by IBM Cloud project without WML instance association (403)
---

# Session — Watsonx client (Sprint 2)

## Mode

**GenerationConductor** (CTRO + plan-first pattern from `bob/playbook.md`).

## Context

Sprint 2 backlog item: thin Watsonx wrapper at `backend/app/services/watsonx_client.py` using `ibm-watsonx-ai`, reading IAM credentials from `app.config`, exponential backoff 1s/2s/4s, hard 8s timeout per attempt, `generate(prompt, system_prompt, model_id, params) -> str`, plus a real-Watsonx integration test.

## Plan (accepted)

1. Add `app/services/` package under the installable `app*` layout.
2. Implement client with `ModelInference.chat`, `max_retries=0`, `validate=False`, `ThreadPoolExecutor` timeout (Windows-safe).
3. Add `ibm-watsonx-ai>=1.0` to backend `pyproject.toml` + `requirements.txt`.
4. Unit tests with mocks; `@pytest.mark.integration` + `skipif` for live call.

## Result

- Client + deps + tests implemented.
- Unit tests: **5 passed**.
- Integration test: hits real endpoint; **403** `no_associated_service_instance_error` — Watsonx project is not linked to a WML instance. Credentials and URL are present; IBM Cloud association must be fixed before the live test can pass.

## Follow-up for humans

In IBM Cloud → watsonx project → associate a **Watson Machine Learning** service instance (same region as `WATSONX_URL`), then re-run:

```bash
cd backend
pytest -m integration tests/test_watsonx_client.py -v
```
