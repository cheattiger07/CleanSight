import pandas as pd
from utils import build_column_map, resolve_column, parse_col_list, to_datetime_safe, to_str_safe


def data_type_engine(df, request, changes):

    column_map = build_column_map(df)

    # NUMERIC TYPE DETECTION
    for col in parse_col_list(request.form.get("numeric_detect_cols", "")):
        real_col = resolve_column(column_map, col)
        if not real_col:
            continue

        before_type = str(df[real_col].dtype)
        converted = pd.to_numeric(df[real_col], errors="coerce")

        non_null = df[real_col].notna().sum()
        success_rate = (converted.notna().sum() / non_null * 100) if non_null else 0

        if success_rate >= 80:
            df[real_col] = converted
            after_type = str(df[real_col].dtype)
            changes.append(f"{real_col}: converted from {before_type} to {after_type}")

    # BOOLEAN DETECTION
    true_values = {"yes", "y", "true", "1"}
    false_values = {"no", "n", "false", "0"}
    allowed = true_values.union(false_values)

    for col in parse_col_list(request.form.get("bool_detect_cols", "")):
        real_col = resolve_column(column_map, col)
        if not real_col:
            continue

        series = to_str_safe(df[real_col]).str.strip().str.lower()
        non_null_vals = set(series.dropna().unique())

        if non_null_vals and non_null_vals.issubset(allowed):
            df[real_col] = series.map({
                "yes": True, "y": True, "true": True, "1": True,
                "no": False, "n": False, "false": False, "0": False
            })
            changes.append(f"{real_col}: auto-detected as boolean")

    # ID PRESERVATION
    for col in parse_col_list(request.form.get("id_cols", "")):
        real_col = resolve_column(column_map, col)
        if real_col:
            df[real_col] = to_str_safe(df[real_col]).str.strip()
            changes.append(f"{real_col}: preserved as ID/string")

    # AUTO DATE DETECTION
    for col in parse_col_list(request.form.get("auto_date_cols", "")):
        real_col = resolve_column(column_map, col)
        if not real_col:
            continue

        before_type = str(df[real_col].dtype)
        converted = to_datetime_safe(df[real_col], dayfirst=True)

        non_null = df[real_col].notna().sum()
        success_rate = (converted.notna().sum() / non_null * 100) if non_null else 0

        if success_rate >= 70:
            df[real_col] = converted
            after_type = str(df[real_col].dtype)
            changes.append(f"{real_col}: auto-detected as date ({after_type})")

    return df, changes