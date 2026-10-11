CLEARDATA - SMART DATA CLEANER MVP

FEATURES
- Upload CSV, XLSX, or XLS files (maximum 20 MB)
- Detect duplicate rows and optionally remove them
- Detect missing values and optionally fill or drop them
- Normalize column names to lowercase_with_underscores
- Trim leading/trailing spaces in text cells
- Optionally place ID/name/date/email-like columns first
- Preview up to 10 cleaned rows
- Download the cleaned file in CSV or XLSX format

REQUIREMENTS
Python 3.10 or newer recommended.

RUN ON WINDOWS
1. Extract this ZIP file.
2. Open Command Prompt or PowerShell in the extracted smart_data_cleaner folder.
3. Create a virtual environment (recommended):
   py -m venv .venv
4. Activate it:
   PowerShell: .\.venv\Scripts\Activate.ps1
   Command Prompt: .venv\Scripts\activate.bat
5. Install packages:
   python -m pip install -r requirements.txt
6. Start the website:
   python app.py
7. Open this address in your browser:
   http://127.0.0.1:5000

NOTES
- This is a local MVP intended for coursework and demonstration, not a hardened production service.
- Uploaded data is processed by the local Flask app. Do not expose the development server publicly.
- The app stores the latest cleaned file in server memory; restarting the server clears downloads.
- For production, add authentication, CSRF protection, secure temporary-file handling, cleanup/expiry, stronger validation, and a production WSGI server.
- The .xls reader uses xlrd; Excel output is written as .xlsx.
