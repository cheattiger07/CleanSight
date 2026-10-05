from utils import build_column_map, resolve_column, parse_col_list, dedupe_columns


def schema_engine(df, request, changes):
    column_map = build_column_map(df)

    # REMOVE COLUMNS (fixes C13 — never drop the last column)
    for col in parse_col_list(request.form.get("drop_cols", "")):
        real_col = resolve_column(column_map, col)
        if real_col and real_col in df.columns:
            if len(df.columns) <= 1:
                changes.append(f"Skipped dropping {real_col}: cannot drop the last remaining column")
                continue
            df = df.drop(columns=[real_col])
            changes.append(f"Dropped column {real_col}")

    # DROP NULL ROWS (fixes C13 — never drop to zero rows silently)
    if request.form.get("drop_nulls"):
        before = len(df)
        candidate = df.dropna()
        if len(candidate) == 0 and before > 0:
            changes.append("Skipped dropping null rows: would remove all rows")
        else:
            df = candidate
            changes.append(f"Dropped null rows: {before - len(df)} rows")

    # CLEAN COLUMN NAMES (fixes C12 — dedupe after normalization)
    if request.form.get("clean_columns"):
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)
        df = dedupe_columns(df)
        changes.append("Cleaned column names")

    return df, changes