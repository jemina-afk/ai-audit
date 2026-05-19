"""
Tulivo Digital – Weekly Report Orchestrator

Every Monday this script:
  1. Researches the web and writes the full strategic report
  2. Saves the report as a Google Doc (via Google Drive API)
  3. Sends a short branded client email via GoHighLevel with a link to the Doc

Environment variables required (set in .env or GitHub Secrets):
  ANTHROPIC_API_KEY   – Anthropic API key
  GHL_API_KEY         – GoHighLevel Private Integration key
  GHL_LOCATION_ID     – GHL sub-account Location ID
  GHL_CLIENT_TAG      – Tag applied to contacts who should receive the report
                        e.g. "weekly-report" or "clients"
  GOOGLE_CREDENTIALS  – Google service account JSON (base64-encoded) OR
  GOOGLE_CREDENTIALS_FILE – path to service account JSON file
  SENDING_DOMAIN      – your email sending domain (default: tulivodigital.com)
"""

import os
import sys
import json
import base64
from datetime import date

# ── Google Drive ──────────────────────────────────────────────────────────────

def create_google_doc(title: str, content: str) -> str:
    """Upload content to Google Drive as a Google Doc. Returns the view URL."""
    try:
        from googleapiclient.discovery import build
        from google.oauth2.service_account import Credentials

        # Accept credentials as a base64 string (GitHub Secret) or a file path
        creds_json = os.environ.get("GOOGLE_CREDENTIALS")
        creds_file = os.environ.get("GOOGLE_CREDENTIALS_FILE")

        if creds_json:
            info = json.loads(base64.b64decode(creds_json).decode())
            creds = Credentials.from_service_account_info(
                info, scopes=["https://www.googleapis.com/auth/drive.file"]
            )
        elif creds_file:
            creds = Credentials.from_service_account_file(
                creds_file, scopes=["https://www.googleapis.com/auth/drive.file"]
            )
        else:
            raise EnvironmentError(
                "Set GOOGLE_CREDENTIALS or GOOGLE_CREDENTIALS_FILE to enable Google Doc creation."
            )

        service  = build("drive", "v3", credentials=creds)
        metadata = {"name": title, "mimeType": "application/vnd.google-apps.document"}
        media    = _media_upload(content)
        file     = (
            service.files()
            .create(body=metadata, media_body=media, fields="id,webViewLink")
            .execute()
        )

        # Make the doc readable by anyone with the link
        service.permissions().create(
            fileId=file["id"],
            body={"type": "anyone", "role": "reader"},
        ).execute()

        url = file.get("webViewLink", f"https://docs.google.com/document/d/{file['id']}/edit")
        print(f"Google Doc created: {url}")
        return url

    except ImportError:
        print("google-api-python-client not installed — skipping Google Doc creation.")
        return ""
    except EnvironmentError as e:
        print(f"Google credentials not configured: {e}")
        return ""


def _media_upload(content: str):
    """Return a MediaInMemoryUpload for plain text content."""
    from googleapiclient.http import MediaInMemoryUpload
    return MediaInMemoryUpload(content.encode("utf-8"), mimetype="text/plain", resumable=False)


# ── Highlights extraction ─────────────────────────────────────────────────────

def extract_highlights(report_text: str, n: int = 5) -> list[str]:
    """Pull the first n bullet points from the Executive Summary."""
    highlights = []
    in_summary = False

    for line in report_text.splitlines():
        if "EXECUTIVE SUMMARY" in line.upper():
            in_summary = True
            continue
        if in_summary:
            stripped = line.strip()
            # Bullet points start with • or -
            if stripped.startswith(("•", "-", "*")) and len(stripped) > 2:
                # Remove markdown bold markers and leading bullet
                clean = stripped.lstrip("•-* ").replace("**", "")
                # Trim at em-dash for conciseness
                clean = clean.split(" — ")[0].split(" – ")[0]
                if clean:
                    highlights.append(clean)
            # Stop after n bullets or at next section heading
            if len(highlights) >= n:
                break
            if stripped.startswith("##") and highlights:
                break

    return highlights or ["Key AI and automation developments affecting SMEs this week."]


# ── Main ──────────────────────────────────────────────────────────────────────

def validate_env():
    required = ["ANTHROPIC_API_KEY", "GHL_API_KEY", "GHL_LOCATION_ID", "GHL_CLIENT_TAG"]
    missing  = [v for v in required if not os.environ.get(v)]
    if missing:
        sys.exit(f"Missing environment variables: {', '.join(missing)}\nCheck your .env file.")


def main():
    print("=" * 55)
    print("  Tulivo Digital – Weekly AI & Automation Report")
    print("=" * 55)

    validate_env()

    today      = date.today()
    title      = f"Tulivo Digital Weekly AI & Automation Opportunity Report – {today.strftime('%-d %B %Y')}"
    filename   = f"weekly-report-{today.strftime('%Y-%m-%d')}.md"

    # Step 1 – Generate report
    print("\n[1/3] Researching and writing report...")
    from generate_report import generate_report
    report_text = generate_report()
    with open(filename, "w") as f:
        f.write(report_text)
    print(f"      Saved: {filename}")

    # Step 2 – Create Google Doc
    print("\n[2/3] Creating Google Doc...")
    doc_url = create_google_doc(title, report_text)

    # Fall back to a placeholder so the email still sends
    if not doc_url:
        doc_url = os.environ.get("FALLBACK_DOC_URL", "https://tulivodigital.com")
        print(f"      Using fallback URL: {doc_url}")

    # Step 3 – Broadcast client email via GHL
    print("\n[3/3] Sending client email via GoHighLevel...")
    highlights = extract_highlights(report_text)
    print(f"      Highlights: {len(highlights)} bullets extracted")

    from send_client_email import broadcast
    broadcast(doc_url, highlights)

    print("\n" + "=" * 55)
    print("  Done.")
    print("=" * 55)


if __name__ == "__main__":
    main()
