import time
from functools import wraps
from flask import Flask,redirect, render_template, request, send_file,flash,url_for,session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from utils import (
    safe_upload_filename,
    is_allowed_extension,
    sanitize_dataframe_for_excel,
    dedupe_columns,
)
import traceback
from datetime import datetime, timedelta, timezone
from tokens import generate_token, confirm_token
from mailer import send_verification_email, send_reset_email
from exports.report import generate_pdf_report
from exports.excel_report import generate_excel_report
import csv 
import openpyxl
from engines.profiling_engine import profiling_engine
from engines.missing_engine import missing_engine
from engines.outlier_engine import outlier_engine
from engines.formatting_engine import formatting_engine
from engines.quality_engine import quality_engine
from engines.recommendation_engine import recommendation_engine
from engines.schema_engine import schema_engine
from engines.duplicate_engine import duplicate_engine
from engines.data_type_engine import data_type_engine
import pandas as pd
import os
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
load_dotenv()
from flask_wtf.csrf import CSRFError


app = Flask(__name__)
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
IS_PRODUCTION = os.environ.get("RENDER") == "true"   # Render sets RENDER=true automatically

_secret = os.environ.get("SECRET_KEY")
if not _secret:
    if IS_PRODUCTION:
        raise RuntimeError("SECRET_KEY environment variable must be set in production")
    _secret = "dev-only-insecure-key-change-me"      # local development only
app.secret_key = _secret
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024   # 16MB

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,       # JavaScript can't read the cookie
    SESSION_COOKIE_SAMESITE="Lax",      # not sent on cross-site POSTs
    SESSION_COOKIE_SECURE=IS_PRODUCTION,  # HTTPS only on Render, still works on http://127.0.0.1
    REMEMBER_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_SAMESITE="Lax",
    REMEMBER_COOKIE_SECURE=IS_PRODUCTION,
)

db_url = os.environ.get("DATABASE_URL", "")
db_url = db_url.replace("postgres://", "postgresql://", 1)
db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

from extensions import db,csrf, limiter


app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
csrf.init_app(app)
limiter.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # redirects here if a @login_required route is hit while logged out
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "warning"

from models import User, UploadedFile  # noqa: E402

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

UPLOAD_FOLDER = "uploads"
CLEANED_FOLDER = "cleaned"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CLEANED_FOLDER, exist_ok=True)
def get_owned_file_or_404(stored_filename):
    """
    Looks up a file record and confirms the CURRENT logged-in user owns it.
    Returns the UploadedFile record if valid, or None if not found / not owned.
    Every route that touches a specific file must call this before doing anything else.
    """
    record = UploadedFile.query.filter_by(stored_filename=stored_filename).first()
    if not record:
        return None
    if record.user_id != current_user.id:
        return None
    return record

FILE_TTL_HOURS = 2


def _delete_file_artifacts(stored_filename):
    """Delete the upload and every generated output (cleaned csv, xlsx, pdf) for one file."""
    stem = stored_filename.rsplit(".", 1)[0]
    if len(stem) < 16:          # safety: never match short/empty names
        return
    for folder in (UPLOAD_FOLDER, CLEANED_FOLDER):
        for name in os.listdir(folder):
            if stem in name:
                try:
                    os.remove(os.path.join(folder, name))
                except OSError:
                    pass


def cleanup_expired_files():
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=FILE_TTL_HOURS)
    expired = UploadedFile.query.filter(UploadedFile.created_at < cutoff).all()
    for record in expired:
        _delete_file_artifacts(record.stored_filename)
        db.session.delete(record)
    if expired:
        db.session.commit()


def safe_cleanup():
    """Never let cleanup problems break a user's request."""
    try:
        cleanup_expired_files()
    except Exception:
        db.session.rollback()
        print(traceback.format_exc())


def send_verification_for(user):
    base = os.environ.get("APP_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
    link = f"{base}/verify/{generate_token(user.email)}"
    return send_verification_email(user.email, link)

def verified_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.email_verified:
            flash("Please verify your email to use this feature. Check your inbox, or resend the email using the banner at the top.", "warning")
            return redirect("/")
        return f(*args, **kwargs)
    return wrapper

def _user_from_reset_token(token):
    data = confirm_token(token, salt="password-reset", max_age=3600)
    if not isinstance(data, dict):
        return None
    user = User.query.filter_by(email=data.get("e")).first()
    if not user or user.password_hash[-12:] != data.get("h"):
        return None
    return user


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
@login_required
@verified_required
def upload():
    try:
        safe_cleanup()
        file = request.files["file"]
        if not file or file.filename == "":
            flash("No file selected.", "danger")
            return redirect("/")
        if not is_allowed_extension(file.filename):
            flash("Only CSV and Excel files are allowed.", "danger")
            return redirect("/")
        stored_filename, ext = safe_upload_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, stored_filename)
        file.save(file_path)
        new_file_record = UploadedFile(
            user_id=current_user.id,
            stored_filename=stored_filename,
            original_filename=file.filename,
        )
        db.session.add(new_file_record)
        db.session.commit()
        if os.path.getsize(file_path) == 0:
            flash("Uploaded file is empty.", "danger")
            return redirect("/")
        # read based on file type
        
        if ext == "csv":
            # Detect the working encoding once, reuse it for both the header
            # check and the actual read — fixes the utf-8-only crash (C4)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    raw_headers = next(reader)
                csv_encoding = "utf-8"
            except UnicodeDecodeError:
                with open(file_path, "r", encoding="latin1") as f:
                    reader = csv.reader(f)
                    raw_headers = next(reader)
                csv_encoding = "latin1"
            except StopIteration:
                flash("Uploaded file appears to be empty or invalid.", "danger")
                return redirect("/")

            if len(raw_headers) != len(set(raw_headers)):
                duplicates = [x for x in raw_headers if raw_headers.count(x) > 1]
                flash(f"Duplicate column names found: {', '.join(set(duplicates))}", "danger")
                return redirect("/")

            df = pd.read_csv(file_path, encoding=csv_encoding)

        else:
            df = pd.read_excel(file_path)
        df = dedupe_columns(df)
        # now check empty dataframe
        if df.empty:
            flash("Dataset has no rows to process.", "danger")
            return redirect("/")

        # now check all-null columns
        all_null_cols = df.columns[df.isnull().all()].tolist()

        if all_null_cols:
            df=df.drop(columns=all_null_cols)
            flash(f"Warning: all-null columns found: {', '.join(all_null_cols)}", "warning")
            
        recommendations = recommendation_engine(df)
        # -------- dataset stats ----------
        total_rows = len(df)
        total_cols = len(df.columns)
        missing_count = df.isnull().sum().sum()
        duplicate_count = df.duplicated().sum()
        numeric_cols = len(df.select_dtypes(include='number').columns)
        quality_score = quality_engine(df)
        tables = df.head(100).to_html(classes="table", index=False)
        # basic issues before cleaning
        issue_count = 0
        if missing_count > 0:
            issue_count += 1
        if duplicate_count > 0:
            issue_count += 1
        remaining_issues = len(recommendations)
        return render_template(
            "tool.html",
            filename=stored_filename,
            tables=tables,
            columns=df.columns,

            total_rows=total_rows,
            total_cols=total_cols,
            missing_count=missing_count,
            duplicate_count=duplicate_count,
            numeric_cols=numeric_cols,
            quality_score=quality_score,
            issue_count=issue_count,
            remaining_issues=remaining_issues,
            recommendations=recommendations
        )
    except Exception as e:
        print(traceback.format_exc())
        flash(f"Upload failed: {str(e)}", "danger")
        return redirect("/")
# ---------------------------
# CLEAN ENGINE
# ---------------------------
@app.route("/clean", methods=["POST"])
@login_required
@verified_required
def clean():
    try:
        filename = request.form["filename"]

        owned = get_owned_file_or_404(filename)
        if not owned:
            flash("File not found or access denied.", "danger")
            return redirect("/")

        file_path = os.path.join(UPLOAD_FOLDER, filename)
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if ext == "csv":
            try:
                df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip")
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding="latin1", on_bad_lines="skip")
        else:
            df = pd.read_excel(file_path)
        df = dedupe_columns(df)
        df=df.dropna(how="all")
        df=df.loc[:,~df.columns.str.contains("^unnamed")]
        #save the original data
        original_df = df.copy()
        changes = []
        # Drop all-null columns — mirrors /upload's logic (fixes C3)
        all_null_cols = df.columns[df.isnull().all()].tolist()
        if all_null_cols:
            df = df.drop(columns=all_null_cols)
            changes.append(f"Dropped all-null columns: {', '.join(all_null_cols)}")


        # ---------------- SCHEMA ENGINE ----------------
        df, changes = schema_engine(df, request, changes)
        # ---------------- formatting DATA ----------------
        df, changes = formatting_engine(df, request, changes)
        #----------------- data type engine --------------
        df, changes = data_type_engine(df, request, changes)
        # ---------------- MISSING DATA ----------------
        df, changes, missing_report = missing_engine(df, request, changes)
        #----------------- Outlier DATA ------------------
        df,changes = outlier_engine(df, request, changes)
        # ---------------- Duplicate DATA ----------------
        df, changes = duplicate_engine(df, request, changes)
        # ---------------- SAVE CLEANED ----------------
        cleaned_path = os.path.join(CLEANED_FOLDER, "cleaned_" + filename)
        df.to_csv(cleaned_path, index=False)
        
        profile = profiling_engine(df)
        quality_score = quality_engine(df)
        recommendations = recommendation_engine(df)
        # Quality color logic
        if quality_score >= 80:
            quality_color = "var(--success)"
            quality_grade = "Excellent — dataset is clean"
        elif quality_score >= 50:
            quality_color = "var(--warn)"
            quality_grade = "Fair — some issues remain"
        else:
            quality_color = "var(--danger)"
            quality_grade = "Poor — significant cleaning needed"
        # SVG stroke color (ring)
        if quality_score >= 80:
            quality_stroke = "#2d6a11"
        elif quality_score >= 50:
            quality_stroke = "#854f0b"
        else:
            quality_stroke = "#a32d2d"

        return render_template(
            "result.html",
            original_table=original_df.head(100).to_html(index=False),
            cleaned_table=df.head(100).to_html(index=False),
            changes=changes,
            filename=filename,
            missing_report=missing_report,
            profile=profile,
            quality_score=quality_score,
            recommendations=recommendations,
            quality_color=quality_color,
            quality_grade=quality_grade,
            quality_stroke=quality_stroke,
        )
    except Exception as e:
        print(traceback.format_exc())
        flash(f"Cleaning failed: {str(e)}", "danger")
        return redirect("/")


# ---------------------------
# DOWNLOAD
# ---------------------------
@app.route("/download", methods=["POST"])
@login_required
def download():
    try:
        filename = request.form["filename"]

        owned = get_owned_file_or_404(filename)
        if not owned:
            flash("File not found or access denied.", "danger")
            return redirect("/")

        cleaned_path = os.path.join(CLEANED_FOLDER, "cleaned_" + filename)
        return send_file(cleaned_path, as_attachment=True)
    except Exception as e:
        print(traceback.format_exc())
        flash("Download failed.", "danger")
        return redirect("/")
@app.route("/download/excel", methods=["GET"])
@login_required
def download_excel():
    try:
        filename = request.args.get("filename")

        owned = get_owned_file_or_404(filename)
        if not owned:
            flash("File not found or access denied.", "danger")
            return redirect("/")

        cleaned_path = os.path.join(CLEANED_FOLDER, "cleaned_" + filename)

        if not os.path.exists(cleaned_path):
            flash("Cleaned file not found.", "danger")
            return redirect("/")

        df = pd.read_csv(cleaned_path)

        missing_report = []
        for col in df.columns:
            count = df[col].isnull().sum()
            if count > 0:
                pct = round((count / len(df)) * 100, 2)
                missing_report.append([col, count, pct])

        profile = profiling_engine(df)
        recommendations = recommendation_engine(df)
        quality_score = quality_engine(df)

        excel_path = generate_excel_report(
            filename,
            CLEANED_FOLDER,
            df,
            missing_report,
            profile,
            recommendations,
            quality_score
        )

        if not excel_path:
            flash("Excel generation failed.", "danger")
            return redirect("/")

        return send_file(excel_path, as_attachment=True)

    except Exception:
        print(traceback.format_exc())
        flash("Excel generation failed.", "danger")
        return redirect("/")
@app.route("/download/csv")
@login_required
def download_csv():
    try:
        filename = request.args.get("filename")

        owned = get_owned_file_or_404(filename)
        if not owned:
            flash("File not found or access denied.", "danger")
            return redirect("/")

        path = os.path.join(CLEANED_FOLDER, "cleaned_" + filename)
        return send_file(path, as_attachment=True)
    except:
        flash("CSV file not found.", "danger")
        return redirect("/")
@app.route("/report")
@login_required
def report():
    try:
        filename = request.args.get("filename")

        owned = get_owned_file_or_404(filename)
        if not owned:
            flash("File not found or access denied.", "danger")
            return redirect("/")

        pdf_path = generate_pdf_report(
            filename,
            CLEANED_FOLDER,
            quality_engine,
            recommendation_engine
        )

        return send_file(pdf_path,
                         as_attachment=True)

    except:
        print(traceback.format_exc())
        flash("PDF generation failed.", "danger")
        return redirect("/")

@app.route("/delete-file", methods=["POST"])
@login_required
def delete_file():
    filename = request.form.get("filename", "")
    record = get_owned_file_or_404(filename)
    if not record:
        flash("File not found or already deleted.", "warning")
        return redirect("/")
    _delete_file_artifacts(record.stored_filename)
    db.session.delete(record)
    db.session.commit()
    flash("Your file has been permanently deleted.", "success")
    return redirect("/")


@app.errorhandler(413)
def too_large(e):
    flash("File too large. Max allowed size is 16MB.", "danger")
    return redirect("/")
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    flash("Your session expired. Please try again.", "warning")
    return redirect("/")
@app.route("/signup", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not email or not password:
            flash("Email and password are required.", "danger")
            return redirect("/signup")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect("/signup")

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return redirect("/signup")

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with this email already exists.", "danger")
            return redirect("/signup")

        new_user = User(email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        if send_verification_for(new_user):
            flash("Account created. Check your email to verify your address.", "success")
        else:
            flash("Account created, but we couldn't send the verification email. You can resend it later.", "warning")
        safe_cleanup()
        login_user(new_user)
        session["last_verification_sent"] = time.time()
        return redirect("/")

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return redirect("/login")

        login_user(user)
        flash("Logged in successfully.", "success")
        return redirect("/")

    return render_template("login.html")

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect("/")

@app.route("/verify/<token>")
def verify_email(token):
    email = confirm_token(token)
    if not email:
        flash("This verification link is invalid or has expired.", "danger")
        return redirect("/")

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("This verification link is invalid or has expired.", "danger")
        return redirect("/")

    if user.email_verified:
        flash("Your email is already verified.", "info")
    else:
        user.email_verified = True
        db.session.commit()
        flash("Email verified. You're all set!", "success")
    return redirect("/")

@app.route("/resend-verification", methods=["POST"])
@login_required
@limiter.limit("5 per hour")
def resend_verification():
    if current_user.email_verified:
        flash("Your email is already verified.", "info")
        return redirect("/")

    wait = 60 - (time.time() - session.get("last_verification_sent", 0))
    if wait > 0:
        flash(f"Please wait {int(wait) + 1} seconds before requesting another email.", "warning")
        return redirect("/")

    if send_verification_for(current_user):
        session["last_verification_sent"] = time.time()
        flash("Verification email sent. Check your inbox.", "success")
    else:
        flash("We couldn't send the email. Please try again later.", "danger")
    return redirect("/")

@app.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        wait = 60 - (time.time() - session.get("last_reset_sent", 0))
        if wait > 0:
            flash(f"Please wait {int(wait) + 1} seconds before trying again.", "warning")
            return redirect("/forgot-password")
        session["last_reset_sent"] = time.time()

        user = User.query.filter_by(email=email).first()
        if user:
            base = os.environ.get("APP_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
            token = generate_token(
                {"e": user.email, "h": user.password_hash[-12:]},
                salt="password-reset",
            )
            send_reset_email(user.email, f"{base}/reset-password/{token}")

        flash("If an account exists for that email, we've sent a password reset link.", "info")
        return redirect("/login")

    return render_template("forgot_password.html")


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = _user_from_reset_token(token)
    if not user:
        flash("This reset link is invalid or has expired. Please request a new one.", "danger")
        return redirect("/forgot-password")

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return redirect(request.path)
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(request.path)

        user.set_password(password)
        db.session.commit()
        flash("Password updated. Please log in with your new password.", "success")
        return redirect("/login")

    return render_template("reset_password.html", token=token)

@app.errorhandler(429)
def too_many_requests(e):
    flash("Too many attempts. Please wait a few minutes and try again.", "warning")
    return redirect("/login")


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode)