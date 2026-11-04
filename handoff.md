# CleanSight Handoff (handoff.md), updated 2026-11-02 (end of day)

Markers: **[CONFIRMED]** = the user reported it working, or I saw the output. **[REPORTED]** = the user said it was done, with no detail. **[INSTRUCTED]** = I gave instructions but the user hasn't confirmed. **[VERIFY]** = unknown, check the real files.

This replaces all earlier handoffs. Phase 2 (payments) is now functionally complete in Test Mode. Phase 3 starts next.

---

## 1. Project overview

- **Purpose:** CleanSight is a data-cleaning web app. Users upload CSV/XLSX, run 9 cleaning engines, then download results (CSV, highlighted Excel, PDF quality report).
- **Version:** building **v2** from a working v1.
- **Goal:** a production SaaS. Student plan ₹199/month now, Pro ₹999/month later (hidden until AI features exist).
- **Audience now:** college students and researchers (datasets of about 600–700 rows). AI bot and analytics come later for professional clients.
- **User:** beginner, Windows/PowerShell, VS Code. **New laptop since 2026-11-02:** path `C:\Users\praav\Documents\Projects\CleanSight`, venv `.venv`. Old path (`...\OneDrive\Documents\My Projects\CleanSight`, `venv`) is obsolete. Git identity was set on the new laptop with `git config --global user.name/user.email` (the user's GitHub account).
- **Live URL:** https://cleansight-zajg.onrender.com
- **Stack:** Flask 3.1.3, Pandas 3.0.2, OpenPyXL, Python 3.14, gunicorn (`Procfile`: `web: gunicorn app:app`), Jinja HTML/CSS/JS. Neon Postgres (`postgresql+psycopg://`), shared by local `.env` and Render. Render free tier. Brevo email (HTTP API). Razorpay (REST via `requests`).
- **Dependencies:** Flask-SQLAlchemy 3.1.1 with `sqlalchemy<2.1` pinned, Flask-Login 0.6.3, Flask-WTF 1.2.2 (CSRF), Flask-Limiter (in-memory), `psycopg[binary]==3.2.10`, `requests`, `python-dotenv`, `itsdangerous`.

## 2. Features completed

**Phase 1 Auth [CONFIRMED, live]:** signup, login, POST-only logout, email verification and password reset (signed single-use tokens, separate salts), CSRF, ownership checks, secure cookies, rate limiting, fail-safe `SECRET_KEY`, formula-injection sanitising, UUID filenames. Files expire after `FILE_TTL_HOURS = 2` through lazy cleanup (`safe_cleanup()` in `upload()` and `login()`), plus a "delete my file now" button. **Cloudflare R2 per-user storage is deferred to the very end of the project** (see section 5).

**Phase 2 Payments and usage limits [CONFIRMED, Test Mode]:**
- `plans.py`: free (3 files/month, 5 MB, no Excel/PDF), student ₹199 (30 files, 16 MB, Excel + PDF + cleaning log flag), pro ₹999 (200 files, 16 MB). `effective_tier(user)` drops a cancelled plan to free once `plan_renews_at` has passed. `plan_for_user(user)` uses it.
- `usage_events` table and `usage.py` count unique files cleaned per user per UTC month.
- Server-side gating (2C): file count, file size, Excel and PDF; `limit_reached.html`. The user ran the test list and committed.
- Razorpay checkout (2D/2F): `billing.py` has `create_subscription(user)` (REST `POST /v1/subscriptions`, plan `RAZORPAY_PLAN_STUDENT`, `total_count 60`, notes carry `user_id`) and `cancel_subscription(sub_id)` (cancel at cycle end). `/subscribe` (POST, verified required, 5 per hour) renders `checkout.html`, which opens Razorpay's checkout window on our own page (`checkout.js`); success goes to `/billing/processing` (`processing.html`, polls `/billing/status` until the webhook has upgraded the plan, then goes to `/billing`).
- Webhook (2E): `POST /razorpay/webhook`, CSRF-exempt, signature-checked with `RAZORPAY_WEBHOOK_SECRET`, duplicates skipped through `webhook_events`. `subscription.activated`/`.charged` set `plan_tier="student"`, store the subscription id and `plan_renews_at` (from `current_end`, falling back to `charge_at`), and clear `cancel_requested`. `.cancelled` keeps access until `plan_renews_at` (sets `cancel_requested`), `.halted`/`.completed` set free.
- Billing page (2F): `/billing` shows plan, renewal date, and a Cancel button (`POST /billing/cancel`, 5 per hour). A Billing link is in `_nav.html`.
- **Verified by the user on the live site:** payment with test card AND UPI AutoPay (mandate created, next charge scheduled), redirect after payment, plan upgrade, `plan_renews_at` stored (UTC, naive), Excel/PDF unlocked, cancel flow, nav link styling. Both Render and localhost work (they share one Neon DB, and Razorpay's webhook goes to Render).
- **Account state:** the Razorpay account's website was **approved**, and live mode is available. Development stays in **Test Mode**.

## 3. Key files, routes, modules

- **Python:** `app.py` (routes), `models.py` (`User` with `plan_tier`, `razorpay_subscription_id`, `plan_renews_at`, `cancel_requested`; `UploadedFile`; `UsageEvent`; `WebhookEvent`), `extensions.py` (`db`, `csrf`, `limiter`), `plans.py`, `usage.py`, `billing.py`, `tokens.py`, `mailer.py`, `utils.py` and `outlier_engine.py` (cleaning engines), `create_tables.py` (one-off `db.create_all()`), `test_usage.py` and `check_razorpay.py` (temporary helpers, can be deleted).
- **Routes:** `/`, `/upload`, `/clean` (POST), `/download` (POST), `/download/excel`, `/download/csv`, `/report`, `/delete-file` (POST), `/signup`, `/login`, `/logout` (POST), `/verify/<token>`, `/resend-verification`, `/forgot-password`, `/reset-password/<token>`, `/subscribe` (POST), `/billing`, `/billing/cancel` (POST), `/billing/processing`, `/billing/status`, `/razorpay/webhook` (POST).
- **Templates:** `index.html`, `tool.html`, `result.html`, `_nav.html`, `auth_base.html`, `login.html`, `signup.html`, `forgot_password.html`, `reset_password.html`, `limit_reached.html`, `billing.html`, `checkout.html`, `processing.html`.
- **Env var names (never paste values):** `SECRET_KEY`, `DATABASE_URL`, Brevo key/sender, `APP_BASE_URL`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_PLAN_STUDENT`, `RAZORPAY_WEBHOOK_SECRET`. `.env` is not in git; a new machine needs its own copy.
- **Neon tables:** `users`, `uploaded_files`, `usage_events`, `webhook_events`.
- **Last commits I know of:** `b2ba017 Phase 2F: renewal date, cancel-aware plan expiry, webhook logging`, then the user reported pushing "Phase 2F: in-site checkout and redirect" and "Phase 2F: billing page, cancel, in-site checkout". [VERIFY with `git log --oneline -5`]

## 4. Bugs

**Fixed [CONFIRMED]:** nav overlap; `/clean` 405 (now POST); mailer ImportError; `url_for` import; BuildError (endpoint is `home`); SQLAlchemy DLL block (pinned `<2.1`); duplicate signup flash; unverified access; auto-expiry never ran; the Razorpay **401 "Authentication failed"** was a stale or mismatched key pair on Render. Lesson: after rotating keys, update both `.env` and Render, and compare the Key ID's last 4 characters. A Razorpay test card is declined for subscriptions unless it is recurring-eligible. The 2E duplicate-log line never showed under gunicorn (Flask's `app.logger.info` is hidden at the default WARNING level). The Billing nav link first looked like a plain link, and was fixed by giving it the same class as "New file".

**Open or unconfirmed:**
- Neon idle disconnect fix (`SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}` before `db.init_app(app)`). I gave it, and the user never said it was applied. [VERIFY in `app.py`]
- `UploadedFile.created_at` default may be local time, not UTC. [VERIFY in `models.py`]
- `result.html`: an HTML comment inside `<style>` (about line 673) and `var(--card)` should be `var(--bg-card)`.
- `index.html`: "5 Cleaning Engines" should say 9; duplicate "Fast" in the footer; the `fileInput` script should be wrapped in `if (input)`.
- Debug logging added to `billing.py` (key prefix, lengths, last 4 characters of the Key ID; no secrets) can be trimmed.
- Confirm `format="mixed"` in `to_datetime_safe` and `outlier_engine.py`. Unresolved checklist items SC3, M5, C9, C15, C19. `tool.html` flash rendering, favicon 404, limiter in-memory storage, `FILE_TTL_HOURS` vs UI text (currently 2).

## 5. Decisions

- Follow the user's Master Specification phase order (Phase 3 infra, Phase 4 row/cell flagging, Phase 5 UI/UX overhaul, Phase 6 AI, Phase 7 retention).
- Plan changes come **only** from the webhook; gating is server-side only. Razorpay is the provider, used via REST; swapping providers means rewriting `billing.py` and the webhook.
- Cancelling keeps access until the end of the paid period (chosen by me as default, the user did not object).
- **2G (go-live) is deferred by the user's choice until after other changes.** Stay in **Test Mode** until then. Needs from the user: business name as registered with Razorpay, a support email to publish (not the college address, since it ends at graduation), location, and a refund choice (7 days / 3 days / no refunds). A refund period is **not legally mandatory**, but a clearly stated refund/cancellation policy is (Razorpay and Indian e-commerce rules). I am not a lawyer. Live switch plan: live keys, live ₹199 plan, live webhook with its own secret, all **only in Render**; one real payment then cancel and refund.
- **Cloudflare R2 stays last.** It's per-user cloud file storage so files survive restarts and multi-instance setups. Revisit earlier only for lost-file complaints, multiple instances, or the Phase 7 history feature.
- Making the plan and usage line prominent is a Phase 5 item.
- Google sign-in later. Pro tier hidden until AI features exist.

## 6. Status

- **Deployed:** Phase 2 through 2F is live on Render in Test Mode. [CONFIRMED by the user's live tests]
- **Pending in Phase 2:** 2G go-live (deferred); the **cleaning-log export** (`cleaning_log_export` flag exists in `plans.py` but no feature behind it, so Student plan promises it without delivering); failed-payment handling (webhook only records `payment.failed`, nothing tells the user); optional CleanSight payment emails; GST/invoice question for the user and an accountant.
- **Not started:** Phases 3–7, pre-launch QA.
- The user's test account is on Student or was reset to Free (unknown). Reset SQL: `UPDATE users SET plan_tier='free', razorpay_subscription_id=NULL, plan_renews_at=NULL, cancel_requested=FALSE WHERE email='<test user>'; DELETE FROM webhook_events;`

## 7. Next steps, in priority order

1. **Tomorrow: start Phase 3.** The user will paste `app.py` (at least `upload()` and `clean()`) in a `.md` file. Order I proposed:
   1. **Row and column caps** server-side (for example 50,000 rows and a column cap), with clear messages.
   2. **Structured logging and Sentry.**
   3. **Health endpoint and UptimeRobot.**
   4. **Flask-Talisman**, with a policy allowing `checkout.razorpay.com` (scripts and frames).
   5. **Gunicorn workers and shared rate-limit storage.**
   6. **Background queue and scheduled cleanup job.**
   7. **Managed Postgres review** (Neon limits and backups).
2. Confirm or apply the Neon idle fix and the small clean-ups in section 4.
3. Decide: build the cleaning-log export before Phase 3, or move it to Phase 7.
4. Phase 4 flagging model: issue records `{row, column, category, severity, message, suggested_fix}`, sort/filter by error type, per-column suggestions, two-colour cell marking, an Issues column, the 10-category problem list.
5. Phase 5 UI/UX, Phase 6 AI profile summary via the Claude API, Phase 7 retention features.
6. **2G go-live** (when the user chooses), then pre-launch QA, then R2.

## 8. Instructions for the next AI assistant

- The user is a beginner. One small step at a time, exact find/replace snippets with context, PowerShell commands.
- Follow the user's spec phases and don't reorder them.
- Never ask for or echo secrets. A Razorpay Key ID is public, but the Key Secret, webhook secret, DB URL, Brevo key and `.env` contents are not. Tell the user to crop phone numbers and emails out of screenshots.
- **Stay in Razorpay Test Mode** until 2G. Test cards: Mastercard `5267 3181 8797 5449`, Visa `4718 6091 0820 4366`, any future expiry, any CVV, OTP `1234`. UPI test: `success@razorpay`.
- Don't claim something works unless the user confirmed it. Ask for the real files when unsure. I can't see the user's computer.
- Security first: CSRF, ownership checks, server-side gating, webhook signature verification.
- Per-phase commit messages. The user has no budget: free tiers only.

## 9. What I can't recover reliably

- Current contents of the user's local files. Ask for `app.py`, `models.py`, `billing.py`, `plans.py` and the templates before editing.
- The exact commit hashes after `b2ba017`, and whether `pool_pre_ping` is deployed.
- The full wording of the user's Master Specification and checklists (re-attach the spec file), and the text of SC3, M5, C9, C15, C19.
- Whether the user's test account is currently Student or Free.
- The earlier transcript: `/root/.claude/projects/-home-claude/46a00415-0931-5206-9f94-fe25dfc1f280.jsonl` (cloud workspace, may be gone).