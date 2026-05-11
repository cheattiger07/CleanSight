import pandas as pd

def data_type_engine(df, request, changes):

    # ---------------- COLUMN MAP ----------------
    column_map = {}

    for col in df.columns:
        column_map[col.lower()] = col


    # ==================================================
    # NUMERIC TYPE DETECTION
    # ==================================================

    numeric_detect_cols = request.form.get(
        "numeric_detect_cols",
        ""
    ).split(",")

    for col in numeric_detect_cols:

        col = col.strip()

        real_col = column_map.get(col.lower())

        if real_col:

            before_type = str(df[real_col].dtype)

            converted = pd.to_numeric(
                df[real_col],
                errors="coerce"
            )

            success_rate = (
                converted.notna().sum() / len(df)
            ) * 100

            if success_rate >= 80:

                df[real_col] = converted

                after_type = str(df[real_col].dtype)

                changes.append(
                    f"{real_col}: converted from {before_type} to {after_type}"
                )


    # ==================================================
    # BOOLEAN DETECTION
    # ==================================================

    bool_detect_cols = request.form.get(
        "bool_detect_cols",
        ""
    ).split(",")

    true_values = {
        "yes", "y", "true", "1"
    }

    false_values = {
        "no", "n", "false", "0"
    }

    for col in bool_detect_cols:

        col = col.strip()

        real_col = column_map.get(col.lower())

        if real_col:

            series = (
                df[real_col]
                .astype(str)
                .str.strip()
                .str.lower()
            )

            unique_vals = set(series.dropna().unique())

            allowed = true_values.union(false_values)

            if unique_vals.issubset(allowed):

                df[real_col] = series.replace({
                    "yes": True,
                    "y": True,
                    "true": True,
                    "1": True,

                    "no": False,
                    "n": False,
                    "false": False,
                    "0": False
                })

                changes.append(
                    f"{real_col}: auto-detected as boolean"
                )

    # ID PRESERVATION
    id_cols = request.form.get(
        "id_cols",
        ""
    ).split(",")

    for col in id_cols:

        col = col.strip()

        real_col = column_map.get(col.lower())

        if real_col:

            # force string type
            df[real_col] = (
                df[real_col]
                .astype(str)
                .str.strip()
            )

            changes.append(
                f"{real_col}: preserved as ID/string"
            )

    # AUTO DATE DETECTION
    # ==================================================

    auto_date_cols = request.form.get(
        "auto_date_cols",
        ""
    ).split(",")

    for col in auto_date_cols:

        col = col.strip()

        real_col = column_map.get(col.lower())

        if real_col:

            before_type = str(df[real_col].dtype)

            converted = pd.to_datetime(
                df[real_col],
                errors="coerce"
            )

            success_rate = (
                converted.notna().sum() / len(df)
            ) * 100

            # only convert if mostly valid dates
            if success_rate >= 70:

                df[real_col] = converted

                after_type = str(df[real_col].dtype)

                changes.append(
                    f"{real_col}: auto-detected as date ({after_type})"
                )





    # ==================================================
    # RETURN
    # ==================================================

    return df, changes

