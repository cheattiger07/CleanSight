import pandas as pd

def formatting_engine(df, request, changes):
    column_map={}
    for col in df.columns:
        column_map[col.lower()] = col
    # LOWERCASE
    lower_cols = request.form.get("lower_cols", "").split(",")
    
    for col in lower_cols:

        col = col.strip()
        real_col = column_map.get(col.lower())
        if real_col:
            df[real_col] = df[real_col].astype(str).str.lower()
            changes.append(f"{real_col}: converted to lowercase")


     # TRIM
    trim_cols = request.form.get("trim_cols", "").split(",")

    for col in trim_cols:

        col = col.strip()
        real_col = column_map.get(col.lower())
        if real_col:
            df[real_col] = df[real_col].astype(str).str.strip()
            changes.append(f"{real_col}: trimmed spaces")

    
    # NUMERIC CLEANUP
    numeric_cols = request.form.get("numeric_clean_cols", "").split(",")

    for col in numeric_cols:

        col = col.strip()

        real_col = column_map.get(col.lower())

        if real_col:

            # convert to string
            df[real_col] = df[real_col].astype(str)

            # remove currency symbols, commas, percentages, units
            df[real_col] = (
                df[real_col]
                .str.replace(r"[₹$€,%kg]", "", regex=True)
                .str.replace(",", "", regex=False)
                .str.strip()
            )

            # convert cleaned values to numeric
            df[real_col] = pd.to_numeric(
                df[real_col],
                errors="coerce"
            )

            changes.append(
                f"{real_col}: cleaned numeric formatting"
            )

  
    # EMAIL CLEANUP
    email_cols = request.form.get("email_cols", "").split(",")

    for col in email_cols:

        col = col.strip()

        real_col = column_map.get(col.lower())

        if real_col:

            # basic cleanup
            df[real_col] = (
                df[real_col]
                .astype(str)
                .str.strip()
                .str.lower()
                .str.replace(" ", "", regex=False)
            )

            # detect invalid emails
            invalid_mask = ~df[real_col].str.contains(
                r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",
                regex=True,
                na=False
            )

            invalid_count = invalid_mask.sum()

            changes.append(
                f"{real_col}: cleaned email formatting, invalid emails found = {invalid_count}"
            )

    # PHONE NUMBER CLEANUP
    phone_cols = request.form.get("phone_cols", "").split(",")

    for col in phone_cols:

        col = col.strip()

        real_col = column_map.get(col.lower())

        if real_col:

            # convert to string
            df[real_col] = df[real_col].astype(str)

            # keep only digits
            df[real_col] = df[real_col].str.replace(
                r"\D",
                "",
                regex=True
            )

            # remove leading country code 91 if length > 10
            df[real_col] = df[real_col].apply(
                lambda x: x[-10:] if len(x) > 10 else x
            )

            # invalid phone detection
            invalid_count = (
                df[real_col].str.len() != 10
            ).sum()

            changes.append(
                f"{real_col}: standardized phone numbers, invalid numbers found = {invalid_count}"
            )


    # DATE STANDARDIZATION
    date_cols = request.form.get("date_cols", "").split(",")

    for col in date_cols:

        col = col.strip()

        real_col = column_map.get(col.lower())

        if real_col:

        # convert to string
            df[real_col] = df[real_col].astype(str)

        # normalize separators
            df[real_col] = df[real_col].str.replace("/", "-", regex=False)

        # parse dates
            df[real_col] = pd.to_datetime(
                df[real_col],
                errors="coerce"
            )

        # count invalid dates
            invalid_dates = df[real_col].isna().sum()

        # standardize format
            df[real_col] = df[real_col].dt.strftime("%Y-%m-%d")

            changes.append(
                f"{real_col}: standardized date format, invalid dates found = {invalid_dates}"
            )
    # BOOLEAN NORMALIZATION
    bool_cols = request.form.get("bool_cols", "").split(",")

    true_values = [
        "yes", "y", "true", "1", "active"
    ]

    false_values = [
        "no", "n", "false", "0", "inactive"
    ]

    for col in bool_cols:

        col = col.strip()

        real_col = column_map.get(col.lower())

        if real_col:

            # normalize text
            df[real_col] = (
                df[real_col]
                .astype(str)
                .str.strip()
                .str.lower()
            )

            # map values
            df[real_col] = df[real_col].replace(
                true_values,
                "True"
            )

            df[real_col] = df[real_col].replace(
                false_values,
                "False"
            )

            changes.append(
                f"{real_col}: normalized boolean values"
            )
    # TEXT STANDARDIZATION
    standardize_cols = request.form.get(
        "standardize_cols",
        ""
    ).split(",")

    replacements = {
        "usa": "USA",
        "u.s.a": "USA",
        "united states": "USA",

        "india": "INDIA",
        "ind": "INDIA",

        "uk": "UK",
        "u.k": "UK",
        "united kingdom": "UK",

        "canada": "CANADA"
    }

    for col in standardize_cols:

        col = col.strip()

        real_col = column_map.get(col.lower())

        if real_col:

            # normalize
            df[real_col] = (
                df[real_col]
                .astype(str)
                .str.strip()
                .str.lower()
            )

            # replace values
            df[real_col] = df[real_col].replace(
                replacements
            )

            changes.append(
                f"{real_col}: standardized text values"
            )

    # ADDRESS CLEANUP
    address_cols = request.form.get(
        "address_cols",
        ""
    ).split(",")

    for col in address_cols:

        col = col.strip()

        real_col = column_map.get(col.lower())

        if real_col:

            df[real_col] = (
                df[real_col]
                .astype(str)

                # remove extra spaces
                .str.strip()

                # remove repeated commas
                .str.replace(r",+", ",", regex=True)

                # normalize comma spacing
                .str.replace(r"\s*,\s*", ", ", regex=True)

                # remove multiple spaces
                .str.replace(r"\s+", " ", regex=True)
            )

            changes.append(
                f"{real_col}: cleaned address formatting"
            )



    return df, changes

