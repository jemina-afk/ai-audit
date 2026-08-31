# Tulivo Digital – Weekly AI & Automation Report

Automated pipeline that researches AI/automation news every Monday and emails
a strategic report to Jemina via GoHighLevel.

## Status

The GitHub Actions schedule (`.github/workflows/weekly_report.yml`, runs
every Monday 07:00 UTC) has run every week since 25 May 2026 and **failed
every single time** — 14/14 runs. The job exits immediately because the
required repository secrets were never configured, so no report has ever
actually been generated or sent.

## Required GitHub repository secrets

Set these at **Settings → Secrets and variables → Actions → Repository
secrets**. All three are currently unset:

| Secret | Required | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Generates the report via the Anthropic API (from console.anthropic.com) |
| `GHL_WEBHOOK_URL` | Yes | GoHighLevel workflow webhook that sends the email — without it the run now fails loudly instead of silently skipping the send |
| `GOOGLE_CREDENTIALS` | Optional | Base64-encoded Google service-account JSON, used to publish the report as a Google Doc. If omitted, `FALLBACK_DOC_URL` (set in the workflow to `https://tulivodigital.com`) is used instead |

`run_weekly.py` now validates `ANTHROPIC_API_KEY` and `GHL_WEBHOOK_URL` are
present before doing any work, and exits with a clear error naming which
secret is missing rather than failing silently.

## Local development

```
cp .env.example .env   # fill in the values above
pip install -r requirements.txt
python run_weekly.py
```

## Pipeline

1. `generate_report.py` — researches the web via the Anthropic API and
   writes the full report (`weekly-report-YYYY-MM-DD.md`)
2. `run_weekly.py` — orchestrates: generate → optionally publish to Google
   Docs → POST to the GHL webhook, which emails the report to tagged clients
3. GitHub Actions commits the saved report file back to the repository
