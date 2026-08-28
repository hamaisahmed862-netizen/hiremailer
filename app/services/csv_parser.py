import csv
import io
import openpyxl


def parse_applicants_csv(file_bytes: bytes) -> list[dict]:
    """
    Expects a CSV with headers: name, role, email
    Returns a list of dicts like [{"name": "Ali", "role": "Backend Developer", "email": "ali@example.com"}, ...]
    """
    text = file_bytes.decode("utf-8-sig")  # handles Excel's BOM prefix too
    reader = csv.DictReader(io.StringIO(text))

    required_columns = {"name", "role", "email"}
    if not required_columns.issubset(set(reader.fieldnames or [])):
        raise ValueError(
            f"CSV must have columns: name, role, email. Found: {reader.fieldnames}"
        )

    applicants = []
    for row in reader:
        applicants.append({
            "name": row["name"].strip(),
            "role": row["role"].strip(),
            "email": row["email"].strip(),
        })

    return applicants


def parse_applicants_excel(file_bytes: bytes) -> list[dict]:
    """
    Expects an .xlsx file with headers in the first row: name, role, email
    (in any column order). Reads the first sheet only.
    """
    workbook = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True)
    sheet = workbook.active

    rows = sheet.iter_rows(values_only=True)
    headers = [str(h).strip().lower() if h else "" for h in next(rows)]

    required_columns = {"name", "role", "email"}
    if not required_columns.issubset(set(headers)):
        raise ValueError(
            f"Excel file must have columns: name, role, email. Found: {headers}"
        )

    name_idx = headers.index("name")
    role_idx = headers.index("role")
    email_idx = headers.index("email")

    applicants = []
    for row in rows:
        if row is None or all(cell is None for cell in row):
            continue  # skip blank rows
        applicants.append({
            "name": str(row[name_idx]).strip() if row[name_idx] else "",
            "role": str(row[role_idx]).strip() if row[role_idx] else "",
            "email": str(row[email_idx]).strip() if row[email_idx] else "",
        })

    return applicants


def parse_applicants_file(filename: str, file_bytes: bytes) -> list[dict]:
    """
    Dispatches to the right parser based on file extension.
    Supports .csv, .xlsx, .xls.
    """
    lower_name = filename.lower()
    if lower_name.endswith(".csv"):
        return parse_applicants_csv(file_bytes)
    elif lower_name.endswith(".xlsx") or lower_name.endswith(".xls"):
        return parse_applicants_excel(file_bytes)
    else:
        raise ValueError("Unsupported file type. Please upload a .csv or .xlsx file.")