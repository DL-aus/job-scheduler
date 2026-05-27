"""
Send follow-up emails to leads who received an initial outreach 5+ days ago but no follow-up yet.
Reads email_log.csv to find eligible leads, skips anyone already followed up.
Run: python3 tools/send_followup.py [--dry-run]
"""

import argparse
import csv
import os
import smtplib
import time
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
REPLY_TO = os.getenv("REPLY_TO", "")
LOG_FILE = os.path.join(BASE_DIR, ".tmp", "email_log.csv")
BLACKLIST_FILE = os.path.join(BASE_DIR, ".tmp", "email_blacklist.txt")

MAX_PER_DAY = 5
FOLLOWUP_DELAY_DAYS = 5

SUBJECT = "Following up — GEM Outdoor"

BODY_TEMPLATE = """Hi {first_name},

Just wanted to make sure my last message didn't get buried — no stress if the timing isn't right.

If you ever have a property that needs a quick exterior tidy before going to market, we're easy to work with and fast to turn around.

Will
GEM Outdoor | 0408493845
"""


def load_blacklist():
    blacklist = set()
    if os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, encoding="utf-8") as f:
            for line in f:
                email = line.strip().lower()
                if email:
                    blacklist.add(email)
    return blacklist


def load_log():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def get_eligible(log_rows, blacklist):
    cutoff = datetime.now() - timedelta(days=FOLLOWUP_DELAY_DAYS)

    already_followed_up = {
        row["email"].lower()
        for row in log_rows
        if row.get("status") in ("FOLLOWUP_SENT", "FOLLOWUP_DRY_RUN")
    }

    seen = set()
    eligible = []
    for row in log_rows:
        if row.get("status") != "SENT":
            continue
        email = row.get("email", "").lower()
        if not email or email in seen:
            continue
        seen.add(email)
        if email in blacklist:
            continue
        if email in already_followed_up:
            continue
        try:
            sent_at = datetime.fromisoformat(row["timestamp"])
        except Exception:
            continue
        if sent_at <= cutoff:
            eligible.append(row)

    return eligible


def log_result(email, first_name, company, suburb, status):
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "email", "first_name", "company", "suburb", "status"])
        writer.writerow([datetime.now().isoformat(), email, first_name, company, suburb, status])


def send_followup(to, first_name, company, suburb, dry_run=False):
    body = BODY_TEMPLATE.format(first_name=first_name)

    if dry_run:
        print(f"[DRY RUN] Would follow up with: {first_name} <{to}>")
        log_result(to, first_name, company, suburb, "FOLLOWUP_DRY_RUN")
        return

    msg = MIMEMultipart()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to
    msg["Subject"] = SUBJECT
    if REPLY_TO:
        msg["Reply-To"] = REPLY_TO
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, to, msg.as_string())
        print(f"Follow-up sent to {first_name} at {to}")
        log_result(to, first_name, company, suburb, "FOLLOWUP_SENT")
    except Exception as e:
        print(f"Failed to send follow-up to {to}: {e}")
        log_result(to, first_name, company, suburb, f"FOLLOWUP_FAILED: {e}")


def run(dry_run=False):
    blacklist = load_blacklist()
    log_rows = load_log()
    eligible = get_eligible(log_rows, blacklist)

    if not eligible:
        print("No follow-ups due today.")
        return

    print(f"{len(eligible)} follow-up(s) due. Sending up to {MAX_PER_DAY} today.")
    sent = 0
    for row in eligible:
        if sent >= MAX_PER_DAY:
            print(f"Daily limit of {MAX_PER_DAY} reached.")
            break
        send_followup(
            to=row["email"],
            first_name=row.get("first_name", ""),
            company=row.get("company", ""),
            suburb=row.get("suburb", ""),
            dry_run=dry_run,
        )
        sent += 1
        if not dry_run:
            time.sleep(2)

    print(f"\nDone. {sent} follow-up(s) {'previewed' if dry_run else 'sent'}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
