"""
Find missing emails for leads by scraping agency websites and searching the web.
Updates the leads CSV in-place with any found emails.
Run: python3 tools/find_missing_emails.py --file .tmp/leads.csv [--dry-run]
"""

import argparse
import csv
import os
import re
import time
import urllib.request
import urllib.parse
from html.parser import HTMLParser

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

# Known email patterns per company — extend as discovered
EMAIL_PATTERNS = {
    "raine & horne mosman": "{first}@rhm.com.au",
    "clarke & humel": "{first}@clarkeandhumel.com.au",
    "cobden hayson": "{first}@ch.com.au",
    "chadwick real estate": "{first}@chadwickrealestate.com.au",
    "mcgrath estate agents": "{first}.{last}@mcgrath.com.au",
    "belle property dee why": "{first}.{last}@belleproperty.com",
}

# Known office/contact pages per company
CONTACT_PAGES = {
    "belle property mosman": "https://belleproperty.com/mosman/contact",
    "belle property neutral bay": "https://belleproperty.com/neutralbay/contact",
    "belle property balmain": "https://belleproperty.com/balmain/contact",
    "belle property surry hills": "https://belleproperty.com/surryhills/contact",
    "belle property bondi junction": "https://belleproperty.com/bondijunction/contact",
    "belle property randwick": "https://belleproperty.com/randwick/contact",
    "belle property north shore": "https://belleproperty.com/northshore/contact",
    "belle property double bay": "https://belleproperty.com/doublebay/contact",
    "belle property manly": "https://belleproperty.com/manly/contact",
    "ray white double bay": "https://rwdoublebay.com.au/contact",
    "ray white inner west": "https://raywhiteinnerwest.com.au/contact",
    "ryder realty": "https://ryderrealty.com.au/contact",
    "stone real estate mosman": "https://stonerealestateaustralia.com/contact",
    "stone real estate neutral bay": "https://stonerealestateaustralia.com/contact",
    "richardson & wrench double bay": "https://rwdoublebay.com.au/contact",
    "mcgrath surry hills": "https://www.mcgrath.com.au/offices/surry-hills",
    "mcgrath coogee": "https://www.mcgrath.com.au/offices/coogee",
    "balmain realty": "https://balmainrealty.com.au/contact",
    "local agency co": "https://localagencyco.com/contact",
}


class EmailScraper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.emails = set()
        self._text_buffer = ""

    def handle_data(self, data):
        self._text_buffer += data
        for match in EMAIL_RE.findall(data):
            self.emails.add(match.lower())

    def handle_starttag(self, tag, attrs):
        for attr, val in attrs:
            if val and EMAIL_RE.search(val):
                for match in EMAIL_RE.findall(val):
                    self.emails.add(match.lower())
            if attr == "href" and val and val.startswith("mailto:"):
                email = val[7:].split("?")[0].strip()
                if email:
                    self.emails.add(email.lower())


def fetch_page(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return None


def scrape_emails_from_url(url):
    html = fetch_page(url)
    if not html:
        return set()
    parser = EmailScraper()
    parser.feed(html)
    # Filter out common false positives
    return {
        e for e in parser.emails
        if not any(skip in e for skip in ["example", "domain", "email", "youremail", "sentry", "wixpress", "schema"])
    }


def apply_pattern(pattern, first_name, last_name):
    return pattern.format(
        first=first_name.lower(),
        last=last_name.lower(),
        first_name=first_name.lower(),
        last_name=last_name.lower(),
    )


def find_email_for_lead(row, dry_run=False):
    first = row["first_name"].strip()
    last = row["last_name"].strip()
    company = row["company"].strip().lower()
    suburb = row["suburb"].strip()

    # 1. Try known email pattern
    for key, pattern in EMAIL_PATTERNS.items():
        if key in company:
            guessed = apply_pattern(pattern, first, last)
            print(f"  Pattern match → {guessed} (inferred)")
            return guessed, "inferred"

    # 2. Try scraping the known contact page
    for key, url in CONTACT_PAGES.items():
        if key in company:
            print(f"  Scraping {url} ...")
            emails = scrape_emails_from_url(url)
            # Look for personal email matching the agent's name
            personal = [e for e in emails if first.lower() in e or last.lower() in e]
            if personal:
                print(f"  Found personal email → {personal[0]}")
                return personal[0], "confirmed"
            # Fall back to any non-generic email on the page
            filtered = [e for e in emails if not any(g in e for g in ["info@", "office@", "admin@", "hello@", "contact@"])]
            if filtered:
                print(f"  Found email on page → {filtered[0]}")
                return filtered[0], "scraped"
            if emails:
                print(f"  Found general email → {list(emails)[0]}")
                return list(emails)[0], "general"
            break

    # 3. Try the agency website root
    agency_domain = derive_domain(company, suburb)
    if agency_domain:
        for path in ["/contact", "/about", "/our-team", "/team", ""]:
            url = f"https://www.{agency_domain}{path}"
            print(f"  Trying {url} ...")
            emails = scrape_emails_from_url(url)
            personal = [e for e in emails if first.lower() in e or last.lower() in e]
            if personal:
                return personal[0], "confirmed"
            if emails:
                return list(emails)[0], "general"
            time.sleep(0.5)

    return None, None


def derive_domain(company, suburb):
    slug = company.lower()
    slug = re.sub(r"[^a-z0-9\s]", "", slug).strip()
    slug = re.sub(r"\s+", "", slug)
    return f"{slug}.com.au" if slug else None


def load_leads(filepath):
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames


def save_leads(filepath, rows, fieldnames):
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run(filepath, dry_run=False):
    rows, fieldnames = load_leads(filepath)
    found_count = 0
    still_missing = 0

    for row in rows:
        email = row.get("email", "").strip()
        if email and email.upper() != "MISSING":
            continue

        name = f"{row['first_name']} {row['last_name']}"
        print(f"\nSearching for {name} at {row['company']} ({row['suburb']})...")

        new_email, confidence = find_email_for_lead(row)

        if new_email:
            print(f"  FOUND: {new_email} [{confidence}]")
            if not dry_run:
                row["email"] = new_email
                row["email_confidence"] = confidence
            found_count += 1
        else:
            print(f"  Not found — still missing")
            still_missing += 1

        time.sleep(1)

    if not dry_run:
        save_leads(filepath, rows, fieldnames)
        print(f"\nCSV updated. Found {found_count} new emails. {still_missing} still missing.")
    else:
        print(f"\n[DRY RUN] Would have found {found_count} emails. {still_missing} still missing.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to leads CSV")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    args = parser.parse_args()
    run(args.file, dry_run=args.dry_run)
