# CleanSight Handoff (handoff.md), updated 2026-10-21

Markers: **[CONFIRMED]** = the user reported it working or I saw the file contents. **[REPORTED]** = the user said it was done, with no detail. **[INSTRUCTED]** = I gave instructions but the user hasn't confirmed. **[VERIFY]** = unknown, check the real files.

This replaces the 2026-10-16 handoff. Phase 2C, 2D and 2E progress is new.

---

## 1. Project overview

- **Purpose:** CleanSight is a data-cleaning web app. Users upload CSV/XLSX, run cleaning engines, then download results (CSV, highlighted Excel, PDF quality report).
- **Version:** building **v2** from a working v1.
- **Goal:** a production SaaS. Student plan ₹199/month now, Pro ₹999/month later.
- **Audience now:** college students and researchers (datasets of about 600–700 rows). AI bot and analytics come later for professional clients.
- **User:** beginner, Windows/PowerShell, VS Code. Path: `C:\Users\praav\OneDrive\Documents\My Projects\CleanSight`.
- **Live URL:** https://cleansight-zajg.onrender.com
- **Stack:**
  - Flask 3.1.3, Pandas 3.0.2, OpenPyXL, Python 3.14, gunicorn (`Procfile`: `web: gunicorn app:app`), Jinja HTML/CSS/JS.
  - Neon Postgres (`postgresql+psycopg://`), shared by local `.env` and Render.
  - Render free tier. Brevo email (HTTP API). Razorpay payments (REST via `requests`, not the `razorpay` package).
- **Dependencies:** Flask-SQLAlchemy 3.1.1 with `sqlalchemy<2.1` pinned, Flask-Login 0.6.3, Flask-WTF 1.2.2 (CSRF), Flask-Limiter (in-memory), `psycopg[binary]==3.2.10`, `requests`, `python-dotenv`, `itsdangerous`.

## 2. Features completed

**Phase 1 Auth [CONFIRMED, live]:** signup, login, POST-only logout, email verification (signed single-use tokens), password reset, CSRF, ownership checks, secure cookies, rate limiting, fail-safe `SECRET_KEY`, formula-injection sanitising, UUID filenames. Files expire after `FILE_TTL_HOURS = 2` through lazy cleanup (`safe_cleanup()` in `upload()` and `login()`), plus a "delete my file now" button. Cloudflare R2 storage is deferred to the very end of the project.

**Phase 2B usage tracking [CONFIRMED]:** `plans.py` (free: 3 files/month, 5 MB, no Excel/PDF; student ₹199: 30 files, 16 MB, Excel + PDF + cleaning log; pro ₹999: 200 files, 16 MB, all). `usage_events` table (unique per user per file), `usage.py` with `files_used_this_month`, `has_counted`, `record_file_usage`.

**Phase 2C server-side gating [REPORTED]:** the user said "done commited" after the test list. Individual test results were not reported. Includes `limit_response()`, `inject_plan` context processor, upload/clean/Excel/PDF checks and `limit_reached.html`. The Upgrade button on that page POSTs to `/subscribe`.

**Phase 2D Razorpay checkout [CONFIRMED, local and Render]:** `billing.py` has `create_subscription(user)`, which calls `POST https://api.razorpay.com/v1/subscriptions` with plan `RAZORPAY_PLAN_STUDENT`, `total_count 60`, and `notes {user_id, email}`, and returns the hosted checkout `short_url`. `/subscribe` (POST, login + verified required, 5 per hour) redirects there. Errors are logged by `billing.py` (it currently logs safe diagnostics: key prefix, length, last 4 characters of the Key ID, whitespace flags, never the secret).

**Phase 2E webhook [CONFIRMED by the user's checks, "all okay"]:** `POST /razorpay/webhook` is CSRF-exempt and limiter-exempt, and checks an HMAC-SHA256 signature using `RAZORPAY_WEBHOOK_SECRET` (a value the user invented, entered in both Render and the Razorpay webhook form). It skips duplicates through the `webhook_events` table (`event_id` unique). `subscription.activated` and `.charged` set `plan_tier="student"` and store `razorpay_subscription_id`. `.cancelled`, `.halted` and `.completed` set it to `"free"` immediately (a known simplification, to be improved in 2F). The user paid with a test card on the live site, and the plan upgraded.

**Home page plan line [CONFIRMED]:** shows "<Plan> plan · X of Y files used this month". The user finds it easy to miss, so a prominent plan/usage display is a Phase 5 item.

**Account state:** the Razorpay account's website was **approved** and live mode is available. Development is still in **Test Mode** (see constraints). The user's test account is currently on the Student plan in Neon.

## 3. Key files, routes, modules

- **Python:** `app.py` (routes), `models.py` (`User` with `plan_tier` and `razorpay_subscription_id`, `UploadedFile`, `UsageEvent`, `WebhookEvent`), `extensions.py` (`db`, `csrf`, `limiter`), `plans.py`, `usage.py`, `billing.py`, `tokens.py`, `mailer.py`, `utils.py` and `outlier_engine.py` (9 cleaning engines), `create_tables.py` (one-off `db.create_all()`), `test_usage.py` and `check_razorpay.py` (temporary helpers, safe but can be deleted or ignored).
- **Routes:** `/`, `/upload`, `/clean` (POST), `/download` (POST), `/download/excel`, `/download/csv`, `/report`, `/delete-file` (POST), `/signup`, `/login`, `/logout` (POST), `/verify/<token>`, `/resend-verification`, `/forgot-password`, `/reset-password/<token>`, `/subscribe` (POST), `/razorpay/webhook` (POST).
- **Templates:** `index.html`, `tool.html`, `result.html`, `_nav.html`, `auth_base.html`, `login.html`, `signup.html`, `forgot_password.html`, `reset_password.html`, `limit_reached.html`.
- **Env var names (never paste values):** `SECRET_KEY`, `DATABASE_URL`, Brevo key/sender, `APP_BASE_URL`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_PLAN_STUDENT`, `RAZORPAY_WEBHOOK_SECRET`.
- **Neon tables:** `users`, `uploaded_files`, `usage_events`, `webhook_events`.

## 4. Bugs

**Fixed [CONFIRMED]:** nav overlap; `/clean` 405 (now POST); mailer ImportError; `url_for` import; BuildError (endpoint is `home`); SQLAlchemy DLL block (pinned `<2.1`); duplicate signup flash; unverified access; auto-expiry never ran; Razorpay **401 "Authentication failed"** was caused by a stale or mismatched key/secret pair. A fresh pair generated once in Test Mode fixed both local and Render. Lesson: after rotating keys, update both `.env` and Render, and compare the Key ID's last 4 characters.

**Fix given, not confirmed applied [INSTRUCTED]:** Neon idle disconnect ("SSL connection has been closed unexpectedly" in `load_user`). The fix is `app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True, "pool_recycle": 280}` in `app.py` before `db.init_app(app)`. Check that it exists and is deployed.

**Open:**
- `UploadedFile.created_at` default may be local time, not UTC. [VERIFY in `models.py`]
- `result.html`: HTML comment inside `<style>` (about line 673) and `var(--card)` should be `var(--bg-card)`.
- `index.html`: "5 Cleaning Engines" should say 9; duplicate "Fast" in the footer; the `fileInput` script should be wrapped in `if (input)`.
- UPI never appeared on checkout for subscriptions earlier. The user said UPI opens only on the deployed site, and whether UPI AutoPay works there is **not confirmed**. Revisit in 2G.
- Confirm `format="mixed"` in `to_datetime_safe` and `outlier_engine.py`. Unresolved checklist items SC3, M5, C9, C15, C19. `tool.html` flash rendering, favicon 404, limiter in-memory storage, `FILE_TTL_HOURS` vs UI text (currently 2).

## 5. Decisions

- Follow the user's Master Specification phase order (Phase 4 = row/cell flagging, Phase 5 = UI/UX overhaul).
- Plan changes come **only** from the webhook; gating is server-side only.
- Razorpay is the provider, used via REST. Provider can be swapped by rewriting `billing.py` and the webhook.
- Student ₹199. Pro stays hidden until the AI features exist.
- **Pending (asked, not answered):** (1) on cancel, keep access until the end of the paid month (my recommendation; the webhook currently downgrades immediately); (2) refund policy. I suggested 7 days, but the user asked whether it's mandatory. My answer: no specific period is mandated that I know of, but a clearly stated refund and cancellation policy is required (Razorpay expects the page, and Indian e-commerce rules require disclosure). "No refunds, cancel any time" is allowed if stated clearly. I am not a lawyer, so verify with Razorpay's requirements and Indian consumer law.
- R2 storage last. Google sign-in later.

## 6. Status

- **Deployed on Render:** through Phase 2E, I believe. [VERIFY that the latest push includes the Neon idle fix]
- **Last commit I saw:** `7cb2c58 Phase 2B`. After that the user reported committing 2C and later changes. Hashes and messages are unknown. [VERIFY with `git log --oneline -5`]
- **Not started:** 2F billing page, 2G go-live, Phases 3–7, pre-launch QA.

## 7. Next steps, in priority order

1. Confirm `git status` is clean and pushed, and the Neon idle fix is in.
2. **2F billing page:** `/billing` showing plan, price, status and renewal date; a Cancel button (Razorpay cancel-at-cycle-end); keep paid access until the period ends (needs a `plan_renews_at` column via `ALTER TABLE users ADD COLUMN ...` in Neon, and a webhook change so `.cancelled` doesn't downgrade immediately); a Billing nav link; a confirmation after checkout.
3. **2G go-live:** terms, privacy and refund/cancellation pages; live key pair, live plan and live webhook (own secret), all set **only in Render**, never in local `.env`; UPI AutoPay check; a small live payment test.
4. **Phase 3** infra: gunicorn workers, background queue, file/row caps, structured logging, Sentry, UptimeRobot, Flask-Talisman, cleanup job, shared limiter storage.
5. **Phase 4** flagging model: issue records `{row, column, category, severity, message, suggested_fix}`, sort/filter by error type, per-column suggestions, two-colour cell marking, an Issues column, the 10-category problem list.
6. **Phase 5** UI/UX overhaul, including prominent plan and usage display.
7. **Phase 6** AI profile summary via the Claude API. **Phase 7** retention features. Pre-launch QA. R2 last.

## 8. Instructions for the next AI assistant

- The user is a beginner. One small step at a time, exact find/replace snippets, PowerShell commands.
- Follow the user's spec phases and don't reorder them.
- Never ask for or echo secrets. A Razorpay Key ID is public, but the Key Secret, webhook secret, DB URL and Brevo key are not.
- **Stay in Razorpay Test Mode** until 2G. Live keys charge real money. Test cards: Mastercard `5267 3181 8797 5449`, Visa `4718 6091 0820 4366`, any future expiry, any CVV, OTP `1234`. UPI test: `success@razorpay`.
- Don't claim something works unless the user confirmed it. Ask for the real files when unsure.
- Security first: CSRF, ownership checks, server-side gating, webhook signature verification.
- Per-phase commit messages.
- Keep costs low: the user has no budget, and Brevo's free tier is 300 emails/day.

## 9. What I can't recover reliably

- Current contents of the user's local files. Ask for `app.py`, `models.py`, `billing.py`, `plans.py` and the templates before editing.
- Which exact edits and commits exist, and the individual 2C test results.
- The full Master Specification and checklist wording (re-attach the spec file).
- Whether the Neon idle fix is deployed, and whether UPI works for subscriptions on the live site.
- The earlier transcript: `/root/.claude/projects/-home-claude/46a00415-0931-5206-9f94-fe25dfc1f280.jsonl` (cloud workspace, may be gone).