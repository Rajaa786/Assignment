# Plan: INFO-tier per-step LLM logging + overridable LOG_FORMAT

## Context
On the `/ask` (NL Q&A) path the user cannot see, per step, what was sent to the model,
what the model returned, and which SQL ran. Today the trace exists but is **PII-tiered**
(ADR-0013, §8): the raw model output is logged only at `qa_sql_candidate` **DEBUG**, the
executed SQL is never logged raw (only `sha8`/`chars` at INFO), and the prompt is never
logged. The container runs at `INFO`, so none of it is visible.

The user has decided (explicitly, accepting the tradeoff) to log the **prompt input, the
raw model output, and the executed SQL at `INFO`** so each step is visible in `docker logs`
without flipping to DEBUG. This **deliberately overrides §8** ("logs never contain salary
amounts") because a generated `WHERE` can embed a numeric salary threshold. Per §17 the
charter must be updated in the same change, not silently contradicted.

Separately: `LOG_FORMAT: json` is hardcoded in the compose files, making `docker logs`
unreadable with no override. Make it `${LOG_FORMAT:-json}` (and add `${LOG_LEVEL:-INFO}`)
for parity with the existing `${VAR:-default}` env pattern.

## Changes

### 1. `backend/app/services/qa_service.py` — promote raw content to INFO
- `respond_to_natural_language_query`: after building the prompt, emit a new INFO event
  `qa_prompt_built` carrying the full `system_prompt` and `question` (the input to the
  model). Note: the prompt is static/large — verbose but amount-free except any threshold
  in the user's question (already logged today).
- `_sql_for`: change `logger.debug("qa_sql_candidate", sql=candidate)` (line 110) to
  **INFO** so the raw model output is visible; add the raw `sql=verdict.sql` field to the
  existing `qa_sql_generated` INFO event (keep `sql_sha8`/`sql_chars`).
- `_execute`: add raw `sql=sql` to the `qa_executed` INFO event (which query ran).
- Update the method/module docstrings (lines 1-7, 44-61) to state raw SQL/prompt are now
  INFO, not DEBUG — keep docstrings truthful (§10).

### 2. Charter + ADR (required by §17 — document the deviation)
- `CLAUDE.md` §8: amend the "Logs never contain salary amounts" bullet to record that on
  the internal-only Q&A path the prompt, model output, and executed SQL are logged at INFO
  (a threshold amount in a generated `WHERE` may appear); risk accepted for a single-tenant
  internal tool; rows/compensation values are still never logged.
- `docs/decisions/0013-*.md`: add a "Superseded/Amended" note (or a short follow-up ADR)
  recording the shift from DEBUG-tier to INFO-tier raw SQL, with the reasoning above.

### 3. Compose — overridable logging (answers "why hardcoded json")
- `docker-compose.yml` and `docker-compose.images.yml`: change `LOG_FORMAT: json` to
  `LOG_FORMAT: ${LOG_FORMAT:-json}`; add `LOG_LEVEL: ${LOG_LEVEL:-INFO}`. Lets the user set
  `LOG_FORMAT=console` in the gitignored root `.env` for readable `docker logs`, no rebuild.

### 4. Tests — `backend/tests/integration/test_request_logging.py`
- Add a test that POSTs `/api/v1/ask` inside `capture_logs()` and asserts the INFO events
  `qa_prompt_built`, `qa_sql_generated` (now carrying `sql`), and `qa_executed` (carrying
  `sql`) fire. Use the stub LLM client (no network) — follow the existing `capture_logs`
  pattern in this file.

## Verification
- `cd backend && .venv/bin/python -m pytest -q` (full suite green; new logging test passes).
- `.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy app` clean.
- `docker compose up -d --build` then `LOG_FORMAT=console` in root `.env`; `curl -X POST
  localhost:8000/api/v1/ask -d '{"question":"avg salary by department"}'` → `docker logs`
  shows `qa_prompt_built` (prompt+question), raw model output, and `qa_executed` with the
  SELECT, all at INFO, in readable console format.

---

# (Earlier, completed) Plan: verify delete API + commit .gitignore

## Context
User asked to (a) exercise the employee delete API and confirm the DB updates and the test
passes, (b) confirm whether the Gemini API key is set in the new Docker build, and
(c) commit the pending `.gitignore` change (already confirmed "yes").

Investigation shows (a) and (b) need **no code change** — the delete path is already
implemented, tested, and green; the Gemini key is intentionally not baked in. The only
remaining action requiring approval is the commit.

## Findings (no work needed)
- **Delete API**: `DELETE /api/v1/employees/{id}` → 204. Soft-delete stamps `deleted_at`
  (`func.now()`) then commits in the service layer — DB updates correctly.
  - `backend/app/api/employees.py:130`
  - `backend/app/services/employee_service.py:126`
  - `backend/app/repositories/employee_repository.py:155`
- **Test**: `test_delete_soft_deletes_employee` (`backend/tests/integration/test_employees_api.py:93`)
  asserts 204 → GET 404 → list total 0. Ran it: **1 passed**.
- **Gemini key in Docker**: `GEMINI_API_KEY: ${GEMINI_API_KEY:-}` passthrough, default empty
  (`docker-compose.yml:18`, `docker-compose.images.yml:20`). No `.env` present; nothing baked
  into the image. Charter §8 (no secrets in code). With `LLM_PROVIDER=auto` + no keys → offline stub.

## Action to execute (the only change)
1. `git add .gitignore`
2. Commit:
   ```
   chore: gitignore local data dir and compose override

   Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
   ```

## Verification
- `git show --stat HEAD` shows only `.gitignore` changed (`.data/` + `docker-compose.override.yml` ignore lines).
- Working tree clean afterward.
- (already done) `cd backend && .venv/bin/python -m pytest tests/integration/test_employees_api.py::test_delete_soft_deletes_employee -q` → passes.
