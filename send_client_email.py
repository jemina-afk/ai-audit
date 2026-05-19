"""
Tulivo Digital – GHL Client Broadcast
Sends a short branded weekly email to all GHL contacts tagged with
GHL_CLIENT_TAG, pointing them to the Google Doc report.
"""

import os
import requests
from datetime import date

BASE_URL = "https://services.leadconnectorhq.com"
HEADERS  = {
    "Authorization": f"Bearer {os.environ['GHL_API_KEY']}",
    "Version": "2021-07-28",
    "Content-Type": "application/json",
}


def get_tagged_contacts() -> list[dict]:
    """Return all contacts in the location that carry GHL_CLIENT_TAG."""
    tag         = os.environ["GHL_CLIENT_TAG"]
    location_id = os.environ["GHL_LOCATION_ID"]
    contacts    = []
    page        = 1

    while True:
        resp = requests.get(
            f"{BASE_URL}/contacts/",
            headers=HEADERS,
            params={"locationId": location_id, "tags": tag, "page": page, "limit": 100},
        )
        resp.raise_for_status()
        data  = resp.json()
        batch = data.get("contacts", [])
        contacts.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    print(f"Found {len(contacts)} contacts tagged '{tag}'")
    return contacts


def get_or_create_conversation(contact_id: str) -> str:
    location_id = os.environ["GHL_LOCATION_ID"]

    resp = requests.get(
        f"{BASE_URL}/conversations/search",
        headers=HEADERS,
        params={"locationId": location_id, "contactId": contact_id},
    )
    resp.raise_for_status()
    convos = resp.json().get("conversations", [])
    if convos:
        return convos[0]["id"]

    resp = requests.post(
        f"{BASE_URL}/conversations/",
        headers=HEADERS,
        json={"locationId": location_id, "contactId": contact_id},
    )
    resp.raise_for_status()
    return resp.json()["conversation"]["id"]


def build_client_email(first_name: str, doc_url: str, highlights: list[str]) -> tuple[str, str]:
    """Return (subject, html) for the client-facing email."""
    today   = date.today()
    display = today.strftime("%-d %B %Y")
    name    = first_name or "there"

    bullet_html = "\n".join(
        f"""
        <tr>
          <td style="padding: 10px 0; border-bottom: 1px solid #f0f0f0;">
            <span style="color:#e63946; font-weight:bold; margin-right:8px;">→</span>
            {h}
          </td>
        </tr>"""
        for h in highlights
    )

    subject = f"Your Weekly AI & Automation Intelligence Briefing – {display}"

    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:Arial,sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:30px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:8px;overflow:hidden;
                    box-shadow:0 2px 8px rgba(0,0,0,0.08);max-width:600px;width:100%;">

        <!-- Header -->
        <tr>
          <td style="background:#1d3557;padding:28px 36px;">
            <p style="margin:0;color:#a8c8e8;font-size:12px;letter-spacing:2px;
                      text-transform:uppercase;">Tulivo Digital</p>
            <h1 style="margin:6px 0 0;color:#ffffff;font-size:20px;font-weight:700;
                       line-height:1.3;">
              Weekly AI &amp; Automation<br>Intelligence Briefing
            </h1>
            <p style="margin:8px 0 0;color:#a8c8e8;font-size:13px;">{display}</p>
          </td>
        </tr>

        <!-- Intro -->
        <tr>
          <td style="padding:28px 36px 16px;">
            <p style="margin:0;font-size:15px;color:#333;line-height:1.6;">
              Hi {name},
            </p>
            <p style="margin:12px 0 0;font-size:15px;color:#333;line-height:1.6;">
              Your weekly AI and automation intelligence briefing is ready.
              This week's report covers the developments most likely to affect
              your business and create new opportunities — curated specifically
              for SMEs.
            </p>
          </td>
        </tr>

        <!-- Highlights -->
        <tr>
          <td style="padding:8px 36px 24px;">
            <p style="margin:0 0 12px;font-size:13px;font-weight:700;color:#1d3557;
                      text-transform:uppercase;letter-spacing:1px;">
              This week's highlights
            </p>
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="font-size:14px;color:#444;line-height:1.5;">
              {bullet_html}
            </table>
          </td>
        </tr>

        <!-- CTA -->
        <tr>
          <td align="center" style="padding:8px 36px 36px;">
            <a href="{doc_url}"
               style="display:inline-block;background:#e63946;color:#ffffff;
                      font-size:15px;font-weight:700;text-decoration:none;
                      padding:14px 36px;border-radius:6px;letter-spacing:0.3px;">
              Read the Full Report &rarr;
            </a>
            <p style="margin:16px 0 0;font-size:12px;color:#999;">
              Opens as a Google Doc — no login required.
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f8f9fa;padding:20px 36px;border-top:1px solid #eee;">
            <p style="margin:0;font-size:12px;color:#999;line-height:1.6;">
              You're receiving this because you're a Tulivo Digital client.
              This briefing is produced every Monday morning.<br>
              <a href="https://tulivodigital.com" style="color:#1d3557;">tulivodigital.com</a>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>

</body>
</html>
"""
    return subject, html


def send_to_contact(contact: dict, doc_url: str, highlights: list[str]) -> bool:
    contact_id = contact["id"]
    first_name = contact.get("firstName", "")
    email      = contact.get("email", "")

    if not email:
        print(f"  Skipping {contact_id} — no email address")
        return False

    subject, html = build_client_email(first_name, doc_url, highlights)

    try:
        conversation_id = get_or_create_conversation(contact_id)
        resp = requests.post(
            f"{BASE_URL}/conversations/messages",
            headers=HEADERS,
            json={
                "type": "Email",
                "contactId": contact_id,
                "conversationId": conversation_id,
                "subject": subject,
                "html": html,
                "emailFrom": f"Tulivo Digital <hello@{os.environ.get('SENDING_DOMAIN','tulivodigital.com')}>",
                "emailTo": email,
            },
        )
        resp.raise_for_status()
        print(f"  Sent to {email}")
        return True
    except Exception as e:
        print(f"  Failed for {email}: {e}")
        return False


def broadcast(doc_url: str, highlights: list[str]) -> None:
    """Send the client email to every tagged contact."""
    contacts = get_tagged_contacts()
    if not contacts:
        print("No contacts found — check GHL_CLIENT_TAG is set correctly.")
        return

    sent = sum(send_to_contact(c, doc_url, highlights) for c in contacts)
    print(f"\nBroadcast complete: {sent}/{len(contacts)} emails sent.")
