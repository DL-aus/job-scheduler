"""
Scrape real estate agent listings from realestate.com.au across Sydney suburbs.
Outputs a CSV of new leads (excluding already-known contacts).
Run: python3 tools/scrape_rea_agents.py --out .tmp/new_leads.csv
"""

import csv
import json
import os
import re
import time
import urllib.request
import urllib.parse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SUBURBS = [
    # Eastern Suburbs
    ("bondi-beach", "NSW", "2026"),
    ("bondi-junction", "NSW", "2022"),
    ("double-bay", "NSW", "2028"),
    ("rose-bay", "NSW", "2029"),
    ("vaucluse", "NSW", "2030"),
    ("bellevue-hill", "NSW", "2023"),
    ("edgecliff", "NSW", "2027"),
    ("woollahra", "NSW", "2025"),
    ("paddington", "NSW", "2021"),
    ("randwick", "NSW", "2031"),
    ("coogee", "NSW", "2034"),
    ("clovelly", "NSW", "2031"),
    ("bronte", "NSW", "2024"),
    ("maroubra", "NSW", "2035"),
    ("kingsford", "NSW", "2032"),
    # Inner Sydney
    ("surry-hills", "NSW", "2010"),
    ("darlinghurst", "NSW", "2010"),
    ("pyrmont", "NSW", "2009"),
    ("glebe", "NSW", "2037"),
    ("newtown", "NSW", "2042"),
    ("redfern", "NSW", "2016"),
    ("chippendale", "NSW", "2008"),
    ("alexandria", "NSW", "2015"),
    # Lower North Shore
    ("mosman", "NSW", "2088"),
    ("neutral-bay", "NSW", "2089"),
    ("cremorne", "NSW", "2090"),
    ("kirribilli", "NSW", "2061"),
    ("cammeray", "NSW", "2062"),
    ("crows-nest", "NSW", "2065"),
    ("st-leonards", "NSW", "2065"),
    ("waverton", "NSW", "2060"),
    # Upper North Shore
    ("turramurra", "NSW", "2074"),
    ("wahroonga", "NSW", "2076"),
    ("st-ives", "NSW", "2075"),
    ("pymble", "NSW", "2073"),
    ("gordon", "NSW", "2072"),
    ("killara", "NSW", "2071"),
    ("lindfield", "NSW", "2070"),
    ("roseville", "NSW", "2069"),
    ("chatswood", "NSW", "2067"),
    ("lane-cove", "NSW", "2066"),
    ("willoughby", "NSW", "2068"),
    # Northern Beaches
    ("manly", "NSW", "2095"),
    ("freshwater", "NSW", "2096"),
    ("dee-why", "NSW", "2099"),
    ("collaroy", "NSW", "2097"),
    ("narrabeen", "NSW", "2101"),
    ("mona-vale", "NSW", "2103"),
    ("avalon-beach", "NSW", "2107"),
    ("palm-beach", "NSW", "2108"),
    ("newport", "NSW", "2106"),
    ("warriewood", "NSW", "2102"),
    # Inner West
    ("balmain", "NSW", "2041"),
    ("rozelle", "NSW", "2039"),
    ("leichhardt", "NSW", "2040"),
    ("annandale", "NSW", "2038"),
    ("marrickville", "NSW", "2204"),
    ("petersham", "NSW", "2049"),
    ("stanmore", "NSW", "2048"),
    ("dulwich-hill", "NSW", "2203"),
    ("lilyfield", "NSW", "2040"),
    # St George / Sutherland
    ("hurstville", "NSW", "2220"),
    ("kogarah", "NSW", "2217"),
    ("rockdale", "NSW", "2216"),
    ("cronulla", "NSW", "2230"),
    ("sutherland", "NSW", "2232"),
    ("miranda", "NSW", "2228"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
}


def fetch(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  Fetch error: {e}")
        return None


def extract_json_data(html):
    """Pull embedded JSON from realestate.com.au page scripts."""
    patterns = [
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        r'window\.__INITIAL_STATE__\s*=\s*({.*?});\s*</script>',
        r'"agents"\s*:\s*(\[.*?\])',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                continue
    return None


def parse_agents_from_json(data, suburb_label):
    agents = []
    if not isinstance(data, dict):
        return agents

    # Walk the JSON tree looking for agent objects
    raw = json.dumps(data)
    agent_blocks = re.findall(r'"agentName"\s*:\s*"([^"]+)".*?"agencyName"\s*:\s*"([^"]+)"', raw)
    for name, agency in agent_blocks:
        parts = name.strip().split(" ", 1)
        first = parts[0] if parts else ""
        last = parts[1] if len(parts) > 1 else ""
        agents.append({
            "first_name": first,
            "last_name": last,
            "email": "MISSING",
            "company": agency.strip(),
            "suburb": suburb_label,
            "office_address": "MISSING",
            "email_confidence": "missing",
            "source": "realestate.com.au",
        })
    return agents


def parse_agents_from_html(html, suburb_label):
    """Fallback: regex parse agent cards from raw HTML."""
    agents = []

    name_pattern = re.compile(r'"agentName"\s*:\s*"([^"]+)"')
    agency_pattern = re.compile(r'"agencyName"\s*:\s*"([^"]+)"')
    email_pattern = re.compile(r'"email"\s*:\s*"([^"@]+@[^"]+)"')

    names = name_pattern.findall(html)
    agencies = agency_pattern.findall(html)
    emails = email_pattern.findall(html)

    for i, name in enumerate(names):
        parts = name.strip().split(" ", 1)
        first = parts[0]
        last = parts[1] if len(parts) > 1 else ""
        agency = agencies[i] if i < len(agencies) else "MISSING"
        email = emails[i] if i < len(emails) else "MISSING"
        confidence = "confirmed" if email != "MISSING" else "missing"

        agents.append({
            "first_name": first,
            "last_name": last,
            "email": email,
            "company": agency,
            "suburb": suburb_label,
            "office_address": "MISSING",
            "email_confidence": confidence,
            "source": "realestate.com.au",
        })
    return agents


def scrape_suburb(suburb_slug, state, postcode):
    suburb_label = suburb_slug.replace("-", " ").title()
    url = f"https://www.realestate.com.au/find-agent/list-1?locations%5B%5D={urllib.parse.quote(suburb_slug)}+{state}+{postcode}"
    print(f"  {suburb_label} → {url}")

    html = fetch(url)
    if not html:
        return []

    data = extract_json_data(html)
    if data:
        agents = parse_agents_from_json(data, suburb_label)
        if agents:
            return agents

    return parse_agents_from_html(html, suburb_label)


def load_existing_names(filepath):
    known = set()
    if os.path.exists(filepath):
        with open(filepath, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key = f"{row['first_name'].lower()}_{row['last_name'].lower()}_{row['company'].lower()}"
                known.add(key)
    return known


def dedupe(agents, existing_keys):
    seen = set()
    out = []
    for a in agents:
        key = f"{a['first_name'].lower()}_{a['last_name'].lower()}_{a['company'].lower()}"
        if key in existing_keys or key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out


def run(out_path, existing_path=None):
    existing_keys = load_existing_names(existing_path) if existing_path else set()
    all_agents = []

    for suburb_slug, state, postcode in SUBURBS:
        print(f"\nScraping {suburb_slug.replace('-', ' ').title()}...")
        agents = scrape_suburb(suburb_slug, state, postcode)
        print(f"  Found {len(agents)} agents")
        all_agents.extend(agents)
        time.sleep(1.5)

    deduped = dedupe(all_agents, existing_keys)
    print(f"\nTotal unique new agents found: {len(deduped)}")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fieldnames = ["first_name", "last_name", "email", "company", "suburb", "office_address", "email_confidence", "source"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(deduped)

    print(f"Saved to {out_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=".tmp/new_leads.csv", help="Output CSV path")
    parser.add_argument("--existing", default=".tmp/leads.csv", help="Existing leads CSV to dedupe against")
    args = parser.parse_args()
    run(args.out, existing_path=args.existing)
