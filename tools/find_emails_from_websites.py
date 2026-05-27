"""
Find emails for contacts by scraping their company websites.
Groups contacts by domain so each website is only fetched once.
Run: python3 tools/find_emails_from_websites.py --file .tmp/contacts_raw.csv --out .tmp/contacts_with_emails.csv
"""

import argparse
import csv
import os
import re
import time
import urllib.request
import urllib.parse
from html.parser import HTMLParser
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
SKIP_DOMAINS = {"example.com", "sentry.io", "wixpress.com", "schema.org", "w3.org"}
SKIP_PREFIXES = ("noreply", "no-reply", "support", "help", "abuse", "postmaster", "webmaster", "bounce")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
}

SCRAPE_PATHS = ["/contact", "/about", "/our-team", "/team", "/people", "/agents", "/staff", ""]


class EmailParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.emails = set()

    def handle_starttag(self, tag, attrs):
        for attr, val in attrs:
            if not val:
                continue
            if attr == "href" and val.startswith("mailto:"):
                email = val[7:].split("?")[0].strip().lower()
                if email:
                    self.emails.add(email)
            else:
                for m in EMAIL_RE.findall(val):
                    self.emails.add(m.lower())

    def handle_data(self, data):
        for m in EMAIL_RE.findall(data):
            self.emails.add(m.lower())


def is_real_email(email):
    local, _, domain = email.partition("@")
    if domain in SKIP_DOMAINS:
        return False
    if local.startswith(SKIP_PREFIXES):
        return False
    if any(s in email for s in ["example", "youremail", "test@", "email@email"]):
        return False
    return True


def fetch(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception:
        return None


def extract_domain(website):
    if not website:
        return None
    try:
        parsed = urllib.parse.urlparse(website if "://" in website else "https://" + website)
        return parsed.netloc.lstrip("www.")
    except Exception:
        return None


def scrape_all_emails(domain):
    found = set()
    base = f"https://www.{domain}"
    for path in SCRAPE_PATHS:
        html = fetch(base + path)
        if html:
            parser = EmailParser()
            parser.feed(html)
            found |= {e for e in parser.emails if is_real_email(e) and domain in e}
        time.sleep(0.3)
    # Also try without www
    if not found:
        for path in SCRAPE_PATHS[:3]:
            html = fetch(f"https://{domain}{path}")
            if html:
                parser = EmailParser()
                parser.feed(html)
                found |= {e for e in parser.emails if is_real_email(e)}
            time.sleep(0.3)
    return found


def name_score(email, first, last):
    """Score how well an email matches a person's name."""
    local = email.split("@")[0].lower()
    f, l = first.lower(), last.lower()
    score = 0
    if f in local:
        score += 2
    if l in local:
        score += 2
    if local == f or local == f"{f}.{l}" or local == f"{f}{l[0]}" or local == f"{f[0]}{l}":
        score += 3
    return score


def best_email_for_person(emails, first, last):
    scored = [(name_score(e, first, last), e) for e in emails]
    scored.sort(reverse=True)
    if scored and scored[0][0] > 0:
        return scored[0][1], "confirmed"
    # Fall back to any non-generic email
    generic = {"info", "office", "admin", "hello", "contact", "enquiries", "sales", "reception"}
    non_generic = [e for e in emails if e.split("@")[0].split(".")[0] not in generic]
    if non_generic:
        return non_generic[0], "general"
    if emails:
        return list(emails)[0], "general"
    return None, None


def parse_name(full_name):
    parts = full_name.strip().split(" ", 1)
    return parts[0], parts[1] if len(parts) > 1 else ""


def run(in_path, out_path):
    with open(in_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Group by domain
    domain_to_rows = defaultdict(list)
    for row in rows:
        domain = extract_domain(row.get("website", ""))
        row["_domain"] = domain
        if domain:
            domain_to_rows[domain].append(row)

    domain_emails = {}
    total_domains = len(domain_to_rows)
    print(f"Scraping {total_domains} unique domains...")

    for i, (domain, _) in enumerate(domain_to_rows.items(), 1):
        print(f"  [{i}/{total_domains}] {domain}", end=" ", flush=True)
        emails = scrape_all_emails(domain)
        domain_emails[domain] = emails
        print(f"→ {len(emails)} emails found")
        time.sleep(1)

    # Match emails to people
    found_count = 0
    for row in rows:
        if row.get("email"):
            continue
        domain = row.get("_domain")
        if not domain or domain not in domain_emails:
            row["email"] = "MISSING"
            row["confidence"] = "missing"
            continue

        emails = domain_emails[domain]
        full_name = row.get("name", "")
        first, last = parse_name(full_name)
        email, confidence = best_email_for_person(emails, first, last)

        if email:
            row["email"] = email
            row["confidence"] = confidence
            found_count += 1
            print(f"  {full_name} → {email} [{confidence}]")
        else:
            row["email"] = "MISSING"
            row["confidence"] = "missing"

    # Write output
    fieldnames = ["record_id", "name", "company", "title", "website", "email", "confidence", "region", "basis"]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    missing = sum(1 for r in rows if r.get("email") == "MISSING")
    print(f"\nDone. {found_count} emails found. {missing} still missing.")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default=".tmp/contacts_raw.csv")
    parser.add_argument("--out", default=".tmp/contacts_with_emails.csv")
    args = parser.parse_args()
    run(args.file, args.out)
