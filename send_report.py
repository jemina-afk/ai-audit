"""
Tulivo Digital – Weekly Report Sender via GoHighLevel API
Reads the latest weekly report and sends it as an email via GHL.

Setup:
  1. Copy .env.example to .env and fill in your values
  2. pip install requests python-dotenv markdown
  3. python send_report.py
"""

import os
import glob
import sys
import markdown
import requests
from datetime import date
from dotenv import load_dotenv

load_dotenv()

GHL_API_KEY  = os.getenv("GHL_API_KEY")
LOCATION_ID  = os.getenv("GHL_LOCATION_ID")
TO_EMAIL     = os.getenv("REPORT_TO_EMAIL", "jemina@tulivodigital.com")
TO_NAME      = os.getenv("REPORT_TO_NAME", "Jemina")
FROM_NAME    = os.getenv("REPORT_FROM_NAME", "Tulivo Digital Research & Strategy")

BASE_URL = "https://services.leadconnectorhq.com"
HEADERS  = {
    "Authorization": f"Bearer {GHL_API_KEY}",
    "Version": "2021-07-28",
    "Content-Type": "application/json",
}


def load_latest_report() -> tuple[str, str]:
    """Return (subject_line, html_body) from the most recent report file."""
    reports = sorted(glob.glob("weekly-report-*.md"), reverse=True)
    if not reports:
        sys.exit("No weekly-report-*.md file found. Generate the report first.")

    path = reports[0]
    print(f"Loading report: {path}")

    with open(path, "r") as f:
        raw = f.read()

    # Strip the front-matter block (--- ... ---) before converting
    if raw.startswith("---"):
        end = raw.find("---", 3)
        raw = raw[end + 3:].lstrip()

    today = date.today().strftime("%-d %B %Y")
    subject = f"Tulivo Digital Weekly AI & Automation Opportunity Report – {today}"

    # Wrap converted HTML in a clean email-safe template
    body_html = markdown.markdown(raw, extensions=["tables", "fenced_code"])
    html = f"""
    <html>
    <head>
      <style>
        body {{ font-family: Arial, sans-serif; font-size: 14px; color: #1a1a1a;
               max-width: 780px; margin: 0 auto; padding: 24px; }}
        h1 {{ color: #0d0d0d; border-bottom: 2px solid #e63946; padding-bottom: 8px; }}
        h2 {{ color: #1d3557; margin-top: 32px; }}
        h3 {{ color: #457b9d; }}
        table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
        th {{ background: #1d3557; color: #fff; padding: 8px 12px; text-align: left; }}
        td {{ padding: 8px 12px; border-bottom: 1px solid #ddd; }}
        tr:nth-child(even) {{ background: #f8f9fa; }}
        hr {{ border: none; border-top: 1px solid #ddd; margin: 24px 0; }}
        code {{ background: #f1f3f5; padding: 2px 5px; border-radius: 3px;
                font-size: 13px; }}
        blockquote {{ border-left: 4px solid #e63946; margin: 0; padding-left: 16px;
                      color: #555; }}
        a {{ color: #e63946; }}
        .footer {{ margin-top: 40px; padding-top: 16px; border-top: 1px solid #ddd;
                   font-size: 12px; color: #888; }}
      </style>
    </head>
    <body>
      {body_html}
      <div class="footer">
        This report was automatically generated and sent by Tulivo Digital's
        AI Research &amp; Strategy system every Monday at 07:00 UK time.
      </div>
    </body>
    </html>
    """
    return subject, html


def get_contact_id() -> str:
    """Look up the contact ID for the recipient email in GHL."""
    resp = requests.get(
        f"{BASE_URL}/contacts/search",
        headers=HEADERS,
        params={"locationId": LOCATION_ID, "email": TO_EMAIL},
    )
    resp.raise_for_status()
    contacts = resp.json().get("contacts", [])

    if contacts:
        cid = contacts[0]["id"]
        print(f"Found existing contact: {cid}")
        return cid

    # Contact doesn't exist – create it
    print(f"Contact not found, creating: {TO_EMAIL}")
    resp = requests.post(
        f"{BASE_URL}/contacts/",
        headers=HEADERS,
        json={
            "locationId": LOCATION_ID,
            "email": TO_EMAIL,
            "firstName": TO_NAME,
        },
    )
    resp.raise_for_status()
    cid = resp.json()["contact"]["id"]
    print(f"Created contact: {cid}")
    return cid


def get_or_create_conversation(contact_id: str) -> str:
    """Return an existing conversation ID or create a new one."""
    resp = requests.get(
        f"{BASE_URL}/conversations/search",
        headers=HEADERS,
        params={"locationId": LOCATION_ID, "contactId": contact_id},
    )
    resp.raise_for_status()
    convos = resp.json().get("conversations", [])

    if convos:
        cid = convos[0]["id"]
        print(f"Using existing conversation: {cid}")
        return cid

    resp = requests.post(
        f"{BASE_URL}/conversations/",
        headers=HEADERS,
        json={"locationId": LOCATION_ID, "contactId": contact_id},
    )
    resp.raise_for_status()
    cid = resp.json()["conversation"]["id"]
    print(f"Created conversation: {cid}")
    return cid


def send_email(conversation_id: str, contact_id: str, subject: str, html: str):
    """Send the email via GHL Conversations API."""
    payload = {
        "type": "Email",
        "contactId": contact_id,
        "conversationId": conversation_id,
        "subject": subject,
        "html": html,
        "emailFrom": f"{FROM_NAME} <noreply@{os.getenv('SENDING_DOMAIN', 'tulivodigital.com')}>",
        "emailTo": TO_EMAIL,
    }
    resp = requests.post(
        f"{BASE_URL}/conversations/messages",
        headers=HEADERS,
        json=payload,
    )

    if resp.status_code not in (200, 201):
        print(f"Send failed [{resp.status_code}]: {resp.text}")
        resp.raise_for_status()

    msg_id = resp.json().get("messageId", resp.json().get("id", "unknown"))
    print(f"Email sent successfully. Message ID: {msg_id}")
    return msg_id


def validate_env():
    missing = [v for v in ("GHL_API_KEY", "GHL_LOCATION_ID") if not os.getenv(v)]
    if missing:
        sys.exit(
            f"Missing environment variables: {', '.join(missing)}\n"
            "Copy .env.example to .env and fill in your values."
        )


if __name__ == "__main__":
    validate_env()
    subject, html     = load_latest_report()
    contact_id        = get_contact_id()
    conversation_id   = get_or_create_conversation(contact_id)
    send_email(conversation_id, contact_id, subject, html)
    print("Done.")
