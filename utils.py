import uuid
import pandas as pd
from werkzeug.utils import secure_filename


# ==================================================
# EMAIL / PHONE — single source of truth (fixes C15 partially, referenced later)
# ==================================================
EMAIL_REGEX = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
PHONE_DIGIT_LENGTH = 10

PLACEHOLDER_MISSING_VALUES = {
    "", " ", "na", "n/a", "null", "none", "-", "unknown", "nan"
}
ALLOWED_UPLOAD_EXTENSIONS = {"csv", "xlsx", "xls"}
def build_column_map(df):
    """Map lowercase column name -> real column name."""
    return {col.lower(): col for col in df.columns}

def resolve_column(column_map, name):
    """Safely look up a real column name from user input."""
    if not name:
        return None
    return column_map.get(name.strip().lower())


def parse_col_list(raw):
    """Split a comma-separated form field into clean column name strings."""
    if not raw:
        return []
    return [c.strip() for c in raw.split(",") if c.strip()]


# ==================================================
# SAFE TYPE COERCION (fixes C1, C6)
# ==================================================
def to_str_safe(series):
    """
    Convert a Series to string WITHOUT turning real NaN into the text "nan".
    Use this instead of series.astype(str) everywhere.
    """
    return series.where(series.notna(), None).astype("string")


def to_numeric_safe(series):
    return pd.to_numeric(series, errors="coerce")


def to_datetime_safe(series, dayfirst=True):
    """
    dayfirst=True by default — assumes DD/MM/YYYY (India-style) input.
    format="mixed" parses each value independently instead of guessing one
    shared format for the whole column — without it, a column containing
    both DD/MM/YYYY and YYYY/MM/DD entries can silently mark genuinely valid
    dates as invalid, because pandas locks onto one format for the batch.
    """
    return pd.to_datetime(series, errors="coerce", dayfirst=dayfirst, format="mixed")


def normalize_missing_placeholders(series):
    """Treat common placeholder strings as real missing values (fixes C8)."""
    is_placeholder = (
        series.astype(str).str.strip().str.lower().isin(PLACEHOLDER_MISSING_VALUES)
    )
    return series.mask(is_placeholder | series.isna(), None)


# ==================================================
# SAFE FORM PARSING (fixes C5)
# ==================================================
def safe_float(value, default=None):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_date(value, default=None):
    try:
        if not value:
            return default
        parsed = pd.to_datetime(value, errors="coerce")
        return default if pd.isna(parsed) else parsed
    except Exception:
        return default


# ==================================================
# EXCEL FORMULA INJECTION GUARD (fixes S6)
# ==================================================
DANGEROUS_LEAD_CHARS = ("=", "+", "-", "@")

def sanitize_cell(value):
    """Prefix values that look like formulas so Excel treats them as text."""
    if isinstance(value, str) and value and value[0] in DANGEROUS_LEAD_CHARS:
        return "'" + value
    return value


def sanitize_dataframe_for_excel(df):
    """Apply sanitize_cell to every text column before writing to .xlsx."""
    safe_df = df.copy()
    for col in safe_df.select_dtypes(include="object").columns:
        safe_df[col] = safe_df[col].apply(sanitize_cell)
    return safe_df


# ==================================================
# SAFE FILE HANDLING (fixes S1, S3)
# ==================================================
def safe_upload_filename(original_filename):
    """
    Generates a collision-proof, traversal-proof filename for storage.
    Returns (stored_filename, extension).
    IMPORTANT: keep the ORIGINAL filename only for display — never use it
    to build a filesystem path.
    """
    original_filename = original_filename or "upload"
    cleaned = secure_filename(original_filename)
    ext = cleaned.rsplit(".", 1)[-1].lower() if "." in cleaned else ""
    unique_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    return unique_name, ext


def is_allowed_extension(filename):
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext in ALLOWED_UPLOAD_EXTENSIONS
def dedupe_columns(df):
    """Rename duplicate column headers to name, name_2, name_3... so
    df[col] never accidentally returns a DataFrame instead of a Series."""
    seen = {}
    new_cols = []
    for col in df.columns:
        if col not in seen:
            seen[col] = 1
            new_cols.append(col)
        else:
            seen[col] += 1
            new_cols.append(f"{col}_{seen[col]}")
    df = df.copy()
    df.columns = new_cols
    return df