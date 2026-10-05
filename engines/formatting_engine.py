import pandas as pd
from utils import build_column_map, resolve_column, parse_col_list, to_str_safe, to_datetime_safe, EMAIL_REGEX


def formatting_engine(df, request, changes):
    column_map = build_column_map(df)

    # LOWERCASE
    for col in parse_col_list(request.form.get("lower_cols", "")):
        real_col = resolve_column(column_map, col)
        if real_col:
            df[real_col] = to_str_safe(df[real_col]).str.lower()
            changes.append(f"{real_col}: converted to lowercase")

    # TRIM
    for col in parse_col_list(request.form.get("trim_cols", "")):
        real_col = resolve_column(column_map, col)
        if real_col:
            df[real_col] = to_str_safe(df[real_col]).str.strip()
            changes.append(f"{real_col}: trimmed spaces")

    # NUMERIC CLEANUP (fixes C11 — no longer strips loose k/g characters)
    for col in parse_col_list(request.form.get("numeric_clean_cols", "")):
        real_col = resolve_column(column_map, col)
        if real_col:
            cleaned = (
                to_str_safe(df[real_col])
                .str.replace(r"[₹$€]", "", regex=True)
                .str.replace(",", "", regex=False)
                .str.replace("%", "", regex=False)
                .str.replace(r"\s*(kg|g|cm|mm|km|lbs?)\b", "", regex=True)
                .str.strip()
            )
            df[real_col] = pd.to_numeric(cleaned, errors="coerce")
            changes.append(f"{real_col}: cleaned numeric formatting")

    # EMAIL CLEANUP
    for col in parse_col_list(request.form.get("email_cols", "")):
        real_col = resolve_column(column_map, col)
        if real_col:
            cleaned = to_str_safe(df[real_col]).str.strip().str.lower().str.replace(" ", "", regex=False)
            df[real_col] = cleaned
            invalid_mask = ~cleaned.str.match(EMAIL_REGEX, na=False)
            changes.append(f"{real_col}: cleaned email formatting, invalid emails found = {int(invalid_mask.sum())}")

    # PHONE NUMBER CLEANUP
    # Assumes 10-digit India-style mobile numbers — adjust PHONE_DIGIT_LENGTH
    # in utils.py if you expand internationally (documented per C10)
    for col in parse_col_list(request.form.get("phone_cols", "")):
        real_col = resolve_column(column_map, col)
        if real_col:
            digits_only = to_str_safe(df[real_col]).str.replace(r"\D", "", regex=True)
            df[real_col] = digits_only.apply(lambda x: x[-10:] if isinstance(x, str) and len(x) > 10 else x)
            invalid_count = int((df[real_col].str.len() != 10).sum())
            changes.append(f"{real_col}: standardized phone numbers, invalid numbers found = {invalid_count}")

    # DATE STANDARDIZATION (fixes C6 — dayfirst=True)
    for col in parse_col_list(request.form.get("date_cols", "")):
        real_col = resolve_column(column_map, col)
        if real_col:
            normalized = to_str_safe(df[real_col]).str.replace("/", "-", regex=False)
            parsed = to_datetime_safe(normalized, dayfirst=True)
            invalid_dates = int(parsed.isna().sum())
            df[real_col] = parsed.dt.strftime("%Y-%m-%d")
            changes.append(f"{real_col}: standardized date format, invalid dates found = {invalid_dates}")

    # BOOLEAN NORMALIZATION
    true_values = ["yes", "y", "true", "1", "active"]
    false_values = ["no", "n", "false", "0", "inactive"]

    for col in parse_col_list(request.form.get("bool_cols", "")):
        real_col = resolve_column(column_map, col)
        if real_col:
            normalized = to_str_safe(df[real_col]).str.strip().str.lower()
            normalized = normalized.replace(true_values, "True")
            normalized = normalized.replace(false_values, "False")
            df[real_col] = normalized
            changes.append(f"{real_col}: normalized boolean values")

    # TEXT STANDARDIZATION
    replacements = {
        "usa": "USA", "u.s.a": "USA", "united states": "USA",
        "india": "INDIA", "ind": "INDIA",
        "uk": "UK", "u.k": "UK", "united kingdom": "UK",
        "canada": "CANADA",
    }

    for col in parse_col_list(request.form.get("standardize_cols", "")):
        real_col = resolve_column(column_map, col)
        if real_col:
            normalized = to_str_safe(df[real_col]).str.strip().str.lower()
            df[real_col] = normalized.replace(replacements)
            changes.append(f"{real_col}: standardized text values")

    # ADDRESS CLEANUP
    for col in parse_col_list(request.form.get("address_cols", "")):
        real_col = resolve_column(column_map, col)
        if real_col:
            df[real_col] = (
                to_str_safe(df[real_col])
                .str.strip()
                .str.replace(r",+", ",", regex=True)
                .str.replace(r"\s*,\s*", ", ", regex=True)
                .str.replace(r"\s+", " ", regex=True)
            )
            changes.append(f"{real_col}: cleaned address formatting")

    return df, changes