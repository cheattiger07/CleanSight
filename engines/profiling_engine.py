import pandas as pd

def profiling_engine(df):

    profile = {}

    profile["rows"] = len(df)

    profile["columns"] = len(df.columns)

    profile["duplicate_rows"] = int(
        df.duplicated().sum()
    )

    profile["missing_values"] = int(
        df.isna().sum().sum()
    )

    numeric_cols = df.select_dtypes(
        include=["number"]
    ).columns

    text_cols = df.select_dtypes(
        include=["object"]
    ).columns

    profile["numeric_columns"] = len(numeric_cols)

    profile["text_columns"] = len(text_cols)

    return profile
