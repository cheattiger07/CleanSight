# CleanSight Handoff (handoff.md)

Generated 2026-10-16 from a compacted conversation. Items are marked **[CONFIRMED]** (the user reported it working or I saw the file contents), **[INSTRUCTED]** (I gave the instructions but the user hasn't confirmed), or **[VERIFY]** (can't be recovered reliably).

---

## 1. Project overview

- **Purpose:** CleanSight is a data-cleaning web app. Users upload CSV/XLSX files, run cleaning engines, then download results (CSV, Excel with highlights, PDF quality report).
- **Version:** building **v2** from a working v1.
- **Long-term goal:** a production SaaS (Pro tier ₹999/month eventually). Right now there is a cheaper **Student plan (₹199/month)**.
- **Current audience:** college students and researchers with datasets of about 600–700 rows. AI bot and analytics features come later for professional clients.
- **User:** beginner, Windows/PowerShell, VS Code. Project path: `C:\Users\praav\OneDrive\Documents\My Projects\CleanSight`.
- **Live URL:** https://cleansight-zajg.onrender.com
- **Stack:**
  - Backend: Flask 3.1.3, Pandas 3.0.2, OpenPyXL, Python 3.14, gunicorn (`Procfile`: `web: gunicorn app:app`).
  - Frontend: HTML/CSS/JS Jinja templates.
  - Database: Neon Postgres. URI scheme is `postgresql+psycopg://`. Local `.env` and Render share the same Neon DB.
  - Hosting: Render (free tier, sets `RENDER=true`).
  - Email: Brevo transactional HTTP API (`https://api.brevo.com/v3/smtp/email`, header `api-key`, free tier 300/day).
  - Planned payments: Razorpay.
- **Dependencies:**
  - Flask-SQLAlchemy 3.1.1, with `sqlalchemy<2.1` pinned (see bugs).
  - Flask-Login 0.6.3, Flask-WTF 1.2.2 (CSRFProtect), Flask-Limiter (in-memory storage).
  - `psycopg[binary]==3.2.10`, `requests`, `python-dotenv`, `itsdangerous`.

## 2. Features completed

**Phase 1 (Auth) is done except R2 storage [CONFIRMED by user tests, live on Render]:**
- Signup, login, POST-only logout, and email verification via a signed, expiring, single-use token (salt `email-verify`). Unverified users cannot upload or clean (`verified_required`).
- Forgot and reset password (salt `password-reset`). The response is the same whether or not the email exists, and resend/reset emails are throttled to once per 60s per session.
- Security:
  - CSRF on all POST forms.
  - Ownership checks via `get_owned_file_or_404`.
  - Cookies are HttpOnly, SameSite=Lax, and Secure in production.
  - Fail-safe `SECRET_KEY`.
  - Rate limiting and ProxyFix(x_for=1).
  - Formula-injection sanitization and UUID filenames.
- File lifecycle:
  - Files expire after `FILE_TTL_HOURS = 2`, cleaned lazily by `safe_cleanup()` on upload and login (there is no scheduler on the free tier). Verified working.
  - A "delete my file now" button on the results page works.

**Phase 2A–2B (plans and usage) [CONFIRMED]:**
- `plans.py` has a `PLANS` dict:
  - **free:** 3 files/month, 5 MB, no Excel, no PDF.
  - **student:** ₹199, 30 files/month, 16 MB, Excel + PDF + cleaning log.
  - **pro:** ₹999, 200 files/month, 16 MB, all features.
  - Helpers: `get_plan(tier)`, `plan_for_user(user)`.
- `usage_events` table with `UsageEvent` model and unique constraint `uq_usage_user_file`.
- `usage.py` has `files_used_this_month`, `has_counted`, `record_file_usage` (idempotent), and `month_start` (UTC).
- `test_usage.py` passed: before 0, first record True, duplicate False, after 1, cleaned up 0.
- The usage tables were created with `create_tables.py` (one-off `db.create_all()`).

**Phase 2C (server-side gating) [INSTRUCTED, NOT confirmed applied or tested]:**
- `app.py` additions:
  - Imports `plan_for_user` and the usage helpers.
  - `LIMIT_MESSAGES` dict and `limit_response(reason)`, which renders `limit_reached.html` with a 403.
  - `inject_plan` context processor, giving templates `user_plan` and `usage_this_month`.
- `/upload`: after `safe_cleanup()`, check the monthly file count. After `file.save()`, check size against `plan["max_file_mb"]` and delete the file if too big.
- `/clean`: if the file hasn't been counted yet and the user is at their limit, block. After writing the cleaned CSV, call `record_file_usage`.
- `/download/excel` and `/report`: blocked unless the plan allows. CSV stays free.
- New template `limit_reached.html` (extends `auth_base.html`, shows the message and a disabled "Upgrade to Student ₹199/month (payments launching soon)" button).
- `result.html`: the Excel and PDF cards show "🔒 Student plan" for free users, and a usage line goes inline-styled in the "Your Data" card.
- `index.html`, given in the last reply, not confirmed applied:
  - Change line 257 to `Max {{ user_plan.max_file_mb }} MB`.
  - Add "Files are automatically deleted after 2 hours." and a plan/usage line.
  - Wrap the `fileInput` script in `if (input)`.
  - Replace the duplicate "Fast" footer span.

## 3. Key files, routes, modules

- **Python:**
  - `app.py`: main app and routes.
  - `models.py`: `User`, `UploadedFile`, `UsageEvent`.
  - `extensions.py`: `db`, `csrf`, `limiter`. This avoids circular imports.
  - `plans.py`, `usage.py`, `tokens.py` (`generate_token`/`confirm_token`), `mailer.py` (`send_email`, `send_verification_email`, `send_reset_email`).
  - `utils.py` and `outlier_engine.py`: cleaning engines (9 engines).
  - `create_tables.py`, `test_usage.py` (temporary, can be deleted).
- **Routes:** `/` (function `home`), `/upload`, `/clean` (POST), `/download` (POST), `/download/excel`, `/download/csv`, `/report`, `/delete-file` (POST), `/signup`, `/login`, `/logout` (POST), `/verify/<token>`, `/resend-verification`, `/forgot-password`, `/reset-password/<token>`. Error handlers: 413, CSRFError, 429.
- **Templates:** `index.html`, `tool.html`, `result.html`, `_nav.html` (fixed 48px top bar plus unverified banner), `auth_base.html`, `login.html`, `signup.html`, `forgot_password.html`, `reset_password.html`, `limit_reached.html`.
- **Env vars (names only; never paste values into chat or git):** `SECRET_KEY`, `DATABASE_URL`, Brevo API key and sender, `APP_BASE_URL` (Render URL on Render, localhost in `.env`).
- **Docs sent earlier:** `CleanSight_v1_Audit_Record.md`, `CleanSight_v2_Production_Checklist.md`, `CleanSight_Master_Production_Checklist.md`, `cleansight_sample_test.csv`.

## 4. Bugs

**Fixed [CONFIRMED]:**
- Nav overlapping page buttons: now a full-width fixed bar with body padding.
- `/clean` 405: the form is now POST and the route reads `request.form`.
- `ImportError: send_email`: `mailer.py` was empty or unsaved.
- `url_for` not imported.
- `BuildError`: the endpoint is `home`, not `index`; the code uses `redirect("/")`.
- SQLAlchemy DLL block (Windows Application Control blocked 2.1's `_row_cy`): pinned `sqlalchemy<2.1`.
- Duplicate signup flash message.
- Unverified users could use the app: fixed with `verified_required`.
- Auto-expiry never ran: `safe_cleanup()` is now called in `upload()` and `login()`.

**Open or unresolved:**
- Possible local-time bug: `UploadedFile.created_at` default may use local `datetime.now` instead of UTC. [VERIFY in `models.py`]
- `result.html` CSS: an HTML comment inside `<style>` (about line 673, `<!-- EXPORT CARDS ... -->`) should be `/* EXPORT CARDS */`, and `var(--card)` should be `var(--bg-card)`.
- `index.html`: the "5 Cleaning Engines" text should say 9, and the footer has a duplicate "Fast".
- Confirm `format="mixed"` in `to_datetime_safe` (`utils.py`) and in `outlier_engine.py`.
- Unresolved checklist items: SC3, M5, C9, C15, C19.
- `tool.html` flash rendering, favicon 404.
- Flask-Limiter in-memory storage warning (fine for one worker, needs shared storage if scaling).
- Keep `FILE_TTL_HOURS` and the UI text in sync (currently 2 hours).
- Git CRLF warnings: harmless.

## 5. Decisions made

- Follow the user's own Master Specification phase order (I once wrongly called Phase 2 "flags"; Phase 2 is Payments).
- Student price ₹199 (suggested). Proposed: 7-day refund, no trial, Pro hidden until AI features exist.
- Cloudflare R2 per-user storage is deferred to the end of the project.
- Google sign-in is an optional later add-on, not a replacement for Brevo.
- Gating is server-side only; plan changes come only from Razorpay webhooks.
- Usage is counted per unique file cleaned per user per UTC month. Re-cleaning the same file doesn't count again.
- "Shorter expiry after download" needs a `downloaded_at` column (ALTER TABLE). Deferred.
- `db.create_all()` only creates new tables. Changes to existing tables need ALTER TABLE or migrations.

## 6. Status

- **Deployed:** Phase 1 is live on Render and tested by the user. [CONFIRMED]
- **Phase 2C:** code and templates were handed over. I don't know which edits the user applied, whether they tested, or whether anything was committed or pushed. [VERIFY]
- **Last commit I know of:** Phase 1 sign-off ("done and commit perfectly and dusted"). Nothing else is confirmed.
- **Not started:** Razorpay (2D–2G), Phases 3–7, pre-launch QA.

## 7. Next steps, in priority order

1. Confirm which 2C edits are applied in `app.py`, `result.html`, `index.html`, `limit_reached.html`. Paste the files if unsure.
2. Run the 2C tests:
   - Temporarily set free `files_per_month=1`. The second new file should be blocked, and re-cleaning the first should still work.
   - A free user's Excel and PDF should be blocked (403 limit page), with CSV still allowed.
   - Upload a file over 5 MB (for example 6 MB) as a free user. It should be blocked.
   - Set `plan_tier='student'` in Neon. Excel and PDF should work and a 6 MB file should be accepted.
   - Check `usage_events` rows in Neon.
   - Restore `files_per_month` to 3.
3. Commit: "Phase 2C: server-side plan gating", then deploy and smoke-test on Render.
4. **2D:** Razorpay test mode (account, test keys, ₹199 Student subscription, upgrade button, UPI AutoPay).
5. **2E:** webhook handler for `subscription.activated`, `.charged`, `.cancelled` and `payment.failed`, with signature verification. Update `plan_tier` only from webhooks, and log events.
6. **2F:** billing page.
7. **2G:** KYC, live keys, policy pages (terms, privacy, refund).
8. **Phase 3:** gunicorn workers, background queue, file/row caps, structured logging, Sentry, UptimeRobot, Flask-Talisman, cleanup job, shared limiter storage.
9. **Phase 4:** issue/flag data model. Shared record `{row, column, category, severity (red/orange), message, suggested_fix}`, detect → review → apply flow, Excel cell comments, an "Issues" column, sort/filter by error type, per-column suggested fixes, two-colour marking of only the problem cell, and the 10-category problem list.
10. **Phases 5–7:** UI/UX overhaul, then AI profile-summary via the Claude API, then retention features (history, presets, diff view, API, teams, audit logs, scheduled jobs, Sheets export, reports). The cleaning-log export for the Student plan also belongs here.
11. Pre-launch QA checklist. Cloudflare R2 comes last.

## 8. Instructions for the next AI assistant

- The user is a beginner. Go one small step at a time, explain each change, and give exact find/replace snippets with line context.
- Use Windows/PowerShell commands.
- Follow the user's spec phases. Don't reorder them.
- Never ask for or echo secrets (`.env`, API keys, DB URLs). Keep them out of git and chat.
- Security-first defaults: CSRF, ownership checks, server-side gating, and no trusting the client for plan or usage.
- After each step, ask the user to run specific tests and report pass or fail before moving on.
- Don't claim something is applied or working unless the user confirmed it. Ask them to paste the current file if unsure.
- Teach RAG/LLM concepts when the AI phase starts.
- Keep Brevo costs and free-tier limits in mind, because the user has no budget.
- Commit messages should be per-phase, for example "Phase 2C: ...".

## 9. What I can't reliably recover

- Exact current contents of the user's local files (`app.py`, `models.py`, `utils.py`, templates). Ask the user to paste them before editing.
- Whether 2C edits were applied, tested or committed, and any test results after the 2B `test_usage.py` run.
- The full wording of the user's Master Specification and checklists. Ask the user to re-attach the spec file.
- Exact text of SC3, M5, C9, C15, C19 (they are in `CleanSight_Master_Production_Checklist.md`).
- The `UploadedFile` column definitions and the `created_at` UTC question.
- The Render environment variable values, and which Brevo sender is verified.
- Full earlier conversation: `/root/.claude/projects/-home-claude/46a00415-0931-5206-9f94-fe25dfc1f280.jsonl` (cloud workspace, may be unavailable later).
