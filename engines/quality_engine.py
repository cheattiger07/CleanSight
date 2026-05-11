import pandas as pd
def quality_engine(df):
    score = 100

    rows = len(df)
    cols = len(df.columns)
    total_cells = max(rows * cols, 1)

    # 1. Missing values (max -30)
    missing = df.isnull().sum().sum()
    score -= min((missing / total_cells) * 100, 30)

    # 2. Duplicate rows (max -20)
    duplicates = df.duplicated().sum()
    score -= min((duplicates / max(rows, 1)) * 100, 20)

    # 3. Negative values (max -15)
    numeric_df = df.select_dtypes(include="number")
    negatives = (numeric_df < 0).sum().sum()
    score -= min(negatives * 3, 15)

    # 4. Zero values (max -10)
    zeros = (numeric_df == 0).sum().sum()
    score -= min(zeros * 1, 10)

    # 5. Outliers using IQR (max -15)
    outliers = 0
    for col in numeric_df.columns:
        q1 = numeric_df[col].quantile(0.25)
        q3 = numeric_df[col].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outliers += ((numeric_df[col] < lower) | (numeric_df[col] > upper)).sum()
    score -= min(outliers * 2, 15)

    # 6. Invalid dates (max -10)
    date_cols = [c for c in df.columns if "date" in c.lower()]
    invalid_dates = 0
    for col in date_cols:
        parsed = pd.to_datetime(df[col], errors="coerce")
        invalid_dates += parsed.isnull().sum()
    score -= min(invalid_dates * 2, 10)

    return round(max(score, 0))