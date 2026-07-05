"""
Tulivo Digital – Weekly Report Orchestrator

Every Monday this script:
  1. Researches the web and writes the full strategic report
  2. Saves the report as a Google Doc
  3. POSTs to a GoHighLevel workflow webhook — GHL then emails your tagged clients

Environment variables (.env or GitHub Secrets):
  ANTHROPIC_API_KEY        – Anthropic API key
  GHL_WEBHOOK_URL          – Webhook URL from your GHL workflow (see README)
  GOOGLE_CREDENTIALS_FILE  – Path to Google service account JSON (optional)
  GOOGLE_CREDENTIALS       – Google service account JSON, base64-encoded (optional)
  FALLBACK_DOC_URL         – URL to use if Google Doc creation fails
"""

import os
import sys
import json
import base64
import requests
from datetime import date
from dotenv import load_dotenv  # FIX 1: load .env file

load_dotenv()


# ── Google Drive ──────────────────────────────────────────────────────────────

def create_google_doc(title: str, content: str) -> str:
    """Create a Google Doc and make it viewable by anyone with the link."""
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaInMemoryUpload
        from google.oauth2.service_account import Credentials

        creds_json = os.environ.get("GOOGLE_CREDENTIALS")
        creds_file = os.environ.get("GOOGLE_CREDENTIALS_FILE")

        if creds_json:
            info  = json.loads(base64.b64decode(creds_json).decode())
            creds = Credentials.from_service_account_info(
                info, scopes=["https://www.googleapis.com/auth/drive.file"]
            )
        elif creds_file and os.path.exists(creds_file):
            creds = Credentials.from_service_account_file(
                creds_file, scopes=["https://www.googleapis.com/auth/drive.file"]
            )
        else:
            raise EnvironmentError("No Google credentials found.")

        service = build("drive", "v3", credentials=creds)
        media   = MediaInMemoryUpload(content.encode(), mimetype="text/plain", resumable=False)
        file    = service.files().create(
            body={"name": title, "mimeType": "application/vnd.google-apps.document"},
            media_body=media,
            fields="id,webViewLink",
        ).execute()
        service.permissions().create(
            fileId=file["id"],
            body={"type": "anyone", "role": "reader"},
        ).execute()

        url = file.get("webViewLink", f"https://docs.google.com/document/d/{file['id']}/edit")
        print(f"  Google Doc created: {url}")
        return url

    except Exception as e:
        print(f"  Google Doc creation skipped: {e}")
        return ""


# ── Highlights ────────────────────────────────────────────────────────────────

def extract_highlights(report_text: str, n: int = 5) -> list:
    highlights = []
    in_summary = False
    for line in report_text.splitlines():
        if "EXECUTIVE SUMMARY" in line.upper():
            in_summary = True
            continue
        if in_summary:
            s = line.strip()
            if s.startswith(("•", "-", "*")) and len(s) > 2:
                clean = s.lstrip("•-* ").replace("**", "")
                clean = clean.split(" — ")[0].split(" – ")[0]
                if clean:
                    highlights.append(clean)
            if len(highlights) >= n:
                break
            if s.startswith("##") and highlights:
                break
    return highlights or ["Key AI and automation developments affecting SMEs this week."]


# ── GHL webhook ───────────────────────────────────────────────────────────────

def trigger_ghl_workflow(doc_url: str, highlights: list) -> None:
    """
    POST to the GHL Workflow webhook. GHL then emails all tagged clients.
    No API scopes needed — this is a simple unauthenticated webhook call.
    """
    webhook_url = os.environ.get("GHL_WEBHOOK_URL", "")
    if not webhook_url:
        print("  GHL_WEBHOOK_URL not set — skipping GHL notification.")
        return

    today   = date.today().strftime("%-d %B %Y")
    payload = {
        "report_date":  today,
        "doc_url":      doc_url,
        "highlight_1":  highlights[0] if len(highlights) > 0 else "",
        "highlight_2":  highlights[1] if len(highlights) > 1 else "",
        "highlight_3":  highlights[2] if len(highlights) > 2 else "",
        "highlight_4":  highlights[3] if len(highlights) > 3 else "",
        "highlight_5":  highlights[4] if len(highlights) > 4 else "",
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=15)
        resp.raise_for_status()
        print(f"  GHL workflow triggered (status {resp.status_code})")
    except Exception as e:
        print(f"  GHL webhook failed: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def validate_env():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Missing ANTHROPIC_API_KEY — check your .env file.")


def main():
    print("=" * 55)
    print("  Tulivo Digital – Weekly AI & Automation Report")
    print("=" * 55)

    validate_env()

    today    = date.today()
    title    = f"Tulivo Digital Weekly AI & Automation Report – {today.strftime('%-d %B %Y')}"
    filename = f"weekly-report-{today.strftime('%Y-%m-%d')}.md"

    # 1 — Generate report
    print("\n[1/3] Researching and writing report...")
    from generate_report import generate_report
    report_text = generate_report()
    with open(filename, "w") as f:
        f.write(report_text)
    print(f"  Saved: {filename}")

    # 2 — Create Google Doc
    print("\n[2/3] Creating Google Doc...")
    doc_url = create_google_doc(title, report_text)
    if not doc_url:
        doc_url = os.environ.get("FALLBACK_DOC_URL", "https://tulivodigital.com")
        print(f"  Using fallback URL: {doc_url}")

    # 3 — Trigger GHL workflow
    print("\n[3/3] Triggering GoHighLevel client email...")
    highlights = extract_highlights(report_text)
    trigger_ghl_workflow(doc_url, highlights)

    print("\n" + "=" * 55)
    print("  Done.")
    print("=" * 55)


if __name__ == "__main__":
    main()
