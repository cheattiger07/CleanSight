import pandas as pd
import re


def recommendation_engine(df):

    recommendations = []

    # =========================
    # MISSING VALUES (SMART)
    # =========================
    missing_cols = df.columns[df.isna().sum() > 0]

    for col in missing_cols:

        if pd.api.types.is_numeric_dtype(df[col]):
            recommendations.append(
                f"{col} is numeric → use median imputation"
            )

        else:
            recommendations.append(
                f"{col} is categorical → use mode imputation"
            )

    # =========================
    # DUPLICATES
    # =========================
    duplicate_count = df.duplicated().sum()

    if duplicate_count > 0:
        recommendations.append(
            f"{duplicate_count} duplicate rows found → remove duplicates"
        )

    # =========================
    # NEGATIVE VALUES
    # =========================
    numeric_cols = df.select_dtypes(
        include=["number"]
    ).columns

    for col in numeric_cols:

        negative_count = (df[col] < 0).sum()

        if negative_count > 0:
            recommendations.append(
                f"{col}: contains negative values"
            )

    # =========================
    # CASE INCONSISTENCY
    # =========================
    text_cols = df.select_dtypes(
        include=["object"]
    ).columns

    for col in text_cols:

        sample = (
            df[col]
            .dropna()
            .astype(str)
            .head(20)
        )

        lower_exists = sample.str.islower().any()
        upper_exists = sample.str.isupper().any()

        if lower_exists and upper_exists:
            recommendations.append(
                f"{col}: inconsistent text casing"
            )

    # =========================
    # DATE FORMAT CHECK
    # =========================
    for col in df.columns:

        col_lower = col.lower()

        if "date" in col_lower or "time" in col_lower:
            recommendations.append(
                f"{col}: standardize date format"
            )

    # =========================
    # EMAIL VALIDATION
    # =========================
    for col in df.columns:

        if "email" in col.lower():

            invalid_count = df[col].dropna().apply(
                lambda x: not bool(
                    re.match(
                        r'^[^@]+@[^@]+\.[^@]+$',
                        str(x)
                    )
                )
            ).sum()

            if invalid_count > 0:
                recommendations.append(
                    f"{col}: contains {invalid_count} invalid emails"
                )

    # =========================
    # PHONE VALIDATION
    # =========================
    for col in df.columns:

        if "phone" in col.lower() or "mobile" in col.lower():

            invalid_count = df[col].dropna().apply(
                lambda x: len(str(x)) != 10
            ).sum()

            if invalid_count > 0:
                recommendations.append(
                    f"{col}: contains {invalid_count} invalid phone numbers"
                )

    # =========================
    # CLEAN DATASET
    # =========================
    if not recommendations:
        recommendations.append(
            "Dataset looks clean."
        )

    return recommendations