import pandas as pd
from rapidfuzz import fuzz
def duplicate_engine(df, request, changes):
    # ---------------- COLUMN MAP ----------------
    column_map = {}
    for col in df.columns:
        column_map[col.lower()] = col

    dup_cols = request.form.getlist("dup_cols")

    real_dup_cols = []

    for col in dup_cols:
        real_col = column_map.get(col.lower())
        if real_col:
            real_dup_cols.append(real_col)

    if real_dup_cols:
        before = len(df)
        df = df.drop_duplicates(subset=real_dup_cols)
        removed = before - len(df)

        changes.append(
            f"Removed {removed} duplicate rows using {', '.join(real_dup_cols)}"
        )    # FUZZY DUPLICATE DETECTION
    # ==================================================

    fuzzy_cols = request.form.get(
        "fuzzy_cols",
        ""
    ).split(",")

    threshold = request.form.get(
        "fuzzy_threshold",
        85
    )

    try:
        threshold = int(threshold)
    except:
        threshold = 85

    for col in fuzzy_cols:

        col = col.strip()

        real_col = column_map.get(col.lower())

        if real_col:

            values = (
                df[real_col]
                .dropna()
                .astype(str)
                .unique()
            )

            fuzzy_matches = []

            for i in range(len(values)):

                for j in range(i + 1, len(values)):

                    score = fuzz.ratio(
                        values[i].lower(),
                        values[j].lower()
                    )

                    if score >= threshold:

                        fuzzy_matches.append(
                            f"{values[i]} ↔ {values[j]} ({score}%)"
                        )

            if fuzzy_matches:

                changes.append(
                    f"{real_col}: found {len(fuzzy_matches)} fuzzy duplicate matches"
                )


    return df, changes