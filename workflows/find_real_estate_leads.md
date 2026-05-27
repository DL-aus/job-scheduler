# Workflow: Find Real Estate Agent Leads (Sydney, Non-Western)

## Objective
Build a list of real estate agents in Sydney (excluding Western Sydney) suitable for a gardening company partnership pitch. Output goes to Google Sheets.

## Target Suburbs
Focus on prestige and high-turnover areas:
- **Eastern Suburbs**: Bondi, Double Bay, Paddington, Woollahra, Randwick, Coogee, Bronte
- **Inner Sydney**: Surry Hills, Newtown, Glebe, Pyrmont, Redfern
- **Lower North Shore**: Mosman, Neutral Bay, Cremorne, Kirribilli, McMahons Point
- **Upper North Shore**: Gordon, Wahroonga, Turramurra, St Ives, Pymble
- **Northern Beaches**: Manly, Dee Why, Narrabeen, Avalon, Balgowlah
- **Inner West**: Balmain, Rozelle, Leichhardt, Annandale, Drummoyne
- **St George**: Kogarah, Hurstville, Rockdale

## Required Outputs Per Lead
- First name
- Last name
- Email address
- Company name
- Suburb
- Office address

## Tools to Use
1. `tools/search_leads.py` — finds agencies per suburb via web search
2. `tools/export_to_sheets.py` — pushes final list to Google Sheets

## Steps
1. Run `search_leads.py` for each target suburb
2. Deduplicate by email or full name + company
3. Filter out: property managers only, commercial-only agents, non-Sydney offices
4. Export clean list via `export_to_sheets.py`
5. Log any leads missing emails to `.tmp/missing_emails.csv` for manual follow-up

## Edge Cases
- If email not found: still include lead, mark email as MISSING
- If suburb is ambiguous (e.g. "Sydney CBD"): classify as Inner Sydney
- Skip agents whose websites clearly show Western Sydney focus (Parramatta, Blacktown, Penrith, Liverpool, Campbelltown)
