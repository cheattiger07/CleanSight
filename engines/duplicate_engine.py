from rapidfuzz import fuzz
from utils import build_column_map, resolve_column, parse_col_list

MAX_FUZZY_UNIQUE_VALUES = 1500  # safety cap — avoids O(n²) blowup (fixes SC1)


def duplicate_engine(df, request, changes):
    column_map = build_column_map(df)

    dup_cols = request.form.getlist("dup_cols")
    real_dup_cols = [c for c in (resolve_column(column_map, c) for c in dup_cols) if c]

    if real_dup_cols:
        before = len(df)
        df = df.drop_duplicates(subset=real_dup_cols)
        changes.append(f"Removed {before - len(df)} duplicate rows using {', '.join(real_dup_cols)}")

    # FUZZY DUPLICATE DETECTION
    threshold = request.form.get("fuzzy_threshold", 85)
    try:
        threshold = int(threshold)
    except (TypeError, ValueError):
        threshold = 85

    for col in parse_col_list(request.form.get("fuzzy_cols", "")):
        real_col = resolve_column(column_map, col)
        if not real_col:
            continue

        values = df[real_col].dropna().astype(str).str.strip().str.lower().unique()

        if len(values) > MAX_FUZZY_UNIQUE_VALUES:
            changes.append(
                f"{real_col}: skipped fuzzy matching — {len(values)} unique values "
                f"exceeds the {MAX_FUZZY_UNIQUE_VALUES} safety limit"
            )
            continue

        fuzzy_matches = []
        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                score = fuzz.ratio(values[i], values[j])
                if score >= threshold:
                    fuzzy_matches.append(f"{values[i]} ↔ {values[j]} ({score}%)")

        if fuzzy_matches:
            changes.append(f"{real_col}: found {len(fuzzy_matches)} fuzzy duplicate matches")

    return df, changes