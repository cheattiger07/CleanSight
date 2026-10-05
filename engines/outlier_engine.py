import pandas as pd
from utils import build_column_map, resolve_column, parse_col_list, safe_float, safe_date, EMAIL_REGEX


def outlier_engine(df, request, changes):

    column_map = build_column_map(df)

    # NEGATIVE VALUE DETECTION
    for col in parse_col_list(request.form.get("negative_cols", "")):
        real_col = resolve_column(column_map, col)
        if real_col:
            df[real_col] = pd.to_numeric(df[real_col], errors="coerce")
            negative_count = int((df[real_col] < 0).sum())
            if negative_count > 0:
                changes.append(f"{real_col}: found {negative_count} negative values")

    # IQR OUTLIER DETECTION
    for col in parse_col_list(request.form.get("outlier_cols", "")):
        real_col = resolve_column(column_map, col)
        if real_col:
            df[real_col] = pd.to_numeric(df[real_col], errors="coerce")
            Q1 = df[real_col].quantile(0.25)
            Q3 = df[real_col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound, upper_bound = Q1 - 1.5*IQR, Q3 + 1.5*IQR
            outlier_count = int(((df[real_col] < lower_bound) | (df[real_col] > upper_bound)).sum())
            if outlier_count > 0:
                changes.append(f"{real_col}: found {outlier_count} outliers using IQR")

    # IMPOSSIBLE VALUE DETECTION (fixes C5 — no crash on bad input)
    min_value = safe_float(request.form.get("min_value"))
    max_value = safe_float(request.form.get("max_value"))

    for col in parse_col_list(request.form.get("impossible_cols", "")):
        real_col = resolve_column(column_map, col)
        if real_col:
            df[real_col] = pd.to_numeric(df[real_col], errors="coerce")
            invalid_count = 0
            if min_value is not None:
                invalid_count += int((df[real_col] < min_value).sum())
            if max_value is not None:
                invalid_count += int((df[real_col] > max_value).sum())
            if invalid_count > 0:
                changes.append(f"{real_col}: found {invalid_count} impossible values")

    # DATE RANGE VALIDATION (fixes C5)
    min_date = safe_date(request.form.get("min_date"))
    max_date = safe_date(request.form.get("max_date"))

    for col in parse_col_list(request.form.get("date_validate_cols", "")):
        real_col = resolve_column(column_map, col)
        if real_col:
            converted = pd.to_datetime(df[real_col], errors="coerce", dayfirst=True, format="mixed")
            invalid_count = 0
            if min_date is not None:
                invalid_count += int((converted < min_date).sum())
            if max_date is not None:
                invalid_count += int((converted > max_date).sum())
            if invalid_count > 0:
                changes.append(f"{real_col}: found {invalid_count} invalid date values")

    # EMAIL VALIDATION
    for col in parse_col_list(request.form.get("email_validate_cols", "")):
        real_col = resolve_column(column_map, col)
        if real_col:
            invalid_mask = ~df[real_col].astype(str).str.match(EMAIL_REGEX, na=False)
            invalid_count = int(invalid_mask.sum())
            if invalid_count > 0:
                changes.append(f"{real_col}: found {invalid_count} invalid emails")

    return df, changes