#!/bin/bash
# Daily outreach sender — runs automatically via cron at 9am
cd "/Users/dailylimmen/Documents/GEM connected"
echo "--- $(date) ---"
/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3 tools/bulk_send_emails.py --file .tmp/master_leads.csv
/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3 tools/send_followup.py
