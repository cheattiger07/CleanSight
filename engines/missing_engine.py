import pandas as pd
from utils import build_column_map, resolve_column, parse_col_list, normalize_missing_placeholders


def missing_engine(df, request, changes):

    column_map = build_column_map(df)

    placeholder_values = ["", " ", "na", "n/a", "null", "none", "-", "unknown"]

    # ---------------- MISSING REPORT (snapshot before fills) ----------------
    missing_report = {}
    for col in df.columns:
        col_series = df[col].astype(str).str.strip().str.lower()
        missing_mask = df[col].isna() | col_series.isin(placeholder_values)
        missing_count = int(missing_mask.sum())
        if missing_count > 0:
            missing_report[col] = {
                "missing_count": missing_count,
                "missing_percent": round((missing_count / len(df)) * 100, 2)
            }

    # Normalize placeholder strings to real NaN BEFORE fills run, so
    # "-"/"unknown"/etc actually get filled, not just reported (fixes C8)
    for col in df.columns:
        df[col] = normalize_missing_placeholders(df[col])

    # FILL 0
    for col in parse_col_list(request.form.get("fill0_cols", "")):
        real_col = resolve_column(column_map, col)
        if real_col:
            df[real_col] = df[real_col].fillna(0)
            changes.append(f"{real_col}: filled missing with 0")

    # FILL MEAN
    zero_as_na = request.form.get("zero_as_na_mean")
    for col in parse_col_list(request.form.get("mean_cols", "")):
        real_col = resolve_column(column_map, col)
        if real_col:
            df[real_col] = pd.to_numeric(df[real_col], errors="coerce")
            if zero_as_na:
                df[real_col] = df[real_col].replace(0, pd.NA)
            value = df[real_col].mean()
            df[real_col] = df[real_col].fillna(value)
            changes.append(f"{real_col}: filled with mean ({round(value,2) if pd.notna(value) else value})")

    # FILL UNKNOWN
    for col in parse_col_list(request.form.get("unknown_cols", "")):
        real_col = resolve_column(column_map, col)
        if real_col:
            df[real_col] = df[real_col].fillna("Unknown")
            changes.append(f"{real_col}: filled with Unknown")

    # FILL MEDIAN
    for col in parse_col_list(request.form.get("median_cols", "")):
        real_col = resolve_column(column_map, col)
        if real_col:
            df[real_col] = pd.to_numeric(df[real_col], errors="coerce")
            if zero_as_na:
                df[real_col] = df[real_col].replace(0, pd.NA)
            value = df[real_col].median()
            df[real_col] = df[real_col].fillna(value)
            changes.append(f"{real_col}: filled with median ({round(value,2) if pd.notna(value) else value})")

    # SMART FILL V2
    strategy = request.form.get("smartfill_strategy")

    for col in parse_col_list(request.form.get("smartfill_cols", "")):
        real_col = resolve_column(column_map, col)
        if not real_col:
            continue

        numeric_col = pd.to_numeric(df[real_col], errors="coerce")

        if strategy == "mean":
            value = numeric_col.mean()
            df[real_col] = numeric_col.fillna(value)
            changes.append(f"{real_col}: smart filled with mean ({round(value,2) if pd.notna(value) else value})")
        elif strategy == "median":
            value = numeric_col.median()
            df[real_col] = numeric_col.fillna(value)
            changes.append(f"{real_col}: smart filled with median ({round(value,2) if pd.notna(value) else value})")
        elif strategy == "mode":
            mode_val = df[real_col].mode()
            if not mode_val.empty:
                df[real_col] = df[real_col].fillna(mode_val[0])
                changes.append(f"{real_col}: smart filled with mode ({mode_val[0]})")
        elif strategy == "zero":
            df[real_col] = numeric_col.fillna(0)
            changes.append(f"{real_col}: smart filled with 0")
        elif strategy == "unknown":
            df[real_col] = df[real_col].fillna("Unknown")
            changes.append(f"{real_col}: smart filled with Unknown")

    for col, info in missing_report.items():
        p = float(info["missing_percent"])
        if p < 20:
            info["bar_class"], info["color_class"] = "low", "success"
        elif p < 50:
            info["bar_class"], info["color_class"] = "mid", "warn"
        else:
            info["bar_class"], info["color_class"] = "high", "danger"

    return df, changes, missing_report