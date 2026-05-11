
def quality_engine(df):

    score = 100

    total_cells = len(df) * len(df.columns)

    # missing penalty
    missing_count = df.isna().sum().sum()

    missing_penalty = (
        missing_count / total_cells
    ) * 40

    # duplicate penalty
    duplicate_count = df.duplicated().sum()

    duplicate_penalty = (
        duplicate_count / len(df)
    ) * 30

    # final score
    score = score - missing_penalty - duplicate_penalty

    # keep in range
    score = max(0, round(score, 2))

    return score
