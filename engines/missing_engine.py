import pandas as pd

def missing_engine(df, request, changes):

    missing_report = {}
    column_map={}
    for col in df.columns:
        column_map[col.lower()] = col
    #Missing data
    missing_report = {}

    placeholder_values = [
        "", " ", "na", "n/a",
        "null", "none", "-",
        "unknown"
    ]

    for col in df.columns:

        col_series = df[col].astype(str).str.strip().str.lower()

        missing_mask = (
            df[col].isna() |
            col_series.isin(placeholder_values)
        )

        missing_count = missing_mask.sum()

        if missing_count > 0:

            missing_report[col] = {
                "missing_count": int(missing_count),
                "missing_percent": round(
                    (missing_count / len(df)) * 100,
                    2
                )
            }
    # FILL 0
    fill0_cols = request.form.get("fill0_cols", "").split(",")

    for col in fill0_cols:

        col = col.strip()
        real_col = column_map.get(col.lower())
        if real_col:
            df[real_col] = df[real_col].fillna(0)
            changes.append(f"{real_col}: filled missing with 0")


    # FILL MEAN
    mean_cols = request.form.get("mean_cols", "").split(",")
    zero_as_na = request.form.get("zero_as_na_mean")
    for col in mean_cols:

        col = col.strip()
        real_col = column_map.get(col.lower())
        if real_col:
            df[real_col] = pd.to_numeric(df[real_col], errors="coerce")
            if zero_as_na:
                df[real_col] = df[real_col].replace(0, pd.NA)
            value = df[real_col].mean()
            df[real_col] = df[real_col].fillna(value)

            changes.append(f"{real_col}: filled with mean ({round(value,2)})")


    # FILL UNKNOWN
    unknown_cols = request.form.get("unknown_cols", "").split(",")

    for col in unknown_cols:

        col = col.strip()
        real_col = column_map.get(col.lower())
        if real_col:
            df[real_col] = df[real_col].fillna("Unknown")

            changes.append(f"{real_col}: filled with Unknown")
    # FILL WITH MEDIAN
    median_cols = request.form.get("median_cols", "").split(",")

    for col in median_cols:
        
        col = col.strip()
        real_col = column_map.get(col.lower())
        if real_col:
            df[real_col] = pd.to_numeric(df[real_col], errors="coerce")
            if zero_as_na:
                df[real_col] = df[real_col].replace(0, pd.NA)
            value = df[real_col].median()
            
            df[real_col] = df[real_col].fillna(value)

            changes.append(f"{real_col}: filled with median ({round(value,2)})")
    
    # ---------------- SMART FILL V2 ----------------

    smartfill_cols = request.form.get(
        "smartfill_cols",
        ""
    ).split(",")

    strategy = request.form.get("smartfill_strategy")


    for col in smartfill_cols:

        col = col.strip()

        real_col = column_map.get(col.lower())

        if not real_col:
            continue

        # normalize missing
        df[real_col] = df[real_col].replace(
            ["", " ", "NA", "na", "NaN", "nan", "null", "-", "unknown"],
            pd.NA
        )

        numeric_col = pd.to_numeric(
            df[real_col],
            errors="coerce"
        )

        # ---------- MEAN ----------
        if strategy == "mean":

            value = numeric_col.mean()

            df[real_col] = numeric_col.fillna(value)

            changes.append(
                f"{real_col}: smart filled with mean ({round(value,2)})"
            )

        # ---------- MEDIAN ----------
        elif strategy == "median":

            value = numeric_col.median()

            df[real_col] = numeric_col.fillna(value)

            changes.append(
                f"{real_col}: smart filled with median ({round(value,2)})"
            )

        # ---------- MODE ----------
        elif strategy == "mode":

            mode_val = df[real_col].mode()

            if not mode_val.empty:

                df[real_col] = df[real_col].fillna(mode_val[0])

                changes.append(
                    f"{real_col}: smart filled with mode ({mode_val[0]})"
                )

        # ---------- ZERO ----------
        elif strategy == "zero":

            df[real_col] = numeric_col.fillna(0)

            changes.append(
                f"{real_col}: smart filled with 0"
            )

        # ---------- UNKNOWN ----------
        elif strategy == "unknown":

            df[real_col] = df[real_col].fillna("Unknown")

            changes.append(
                f"{real_col}: smart filled with Unknown"
            )
    for col, info in missing_report.items():
        p = float(info["missing_percent"])

        if p < 20:
            info["bar_class"] = "low"
            info["color_class"] = "success"

        elif p < 50:
            info["bar_class"] = "mid"
            info["color_class"] = "warn"

        else:
            info["bar_class"] = "high"
            info["color_class"] = "danger"
    return df, changes, missing_report