"""
Tulivo Digital – Weekly Report Orchestrator
Runs every Monday: generates the report then sends it via GoHighLevel.
"""

from generate_report import generate_report, save_report
from send_report import load_latest_report, get_contact_id, get_or_create_conversation, send_email, validate_env
import sys


def main():
    print("=== Tulivo Digital Weekly Report ===")

    # Step 1: validate environment variables before doing any work
    validate_env()

    # Step 2: generate fresh report via Anthropic API + web search
    print("\n[1/3] Researching and generating report...")
    report_text = generate_report()
    save_report(report_text)

    # Step 3: load and send via GoHighLevel
    print("\n[2/3] Preparing email...")
    subject, html = load_latest_report()

    print("\n[3/3] Sending via GoHighLevel...")
    contact_id      = get_contact_id()
    conversation_id = get_or_create_conversation(contact_id)
    send_email(conversation_id, contact_id, subject, html)

    print("\n=== Done. Report sent successfully. ===")


if __name__ == "__main__":
    main()
