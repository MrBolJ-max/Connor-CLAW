#!/usr/bin/env python3
"""
SYN Systems — New Client Onboarding CLI
Interactive terminal wizard to onboard a new client in minutes.

Usage: python scripts/new_client.py
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

CYAN   = "\033[0;36m"
GREEN  = "\033[0;32m"
YELLOW = "\033[1;33m"
RED    = "\033[0;31m"
BOLD   = "\033[1m"
NC     = "\033[0m"

INDUSTRIES = [
    "B2B Services",
    "Healthcare",
    "SaaS",
    "Technology",
    "Real Estate",
    "E-commerce",
]

AGENTS = {
    "1": ("ava",            "AVA — AI Receptionist (24/7 voice, bookings, payments)"),
    "2": ("lead_capture",   "Lead Capture Agent (multi-channel qualification)"),
    "3": ("sales_followup", "Sales Follow-Up Agent (emails, objections, close)"),
    "4": ("content_seo",    "Content & SEO Agent (blog, LinkedIn, ads)"),
    "5": ("ai_auditor",     "AI Auditor (invoices, cash flow, discrepancies)"),
}


def prompt(msg: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    value = input(f"{CYAN}  → {msg}{hint}: {NC}").strip()
    return value if value else default


def choose_industry() -> str:
    print(f"\n{BOLD}  Industries:{NC}")
    for i, ind in enumerate(INDUSTRIES, 1):
        print(f"    {i}. {ind}")
    while True:
        choice = input(f"{CYAN}  → Select industry (1-{len(INDUSTRIES)}): {NC}").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(INDUSTRIES):
                return INDUSTRIES[idx]
        except ValueError:
            pass
        print(f"{RED}  Invalid choice — enter a number 1-{len(INDUSTRIES)}{NC}")


def choose_agents() -> list[str]:
    print(f"\n{BOLD}  Available Agents:{NC}")
    for key, (_, label) in AGENTS.items():
        print(f"    {key}. {label}")
    print(f"    A. All agents")
    choice = input(f"{CYAN}  → Select agents (e.g. 1,2,3 or A for all): {NC}").strip().upper()

    if choice == "A":
        return [v[0] for v in AGENTS.values()]

    selected = []
    for c in choice.split(","):
        c = c.strip()
        if c in AGENTS:
            selected.append(AGENTS[c][0])
    return selected or [AGENTS["1"][0], AGENTS["2"][0]]


def collect_documents() -> list[dict]:
    print(f"\n{BOLD}  Document Ingestion (Step 01){NC}")
    print(f"  Paste SOPs, FAQs, product docs, or press Enter to skip.")
    docs = []
    doc_types = ["sop", "product", "faq", "brand_voice", "conversation"]

    while True:
        add = input(f"{CYAN}  → Add a document? (y/N): {NC}").strip().lower()
        if add != "y":
            break

        title = prompt("Document title", "Company SOP")
        print(f"  Types: {', '.join(doc_types)}")
        doc_type = prompt("Document type", "sop")

        print(f"{YELLOW}  Paste the document text below.")
        print(f"  Type END on a new line when done:{NC}")
        lines = []
        while True:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)

        if lines:
            docs.append({"title": title, "type": doc_type, "text": "\n".join(lines)})
            print(f"{GREEN}  ✓ Document added: {title}{NC}")

    return docs


async def run():
    print(f"\n{BOLD}{CYAN}")
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║   SYN Systems — New Client Onboarding       ║")
    print("  ║   3 steps: Ingest → Train → Deploy (48hrs)  ║")
    print("  ╚══════════════════════════════════════════════╝")
    print(f"{NC}")

    print(f"{BOLD}  Step 01 — Client Details{NC}")
    client_name   = prompt("Client / company name")
    business_name = prompt("Trading name (if different)", client_name)
    contact_name  = prompt("Primary contact name")
    contact_email = prompt("Contact email")
    industry      = choose_industry()

    if not client_name or not contact_email:
        print(f"{RED}  Client name and email are required.{NC}")
        sys.exit(1)

    print(f"\n{BOLD}  Step 02 — Select Agents{NC}")
    selected_agents = choose_agents()

    print(f"\n{BOLD}  Step 02b — Document Ingestion{NC}")
    docs = collect_documents()

    # Confirm
    print(f"\n{CYAN}{'─' * 50}{NC}")
    print(f"{BOLD}  Onboarding Summary:{NC}")
    print(f"  Client:   {client_name}")
    print(f"  Industry: {industry}")
    print(f"  Contact:  {contact_name} <{contact_email}>")
    print(f"  Agents:   {', '.join(selected_agents)}")
    print(f"  Docs:     {len(docs)} provided")
    print(f"{CYAN}{'─' * 50}{NC}")

    confirm = input(f"{CYAN}  → Start onboarding? (Y/n): {NC}").strip().lower()
    if confirm == "n":
        print(f"{YELLOW}  Cancelled.{NC}")
        sys.exit(0)

    print(f"\n{CYAN}  Running onboarding pipeline...{NC}")

    from workflows.onboarding import OnboardingWorkflow
    workflow = OnboardingWorkflow()

    try:
        session = await workflow.run(
            client_name=client_name,
            industry=industry,
            business_name=business_name,
            contact_name=contact_name,
            contact_email=contact_email,
            document_texts=docs if docs else None,
            agents_to_deploy=selected_agents,
        )

        print(f"\n{GREEN}{'═' * 50}{NC}")
        print(f"{GREEN}{BOLD}  Onboarding Complete!{NC}")
        print(f"{GREEN}{'═' * 50}{NC}")
        print(f"  Session ID: {session.session_id}")
        print(f"  Docs ingested: {session.documents_ingested}")
        print(f"  Agents configured:")
        for agent in session.agents_configured:
            print(f"    ✓ {agent}")

        if session.deployment_notes:
            print(f"\n{BOLD}  Deployment Notes:{NC}")
            for line in session.deployment_notes.split("\n")[:8]:
                if line.strip():
                    print(f"  {line.strip()}")

        if session.errors:
            print(f"\n{YELLOW}  Warnings:{NC}")
            for err in session.errors:
                print(f"  ⚠ {err}")

        print(f"\n{GREEN}  Client is live. Agents are operational. 🚀{NC}\n")

    except Exception as e:
        print(f"\n{RED}  Onboarding failed: {e}{NC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run())
