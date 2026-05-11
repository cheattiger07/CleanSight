import pandas as pd
def schema_engine(df, request, changes):
    column_map={}
    for col in df.columns:
        column_map[col.lower()] = col
    #REMOVE COLUMNS
    drop_cols = request.form.get("drop_cols", "").split(",")
    for col in drop_cols:

        col = col.strip()
        real_col = column_map.get(col.lower())
        if real_col:
            df = df.drop(columns=[real_col])

            changes.append(f"Dropped column {real_col}")
    #drop NULL ROWS
    if request.form.get("drop_nulls"):
        before = len(df)
        df = df.dropna()
        changes.append(f"Dropped null rows: {before - len(df)} rows")
    #CLEAN COLUMN
    if request.form.get("clean_columns"):
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
        changes.append("Cleaned column names")
    
    
    return df,changes
