from flask import Flask, render_template, request, send_file
from engines.profiling_engine import profiling_engine
from engines.missing_engine import missing_engine
from engines.outlier_engine import outlier_engine
from engines.formatting_engine import formatting_engine
from engines.quality_engine import quality_engine
from engines.recommendation_engine import recommendation_engine
from engines.schema_engine import schema_engine
from engines.duplicate_engine import duplicate_engine
from engines.data_type_engine import data_type_engine
import pandas as pd
import os

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
CLEANED_FOLDER = "cleaned"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CLEANED_FOLDER, exist_ok=True)
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]

    if not file:
        return "No file uploaded"

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    df = pd.read_csv(file_path)
    recommendations = recommendation_engine(df)

    # -------- dataset stats ----------
    total_rows = len(df)
    total_cols = len(df.columns)

    missing_count = df.isnull().sum().sum()
    duplicate_count = df.duplicated().sum()
    numeric_cols = len(df.select_dtypes(include='number').columns)

    quality_score = max(
        0,
        100 - (
            int(missing_count / max(total_rows * total_cols, 1) * 50)
            + int(duplicate_count / max(total_rows, 1) * 50)
        )
    )
    tables = df.head(50).to_html(classes="table", index=False)

    # basic issues before cleaning
    issue_count = 0

    if missing_count > 0:
        issue_count += 1

    if duplicate_count > 0:
        issue_count += 1

    return render_template(
        "tool.html",
        filename=file.filename,
        tables=tables,
        columns=df.columns,

        total_rows=total_rows,
        total_cols=total_cols,
        missing_count=missing_count,
        duplicate_count=duplicate_count,
        numeric_cols=numeric_cols,
        quality_score=quality_score,
        issue_count=issue_count,
        recommendations=recommendations
    )
# ---------------------------
# CLEAN ENGINE
# ---------------------------
@app.route("/clean", methods=["POST"])
def clean():
    filename = request.form["filename"]
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    df = pd.read_csv(file_path)
    #save the original data
    original_df = df.copy()

    changes = []

    # ---------------- SCHEMA ENGINE ----------------
    df, changes = schema_engine(df, request, changes)
    # ---------------- formatting DATA ----------------
    df, changes = formatting_engine(df, request, changes)
     #----------------- data type engine --------------
    df, changes = data_type_engine(df, request, changes)
    # ---------------- MISSING DATA ----------------
    df, changes, missing_report = missing_engine(df, request, changes)
    #----------------- Outlier DATA ------------------
    df,changes = outlier_engine(df, request, changes)
    # ---------------- Duplicate DATA ----------------
    df, changes = duplicate_engine(df, request, changes)
        
    # ---------------- SAVE CLEANED ----------------
    cleaned_path = os.path.join(CLEANED_FOLDER, "cleaned_" + filename)
    df.to_csv(cleaned_path, index=False)
    
    profile = profiling_engine(df)
    quality_score = quality_engine(df)
    recommendations = recommendation_engine(df)
    # Quality color logic
    if quality_score >= 80:
        quality_color = "var(--success)"
        quality_grade = "Excellent — dataset is clean"
    elif quality_score >= 50:
        quality_color = "var(--warn)"
        quality_grade = "Fair — some issues remain"
    else:
        quality_color = "var(--danger)"
        quality_grade = "Poor — significant cleaning needed"

    # SVG stroke color (ring)
    if quality_score >= 80:
        quality_stroke = "#2d6a11"
    elif quality_score >= 50:
        quality_stroke = "#854f0b"
    else:
        quality_stroke = "#a32d2d"
    


    return render_template(
        "result.html",
        original_table=original_df.head(25).to_html(index=False),
        cleaned_table=df.head(25).to_html(index=False),
        changes=changes,
        filename=filename,
        missing_report=missing_report,
        profile=profile,
        quality_score=quality_score,
        recommendations=recommendations,
        quality_color=quality_color,
        quality_grade=quality_grade,
        quality_stroke=quality_stroke  
    )


# ---------------------------
# DOWNLOAD
# ---------------------------
@app.route("/download", methods=["POST"])
def download():
    filename = request.form["filename"]
    cleaned_path = os.path.join(CLEANED_FOLDER, "cleaned_" + filename)
    return send_file(cleaned_path, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)