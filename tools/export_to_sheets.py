"""
Export leads list to Google Sheets.
Requires: credentials.json + token.json in project root (Google OAuth).
Run: python tools/export_to_sheets.py --file .tmp/leads.csv --sheet "GEM Leads"
"""

import argparse
import csv
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_credentials():
    creds = None
    token_path = os.path.join(BASE_DIR, "token.json")
    creds_path = os.path.join(BASE_DIR, "credentials.json")

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return creds


def load_csv(filepath):
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames


def create_or_find_sheet(service, sheet_name):
    sheets = service.spreadsheets().list().execute().get("files", [])
    for s in sheets:
        if s["name"] == sheet_name:
            return s["spreadsheetId"]

    body = {"properties": {"title": sheet_name}}
    result = service.spreadsheets().create(body=body).execute()
    return result["spreadsheetId"]


def push_to_sheets(filepath, sheet_name):
    rows, headers = load_csv(filepath)
    creds = get_credentials()
    service = build("sheets", "v4", credentials=creds)

    spreadsheet = service.spreadsheets().create(body={
        "properties": {"title": sheet_name}
    }).execute()
    spreadsheet_id = spreadsheet["spreadsheetId"]

    values = [list(headers)] + [[row.get(h, "") for h in headers] for row in rows]
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="A1",
        valueInputOption="RAW",
        body={"values": values}
    ).execute()

    print(f"Exported {len(rows)} leads to Google Sheets: {sheet_name}")
    print(f"Sheet ID: {spreadsheet_id}")
    print(f"URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to CSV file")
    parser.add_argument("--sheet", default="GEM Leads", help="Sheet name")
    args = parser.parse_args()
    push_to_sheets(args.file, args.sheet)
