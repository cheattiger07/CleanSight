from flask import Flask,redirect, render_template, request, send_file,flash
import traceback
from exports.report import generate_pdf_report
from exports.excel_report import generate_excel_report
import csv 
import openpyxl
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
app.secret_key = "cleansight-secret-key"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024   # 16MB

UPLOAD_FOLDER = "uploads"
CLEANED_FOLDER = "cleaned"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CLEANED_FOLDER, exist_ok=True)
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    try:
        file = request.files["file"]
        if not file or file.filename == "":
            flash("No file selected.", "danger")
            return redirect("/")
        ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}
        ext = file.filename.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            flash("Only CSV and Excel files are allowed.", "danger")
            return redirect("/")
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        if os.path.getsize(file_path) == 0:
            flash("Uploaded file is empty.", "danger")
            return redirect("/")
        # read based on file type
        if ext == "csv":
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                raw_headers = next(reader)
            if len(raw_headers) != len(set(raw_headers)):
                duplicates = [x for x in raw_headers if raw_headers.count(x) > 1]
                flash(f"Duplicate column names found: {', '.join(set(duplicates))}", "danger")
                return redirect("/")
            try:
                df = pd.read_csv(file_path, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding="latin1")

        else:
            df = pd.read_excel(file_path)
        # now check empty dataframe
        if df.empty:
            flash("Dataset has no rows to process.", "danger")
            return redirect("/")

        # now check all-null columns
        all_null_cols = df.columns[df.isnull().all()].tolist()

        if all_null_cols:
            df=df.drop(columns=all_null_cols)
            flash(f"Warning: all-null columns found: {', '.join(all_null_cols)}", "warning")
            
        recommendations = recommendation_engine(df)
        # -------- dataset stats ----------
        total_rows = len(df)
        total_cols = len(df.columns)
        missing_count = df.isnull().sum().sum()
        duplicate_count = df.duplicated().sum()
        numeric_cols = len(df.select_dtypes(include='number').columns)
        quality_score = quality_engine(df)
        tables = df.head(100).to_html(classes="table", index=False)
        # basic issues before cleaning
        issue_count = 0
        if missing_count > 0:
            issue_count += 1
        if duplicate_count > 0:
            issue_count += 1
        remaining_issues = len(recommendations)
        if recommendations == ["Dataset looks clean."]:
            remaining_issues = 0
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
            remaining_issues=remaining_issues,
            recommendations=recommendations
        )
    except Exception as e:
        print(traceback.format_exc())
        flash(f"Upload failed: {str(e)}", "danger")
        return redirect("/")
# ---------------------------
# CLEAN ENGINE
# ---------------------------
@app.route("/clean", methods=["POST"])
def clean():
    try:
        filename = request.form["filename"]
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        try:
            df = pd.read_csv(file_path, encoding="utf-8",on_bad_lines="skip")
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, encoding="latin1",on_bad_lines="skip")
        df=df.dropna(how="all")
        df=df.loc[:,~df.columns.str.contains("^unnamed")]
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
        excel_path = os.path.join( CLEANED_FOLDER, "cleaned_" + filename.rsplit(".", 1)[0] + ".xlsx")
        with pd.ExcelWriter(excel_path) as writer:
            df.to_excel(writer, sheet_name="Cleaned Data", index=False)
            pd.DataFrame(missing_report).T.to_excel(writer,sheet_name="Missing Report")
            pd.DataFrame([profile]).to_excel(writer,sheet_name="Profile Summary",index=False)
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
            original_table=original_df.head(100).to_html(index=False),
            cleaned_table=df.head(100).to_html(index=False),
            changes=changes,
            filename=filename,
            missing_report=missing_report,
            profile=profile,
            quality_score=quality_score,
            recommendations=recommendations,
            quality_color=quality_color,
            quality_grade=quality_grade,
            quality_stroke=quality_stroke,
        )
    except Exception as e:
        print(traceback.format_exc())
        flash(f"Cleaning failed: {str(e)}", "danger")
        return redirect("/")


# ---------------------------
# DOWNLOAD
# ---------------------------
@app.route("/download", methods=["POST"])
def download():
    try:
        filename = request.form["filename"]
        cleaned_path = os.path.join(CLEANED_FOLDER, "cleaned_" + filename)
        return send_file(cleaned_path, as_attachment=True)
    except Exception as e:
        print(traceback.format_exc())
        flash("Download failed.", "danger")
        return redirect("/")
@app.route("/download/excel", methods=["GET"])
def download_excel():
    try:
        filename = request.args.get("filename")

        cleaned_path = os.path.join(CLEANED_FOLDER, "cleaned_" + filename)

        if not os.path.exists(cleaned_path):
            flash("Cleaned file not found.", "danger")
            return redirect("/")

        df = pd.read_csv(cleaned_path)

        missing_report = []
        for col in df.columns:
            count = df[col].isnull().sum()
            if count > 0:
                pct = round((count / len(df)) * 100, 2)
                missing_report.append([col, count, pct])

        profile = profiling_engine(df)
        recommendations = recommendation_engine(df)
        quality_score = quality_engine(df)

        excel_path = generate_excel_report(
            filename,
            CLEANED_FOLDER,
            df,
            missing_report,
            profile,
            recommendations,
            quality_score
        )

        if not excel_path:
            flash("Excel generation failed.", "danger")
            return redirect("/")

        return send_file(excel_path, as_attachment=True)

    except Exception:
        print(traceback.format_exc())
        flash("Excel generation failed.", "danger")
        return redirect("/")
@app.route("/download/csv")
def download_csv():
    try:
        filename = request.args.get("filename")
        path = os.path.join(
            CLEANED_FOLDER,
            "cleaned_" + filename
        )
        return send_file(path, as_attachment=True)

    except:
        flash("CSV file not found.", "danger")
        return redirect("/")
@app.route("/report")
def report():
    try:
        filename = request.args.get("filename")

        pdf_path = generate_pdf_report(
            filename,
            CLEANED_FOLDER,
            quality_engine,
            recommendation_engine
        )

        return send_file(pdf_path,
                         as_attachment=True)

    except:
        print(traceback.format_exc())
        flash("PDF generation failed.", "danger")
        return redirect("/")
@app.errorhandler(413)
def too_large(e):
    flash("File too large. Max allowed size is 16MB.", "danger")
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)