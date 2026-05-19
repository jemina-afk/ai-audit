"""
Tulivo Digital – Weekly Report Generator
Uses the Anthropic API with web search to research and write the report.
"""

import anthropic
import os
from datetime import date, timedelta

PROMPT_SYSTEM = """You are the Head of Research and Strategy for Tulivo Digital,
a digital transformation, AI automation and business growth consultancy serving SMEs.
You write weekly strategic intelligence briefings that are commercial, action-oriented
and focused on revenue generation for the consultancy. Avoid hype. Prioritise SME
use cases over enterprise ones."""

PROMPT_TEMPLATE = """
Research and compile the Tulivo Digital Weekly AI & Automation Opportunity Report.
Period covered: {week_start} to {week_end}.

Search the web for the most important developments from the past 7 days across:
- AI agents and agentic workflows
- Business process automation
- Customer service automation
- Lead generation and CRM automation
- Marketing automation and website technology
- Conversational AI and Voice AI
- AI-powered sales and recruitment tools
- Workflow automation (Make, Zapier, n8n)
- CRM platforms (HubSpot, GoHighLevel)
- AI models (Claude/Anthropic, OpenAI, Google Gemini, Microsoft Copilot)
- No-code and low-code platforms
- SME technology adoption and digital transformation trends
- UK government AI updates and regulations

Research at least: Reuters, Financial Times, TechCrunch, VentureBeat, Axios,
MIT Technology Review, OpenAI announcements, Anthropic announcements, Google AI
announcements, Microsoft AI announcements, UK government AI updates.

Then write the full report in this exact format:

---
# Tulivo Digital Weekly AI & Automation Opportunity Report
## {report_date} | Strategic Intelligence Briefing

---

## 1. EXECUTIVE SUMMARY
[5-10 bullet points: the week's most important developments]

---

## 2. TOP AI NEWS STORIES
[For each of the top 6-8 stories:]
### STORY N: [Headline]
**Source:** [Publication]
**Date:** [Date]
**Summary:** [150-250 words]
**Why it matters to SMEs:** [2-3 sentences]
**Why it matters to Tulivo Digital:** [2-3 sentences]

---

## 3. SERVICE OPPORTUNITIES FOR TULIVO DIGITAL
### New Services to Offer
[List with pricing estimates]

### Existing Services That Have Become More Valuable
[List]

### Industries Most Likely to Buy These Services Now
[Numbered list]

### Suggested Pricing Opportunities
[Table: Service | Setup Fee | Monthly Retainer]

---

## 4. CLIENT CONVERSATION STARTERS
### 10 Talking Points
### 10 LinkedIn Content Ideas
### 10 Networking Conversation Starters
### 5 Sales Outreach Angles

---

## 5. IMPLEMENTATION OPPORTUNITIES
[For each of 5-6 opportunities:]
- **Description:**
- **Implementation effort:**
- **Ideal client:**
- **Expected business outcome:**
- **Potential MRR:**

---

## 6. COMPETITIVE ADVANTAGE INSIGHTS
### What Competitors Are Likely Missing
### Underserved SME Opportunities
### Early Adopter Opportunities
### High-Growth Niches

---

## 7. ACTION PLAN
### Top 5 Actions This Week
### Top 5 Actions This Month
### Potential Partnership Opportunities

---

## SOURCES CONSULTED
[List all URLs researched]

---
*Compiled by Tulivo Digital Research & Strategy Team | {report_date}*
*Next report: Monday {next_report_date}*
"""


def generate_report() -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    today        = date.today()
    week_start   = (today - timedelta(days=7)).strftime("%-d %B %Y")
    week_end     = today.strftime("%-d %B %Y")
    report_date  = today.strftime("%-d %B %Y")
    next_monday  = (today + timedelta(days=7)).strftime("%-d %B %Y")

    user_message = PROMPT_TEMPLATE.format(
        week_start=week_start,
        week_end=week_end,
        report_date=report_date,
        next_report_date=next_monday,
    )

    messages = [{"role": "user", "content": user_message}]

    # Agentic loop — Claude searches the web and compiles the report
    while True:
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=8000,
            system=PROMPT_SYSTEM,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            break

        # If Claude used a tool, feed results back and continue
        if response.stop_reason == "tool_use":
            tool_results = [
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": getattr(block, "content", ""),
                }
                for block in response.content
                if block.type == "tool_use"
            ]
            if tool_results:
                messages.append({"role": "user", "content": tool_results})
        else:
            break

    # Extract the final text
    text = "".join(
        block.text for block in response.content if hasattr(block, "text")
    )
    return text


def save_report(text: str) -> str:
    today     = date.today()
    filename  = f"weekly-report-{today.strftime('%Y-%m-%d')}.md"
    with open(filename, "w") as f:
        f.write(text)
    print(f"Report saved: {filename}")
    return filename


if __name__ == "__main__":
    print("Generating weekly report...")
    report = generate_report()
    save_report(report)
    print("Done.")
