"""
Send personalized emails to all leads in a CSV file.
Skips leads with MISSING email or already in email_log.csv.
Run: python tools/bulk_send_emails.py --file .tmp/leads.csv [--dry-run]
"""

import argparse
import csv
import os
import time
from send_email import send_email, LOG_FILE

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_PER_DAY = 10
BLACKLIST_FILE = os.path.join(BASE_DIR, ".tmp", "email_blacklist.txt")


def load_blacklist():
    blacklist = set()
    if os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, encoding="utf-8") as f:
            for line in f:
                email = line.strip().lower()
                if email:
                    blacklist.add(email)
    return blacklist


def load_already_sent():
    sent = set()
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("status") == "SENT":
                    sent.add(row["email"].lower())
    return sent


def run(filepath, dry_run=False):
    sender_name = os.getenv("SENDER_NAME", "Your Name")
    sender_phone = os.getenv("SENDER_PHONE", "0400 000 000")
    sender_business = os.getenv("SENDER_BUSINESS", "Your Gardening Business")

    already_sent = load_already_sent()
    blacklist = load_blacklist()
    sent_count = 0

    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if sent_count >= MAX_PER_DAY:
                print(f"\nDaily limit of {MAX_PER_DAY} reached. Run again tomorrow.")
                break

            email = row.get("email", "").strip()
            if not email or email.upper() == "MISSING":
                print(f"Skipping {row.get('first_name')} {row.get('last_name')} — no email")
                continue

            if email.lower() in blacklist:
                print(f"Skipping {email} — blacklisted")
                continue

            if email.lower() in already_sent:
                print(f"Skipping {email} — already sent")
                continue

            send_email(
                to=email,
                first_name=row.get("first_name", ""),
                company=row.get("company", ""),
                suburb=row.get("suburb", ""),
                sender_name=sender_name,
                sender_phone=sender_phone,
                sender_business=sender_business,
                dry_run=dry_run
            )
            sent_count += 1
            if not dry_run:
                time.sleep(2)

    print(f"\nDone. {sent_count} emails {'previewed' if dry_run else 'sent'}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to leads CSV")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(args.file, dry_run=args.dry_run)
