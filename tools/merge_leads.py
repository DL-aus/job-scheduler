"""
Merge leads.csv and contacts_with_emails.csv into a single master_leads.csv.
Run: python3 tools/merge_leads.py
"""

import csv
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEADS_FILE = os.path.join(BASE_DIR, ".tmp", "leads.csv")
CONTACTS_FILE = os.path.join(BASE_DIR, ".tmp", "contacts_with_emails.csv")
MASTER_FILE = os.path.join(BASE_DIR, ".tmp", "master_leads.csv")

FIELDNAMES = ["first_name", "last_name", "email", "company", "suburb", "email_confidence"]

SKIP_CONFIDENCE = {"missing"}
GENERIC_PREFIXES = {"info", "office", "admin", "hello", "contact", "enquiries", "sales", "reception"}


def is_sendable(row):
    email = row.get("email", "").strip()
    if not email or email.upper() == "MISSING":
        return False
    confidence = row.get("email_confidence", "").lower()
    if confidence in SKIP_CONFIDENCE:
        return False
    return True


def load_leads():
    rows = []
    if not os.path.exists(LEADS_FILE):
        return rows
    with open(LEADS_FILE, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "first_name": r.get("first_name", "").strip(),
                "last_name": r.get("last_name", "").strip(),
                "email": r.get("email", "").strip().lower(),
                "company": r.get("company", "").strip(),
                "suburb": r.get("suburb", "").strip(),
                "email_confidence": r.get("email_confidence", "").strip(),
            })
    return rows


def load_contacts():
    rows = []
    if not os.path.exists(CONTACTS_FILE):
        return rows
    with open(CONTACTS_FILE, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            name = r.get("name", "").strip()
            parts = name.split(" ", 1)
            first = parts[0] if parts else ""
            last = parts[1] if len(parts) > 1 else ""
            rows.append({
                "first_name": first,
                "last_name": last,
                "email": r.get("email", "").strip().lower(),
                "company": r.get("company", "").strip(),
                "suburb": r.get("region", "").strip(),
                "email_confidence": r.get("confidence", "").strip(),
            })
    return rows


def run():
    leads = load_leads()
    contacts = load_contacts()
    all_rows = leads + contacts

    seen_emails = set()
    merged = []
    for row in all_rows:
        if not is_sendable(row):
            continue
        email = row["email"]
        if email in seen_emails:
            continue
        seen_emails.add(email)
        merged.append(row)

    os.makedirs(os.path.dirname(MASTER_FILE), exist_ok=True)
    with open(MASTER_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(merged)

    confirmed = sum(1 for r in merged if r["email_confidence"] == "confirmed")
    inferred = sum(1 for r in merged if r["email_confidence"] == "inferred")
    general = sum(1 for r in merged if r["email_confidence"] == "general")
    print(f"Master list: {len(merged)} leads total")
    print(f"  {confirmed} confirmed  |  {inferred} inferred  |  {general} general")
    print(f"Saved to {MASTER_FILE}")


if __name__ == "__main__":
    run()
