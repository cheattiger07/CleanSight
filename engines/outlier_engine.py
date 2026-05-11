import pandas as pd

def outlier_engine(df, request, changes):

    # ---------------- COLUMN MAP ----------------
    column_map = {}

    for col in df.columns:
        column_map[col.lower()] = col


    # ==================================================
    # NEGATIVE VALUE DETECTION
    # ==================================================

    negative_cols = request.form.get(
        "negative_cols",
        ""
    ).split(",")

    for col in negative_cols:

        col = col.strip()

        real_col = column_map.get(col.lower())

        if real_col:

            # numeric conversion
            df[real_col] = pd.to_numeric(
                df[real_col],
                errors="coerce"
            )

            negative_count = (
                df[real_col] < 0
            ).sum()

            if negative_count > 0:

                changes.append(
                    f"{real_col}: found {negative_count} negative values"
                )
    # IQR OUTLIER DETECTION
    # ==================================================

    outlier_cols = request.form.get(
        "outlier_cols",
        ""
    ).split(",")

    for col in outlier_cols:

        col = col.strip()

        real_col = column_map.get(col.lower())

        if real_col:

            # convert numeric
            df[real_col] = pd.to_numeric(
                df[real_col],
                errors="coerce"
            )

            Q1 = df[real_col].quantile(0.25)
            Q3 = df[real_col].quantile(0.75)

            IQR = Q3 - Q1

            lower_bound = Q1 - (1.5 * IQR)
            upper_bound = Q3 + (1.5 * IQR)

            outliers = df[
                (df[real_col] < lower_bound) |
                (df[real_col] > upper_bound)
            ]

            outlier_count = len(outliers)

            if outlier_count > 0:

                changes.append(
                    f"{real_col}: found {outlier_count} outliers using IQR"
                )

    # IMPOSSIBLE VALUE DETECTION
    # ==================================================

    impossible_cols = request.form.get(
        "impossible_cols",
        ""
    ).split(",")

    min_value = request.form.get("min_value")
    max_value = request.form.get("max_value")

    for col in impossible_cols:

        col = col.strip()

        real_col = column_map.get(col.lower())

        if real_col:

            df[real_col] = pd.to_numeric(
                df[real_col],
                errors="coerce"
            )

            invalid_count = 0

            # minimum check
            if min_value:

                invalid_count += (
                    df[real_col] < float(min_value)
                ).sum()

            # maximum check
            if max_value:

                invalid_count += (
                    df[real_col] > float(max_value)
                ).sum()

            if invalid_count > 0:

                changes.append(
                    f"{real_col}: found {invalid_count} impossible values"
                )
    # DATE RANGE VALIDATION
    # ==================================================

    date_validate_cols = request.form.get(
        "date_validate_cols",
        ""
    ).split(",")

    min_date = request.form.get("min_date")
    max_date = request.form.get("max_date")

    for col in date_validate_cols:

        col = col.strip()

        real_col = column_map.get(col.lower())

        if real_col:

            # convert to datetime
            converted = pd.to_datetime(
                df[real_col],
                errors="coerce"
            )

            invalid_count = 0

            # minimum date check
            if min_date:

                invalid_count += (
                    converted < pd.to_datetime(min_date)
                ).sum()

            # maximum date check
            if max_date:

                invalid_count += (
                    converted > pd.to_datetime(max_date)
                ).sum()

            if invalid_count > 0:

                changes.append(
                    f"{real_col}: found {invalid_count} invalid date values"
                )

    # EMAIL VALIDATION
    # ==================================================

    email_validate_cols = request.form.get(
        "email_validate_cols",
        ""
    ).split(",")

    email_pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'

    for col in email_validate_cols:

        col = col.strip()

        real_col = column_map.get(col.lower())

        if real_col:

            invalid_mask = ~df[real_col].astype(str).str.match(
                email_pattern,
                na=False
            )

            invalid_count = invalid_mask.sum()

            if invalid_count > 0:

                changes.append(
                    f"{real_col}: found {invalid_count} invalid emails"
                )



    return df, changes
