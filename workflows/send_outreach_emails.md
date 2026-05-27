# Workflow: Send Personalized Outreach Emails

## Objective
Send individual, personalized emails to real estate agent leads on behalf of a gardening company. Goal: establish a referral partnership (they sell house, we fix garden).

## Inputs
- Leads list (from Google Sheets or .tmp/leads.csv)
- Sender Gmail account credentials
- Email template (see below)

## Tools to Use
1. `tools/send_email.py` — sends one email at a time via Gmail SMTP

## Personalization Variables
- {first_name} — agent's first name
- {company} — their agency name
- {suburb} — their suburb

## Email Template
Subject: Partnership idea for your {suburb} listings, {first_name}

Body:
Hi {first_name},

I came across {company} and was impressed by your work in {suburb}.

I run a gardening and landscaping business in Sydney, and I wanted to reach out about a simple idea: whenever you list a property, I can step in to get the garden looking its best before open homes.

A well-presented garden can add real value on inspection day — and it's one less thing you and your vendors need to worry about.

I'd love to offer a free garden assessment for your next listing, no strings attached. If it works out, great — if not, no pressure.

Would you be open to a quick chat?

Best,
[Your name]
[Your phone]
[Your business name]

---

## Steps
1. Load leads from sheet or CSV
2. For each lead with a valid email:
   a. Personalise the template
   b. Send via `send_email.py`
   c. Log sent status to `.tmp/email_log.csv`
3. Wait at least 5 days before follow-up
4. For MISSING emails: skip and flag for manual outreach via LinkedIn

## Rules
- Never send to the same email twice in one campaign
- Send max 30 emails per day to avoid spam filters
- Always personalise — never send a generic blast
