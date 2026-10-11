from flask import Flask, render_template, request, send_file, jsonify
import pandas as pd
import os
import io
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB upload limit
ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# In-memory cleaned-file store for this MVP. Restarting the server clears it.
cleaned_files = {}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def read_table(file_storage, filename):
    extension = filename.rsplit(".", 1)[1].lower()
    if extension == "csv":
        # Try common encodings and let pandas infer the separator.
        raw = file_storage.read()
        file_storage.stream.seek(0)
        try:
            return pd.read_csv(io.BytesIO(raw), sep=None, engine="python", encoding="utf-8")
        except UnicodeDecodeError:
            return pd.read_csv(io.BytesIO(raw), sep=None, engine="python", encoding="latin-1")
    if extension in {"xlsx", "xls"}:
        return pd.read_excel(file_storage)
    raise ValueError("Unsupported file type.")

def make_unique_columns(columns):
    seen = {}
    result = []
    for col in columns:
        base = col if col else "column"
        count = seen.get(base, 0)
        result.append(base if count == 0 else f"{base}_{count + 1}")
        seen[base] = count + 1
    return result

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/clean", methods=["POST"])
def clean_file():
    if "file" not in request.files:
        return jsonify(error="Please choose a file to upload."), 400

    uploaded = request.files["file"]
    if not uploaded.filename:
        return jsonify(error="Please choose a file to upload."), 400
    if not allowed_file(uploaded.filename):
        return jsonify(error="Unsupported file type. Upload CSV, XLSX, or XLS."), 400

    try:
        original_name = secure_filename(uploaded.filename)
        df = read_table(uploaded, original_name)
        original_rows, original_cols = df.shape
        original_missing = int(df.isna().sum().sum())
        duplicate_count = int(df.duplicated().sum())

        remove_duplicates = request.form.get("remove_duplicates", "true") == "true"
        missing_action = request.form.get("missing_action", "keep")
        normalize_columns = request.form.get("normalize_columns", "true") == "true"
        trim_cells = request.form.get("trim_cells", "true") == "true"
        restructure = request.form.get("restructure", "false") == "true"

        # Normalize headers first: trim, lowercase, replace spaces/punctuation with underscores.
        if normalize_columns:
            headers = (
                pd.Index(df.columns.astype(str))
                .str.strip()
                .str.lower()
                .str.replace(r"[^a-z0-9]+", "_", regex=True)
                .str.strip("_")
            )
            headers = [h if h else f"column_{i+1}" for i, h in enumerate(headers)]
            df.columns = make_unique_columns(headers)

        if trim_cells:
            for col in df.select_dtypes(include=["object", "string"]).columns:
                df[col] = df[col].map(lambda value: value.strip() if isinstance(value, str) else value)
                df[col] = df[col].replace("", pd.NA)

        if remove_duplicates:
            df = df.drop_duplicates()

        if missing_action == "drop_rows":
            df = df.dropna()
        elif missing_action == "fill_text":
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    if df[col].notna().any():
                        df[col] = df[col].fillna(df[col].median())
                else:
                    df[col] = df[col].fillna("Unknown")
        elif missing_action == "fill_median":
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]) and df[col].notna().any():
                    df[col] = df[col].fillna(df[col].median())

        # Restructure: place columns containing common ID/name/date fields first, preserving remaining order.
        if restructure:
            preferred = []
            keys = ("id", "name", "date", "email")
            for key in keys:
                preferred.extend([c for c in df.columns if key in str(c).lower() and c not in preferred])
            df = df[preferred + [c for c in df.columns if c not in preferred]]

        cleaned_missing = int(df.isna().sum().sum())
        cleaned_rows, cleaned_cols = df.shape
        preview_df = df.head(10).copy()
        preview_df = preview_df.astype(object).where(pd.notna(preview_df), "")
        preview = {
            "columns": [str(c) for c in preview_df.columns],
            "rows": preview_df.values.tolist()
        }

        file_id = str(uuid.uuid4())
        output = io.BytesIO()
        out_ext = "csv" if original_name.lower().endswith(".csv") else "xlsx"
        if out_ext == "csv":
            df.to_csv(output, index=False)
            mimetype = "text/csv"
            download_name = "cleaned_" + os.path.splitext(original_name)[0] + ".csv"
        else:
            df.to_excel(output, index=False, engine="openpyxl")
            mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            download_name = "cleaned_" + os.path.splitext(original_name)[0] + ".xlsx"
        output.seek(0)
        cleaned_files[file_id] = {
            "bytes": output.getvalue(),
            "mimetype": mimetype,
            "download_name": download_name
        }

        return jsonify({
            "file_id": file_id,
            "download_name": download_name,
            "original": {"rows": int(original_rows), "columns": int(original_cols), "missing": original_missing, "duplicates": duplicate_count},
            "cleaned": {"rows": int(cleaned_rows), "columns": int(cleaned_cols), "missing": cleaned_missing},
            "removed_duplicates": duplicate_count if remove_duplicates else 0,
            "preview": preview
        })
    except Exception as exc:
        return jsonify(error=f"Could not process this file. Check that it is a valid CSV or Excel file. Details: {str(exc)}"), 400

@app.route("/api/download/<file_id>")
def download_file(file_id):
    item = cleaned_files.get(file_id)
    if not item:
        return jsonify(error="This download has expired. Please clean the file again."), 404
    return send_file(
        io.BytesIO(item["bytes"]),
        mimetype=item["mimetype"],
        as_attachment=True,
        download_name=item["download_name"]
    )

@app.errorhandler(413)
def too_large(_error):
    return jsonify(error="File is too large. Please upload a file smaller than 20 MB."), 413

if __name__ == "__main__":
    app.run(debug=True)
