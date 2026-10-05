import pandas as pd
import re
from utils import EMAIL_REGEX, PHONE_DIGIT_LENGTH


def _reco(text, severity="info", category="General", icon="ti-alert-circle"):
    return {"text": text, "severity": severity, "category": category, "icon": icon}


def recommendation_engine(df):

    recommendations = []

    # MISSING VALUES
    # MISSING VALUES
    missing_cols = df.columns[df.isna().sum() > 0]
    for col in missing_cols:
        if df[col].isna().all():
            recommendations.append(_reco(
                f"{col} is entirely empty → consider dropping this column",
                severity="warning", category="Missing", icon="ti-cell-signal-off"
            ))
        elif pd.api.types.is_numeric_dtype(df[col]):
            recommendations.append(_reco(
                f"{col} is numeric → use median imputation",
                severity="warning", category="Missing", icon="ti-cell-signal-off"
            ))
        else:
            recommendations.append(_reco(
                f"{col} is categorical → use mode imputation",
                severity="warning", category="Missing", icon="ti-cell-signal-off"
            ))

    # DUPLICATES
    duplicate_count = df.duplicated().sum()
    if duplicate_count > 0:
        recommendations.append(_reco(
            f"{duplicate_count} duplicate rows found → remove duplicates",
            severity="warning", category="Duplicate", icon="ti-copy"
        ))

    # NEGATIVE VALUES
    numeric_cols = df.select_dtypes(include=["number"]).columns
    for col in numeric_cols:
        negative_count = (df[col] < 0).sum()
        if negative_count > 0:
            recommendations.append(_reco(
                f"{col}: contains negative values",
                severity="critical", category="Outlier", icon="ti-trending-down"
            ))

    # CASE INCONSISTENCY
    text_cols = df.select_dtypes(include=["object"]).columns
    for col in text_cols:
        sample = df[col].dropna().astype(str).head(20)
        lower_exists = sample.str.islower().any()
        upper_exists = sample.str.isupper().any()
        if lower_exists and upper_exists:
            recommendations.append(_reco(
                f"{col}: inconsistent text casing",
                severity="warning", category="Consistency", icon="ti-alert-circle"
            ))

    # DATE FORMAT CHECK
    for col in df.columns:
        col_lower = col.lower()
        if "date" in col_lower or "time" in col_lower:
            recommendations.append(_reco(
                f"{col}: standardize date format",
                severity="info", category="Format", icon="ti-calendar"
            ))

    # EMAIL VALIDATION
    for col in df.columns:
        if "email" in col.lower():
            invalid_count = df[col].dropna().apply(
                lambda x: not bool(re.match(EMAIL_REGEX, str(x)))
            ).sum()
            if invalid_count > 0:
                recommendations.append(_reco(
                    f"{col}: contains {invalid_count} invalid emails",
                    severity="critical", category="Validation", icon="ti-at"
                ))

    # PHONE VALIDATION — now strips formatting before counting digits (fixes C16)
    for col in df.columns:
        if "phone" in col.lower() or "mobile" in col.lower():
            invalid_count = df[col].dropna().apply(
                lambda x: len(re.sub(r"\D", "", str(x))) != PHONE_DIGIT_LENGTH
            ).sum()
            if invalid_count > 0:
                recommendations.append(_reco(
                    f"{col}: contains {invalid_count} invalid phone numbers",
                    severity="critical", category="Validation", icon="ti-phone"
                ))

    # No more "Dataset looks clean." string — an empty list now means clean.
    return recommendations