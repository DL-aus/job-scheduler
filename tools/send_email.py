"""
Send a single personalized outreach email via Gmail SMTP.
Requires: GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env
Run: python tools/send_email.py --to agent@email.com --first Jane --company "Ray White" --suburb Mosman
"""

import argparse
import csv
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
REPLY_TO = os.getenv("REPLY_TO", "")
LOG_FILE = os.path.join(BASE_DIR, ".tmp", "email_log.csv")

SUBJECT_TEMPLATE = "GEM Outdoor X {company}"

BODY_TEMPLATE = """Hi {first_name},

Most properties hit the market with a garden that looks like it's been on a six-month holiday.

My name's Will Nicholls and I run GEM Outdoor. We go in before the campaign and fix that. Rather than coordinating multiple trades, we handle everything in one visit:

• Garden tidy-ups — mowing, edging, hedge trimming, and general cleanup
• Pressure washing — driveways, paths, fences, and outdoor surfaces
• House washing — exterior soft washes to remove dirt, mould, and cobwebs
• Window cleaning — crystal-clear results ready for listing photos

One team, one booking, one less thing on your plate.

Reply to this email and I can give you a ring. We work all over the Eastern Suburbs so I'm happy to swing by for a chat.

Thanks for reading, {first_name}

Kind regards,
Will Nicholls
GEM - Garden & Exterior Maintenance
admin@gemoutdoor.net
0408493845
"""


def send_email(to, first_name, company, suburb, sender_name, sender_phone, sender_business, dry_run=False):
    subject = SUBJECT_TEMPLATE.format(suburb=suburb, first_name=first_name, company=company)
    body = BODY_TEMPLATE.format(
        first_name=first_name,
        company=company,
        suburb=suburb,
        sender_name=sender_name,
        sender_phone=sender_phone,
        sender_business=sender_business
    )

    if dry_run:
        print(f"\n[DRY RUN] Would send to: {to}")
        print(f"Subject: {subject}")
        print(f"Body:\n{body}")
        log_result(to, first_name, company, suburb, "DRY_RUN")
        return

    msg = MIMEMultipart()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to
    msg["Subject"] = subject
    if REPLY_TO:
        msg["Reply-To"] = REPLY_TO
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, to, msg.as_string())
        print(f"Sent to {first_name} at {to}")
        log_result(to, first_name, company, suburb, "SENT")
    except Exception as e:
        print(f"Failed to send to {to}: {e}")
        log_result(to, first_name, company, suburb, f"FAILED: {e}")


def log_result(to, first_name, company, suburb, status):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "email", "first_name", "company", "suburb", "status"])
        writer.writerow([datetime.now().isoformat(), to, first_name, company, suburb, status])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", required=True)
    parser.add_argument("--first", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--suburb", required=True)
    parser.add_argument("--sender-name", default=os.getenv("SENDER_NAME", "Your Name"))
    parser.add_argument("--sender-phone", default=os.getenv("SENDER_PHONE", "0400 000 000"))
    parser.add_argument("--sender-business", default=os.getenv("SENDER_BUSINESS", "Your Gardening Business"))
    parser.add_argument("--dry-run", action="store_true", help="Preview without sending")
    args = parser.parse_args()

    send_email(
        to=args.to,
        first_name=args.first,
        company=args.company,
        suburb=args.suburb,
        sender_name=args.sender_name,
        sender_phone=args.sender_phone,
        sender_business=args.sender_business,
        dry_run=args.dry_run
    )
