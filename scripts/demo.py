#!/usr/bin/env python3
"""
SYN Systems — Connor-CLAW Demo
Exercises every AI agent with realistic data so you can verify
everything works before going live with real clients.

Usage: python scripts/demo.py
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from loguru import logger

CYAN  = "\033[0;36m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED   = "\033[0;31m"
BOLD  = "\033[1m"
NC    = "\033[0m"

def section(title: str):
    print(f"\n{CYAN}{'─' * 55}{NC}")
    print(f"{BOLD}{CYAN}  {title}{NC}")
    print(f"{CYAN}{'─' * 55}{NC}")

def ok(msg: str):
    print(f"{GREEN}  ✓ {msg}{NC}")

def info(msg: str):
    print(f"  {msg}")

def warn(msg: str):
    print(f"{YELLOW}  ⚠ {msg}{NC}")


# ── Demo 1: Lead Capture ──────────────────────────────────────────
async def demo_lead_capture():
    section("AGENT 1 — Lead Capture")
    from agents.lead_capture import LeadCaptureAgent, Lead, LeadSource

    agent = LeadCaptureAgent()

    test_leads = [
        Lead(
            name="Sarah Mitchell",
            email="sarah@apexconsulting.com.au",
            phone="+61412345678",
            company="Apex Consulting",
            industry="B2B Services",
            pain_point="We spend 20+ hours a week manually following up leads. Half of them go cold.",
            budget="$5k–$15k/mo",
            source=LeadSource.WEB_FORM,
        ),
        Lead(
            name="Dr. James Nguyen",
            email="james@medcareclinics.com.au",
            phone="+61398765432",
            company="MedCare Clinics",
            industry="Healthcare",
            pain_point="Reception overwhelmed. Missing calls after hours. Patients going to competitors.",
            budget="$5k–$15k/mo",
            source=LeadSource.GOOGLE_ADS,
        ),
        Lead(
            name="Tom",
            email="tom@gmail.com",
            phone="",
            company="",
            industry="",
            pain_point="just curious",
            budget="< $1k/mo",
            source=LeadSource.FACEBOOK,
        ),
    ]

    for lead in test_leads:
        qualified = agent.qualify(lead)
        status_icon = "🔥" if qualified.is_hot() else "👋" if qualified.score >= 4 else "❄️"
        ok(f"{status_icon} {lead.name} | Score: {qualified.score}/10 | {qualified.status.value.upper()}")
        info(f"   Action: {qualified.recommended_action}")

        if qualified.is_hot():
            email = agent.generate_follow_up_email(qualified)
            info(f"   Follow-up email generated: \"{email[:80]}...\"")

    ok(f"Processed {len(test_leads)} leads | {agent.hot_leads_today} hot today")


# ── Demo 2: Sales Follow-Up ───────────────────────────────────────
async def demo_sales_followup():
    section("AGENT 2 — Sales Follow-Up")
    from agents.sales_followup import SalesFollowUpAgent, FollowUpContext, FollowUpStage

    agent = SalesFollowUpAgent()

    ctx = FollowUpContext(
        lead_name="Sarah Mitchell",
        lead_email="sarah@apexconsulting.com.au",
        company="Apex Consulting",
        industry="B2B Services",
        pain_point="Spending 20+ hours manually following up leads",
        budget="$5k–$15k/mo",
        stage=FollowUpStage.INITIAL,
        previous_interactions=[],
        objections_raised=[],
        score=8,
    )

    email = agent.generate_email(ctx)
    ok(f"Initial email generated")
    info(f"   Subject: {email.get('subject', 'N/A')}")
    info(f"   CTA: {email.get('cta', 'N/A')}")

    ctx.objections_raised = ["too expensive"]
    objection_response = agent.handle_objection("It's too expensive for us right now", ctx)
    ok("Objection handled: 'too expensive'")
    info(f"   Response preview: {objection_response[:100]}...")

    should_escalate = agent.should_escalate(ctx)
    ok(f"Escalation check: {'Escalate to human' if should_escalate else 'Keep AI handling'}")

    sequence = agent.generate_sequence(ctx)
    ok(f"4-email sequence generated: {[e['stage'] for e in sequence]}")


# ── Demo 3: Content & SEO ─────────────────────────────────────────
async def demo_content_seo():
    section("AGENT 3 — Content & SEO")
    from agents.content_seo import ContentSEOAgent, ContentBrief, ContentType

    agent = ContentSEOAgent()

    keywords = agent.research_keywords("AI automation for medical practices", "Healthcare")
    ok(f"Keyword research complete")
    info(f"   Primary: {keywords.get('primary_keyword', 'N/A')}")
    info(f"   Intent: {keywords.get('search_intent', 'N/A')}")
    info(f"   Competition: {keywords.get('competition', 'N/A')}")

    brief = ContentBrief(
        title="How AI Is Transforming Medical Receptionists in Australia (2026)",
        content_type=ContentType.BLOG_POST,
        primary_keyword="AI receptionist for medical practices Australia",
        secondary_keywords=["AI healthcare automation", "medical clinic AI"],
        target_audience="Healthcare practice managers and clinic owners in Australia",
        industry="Healthcare",
        word_count=800,
    )
    content = agent.generate_content(brief)
    ok(f"Blog post generated: {content.estimated_word_count} words")
    info(f"   SEO score estimate: {content.seo_score_estimate}/100")
    info(f"   Meta: {content.meta_description}")
    info(f"   Tags: {content.tags[:3]}")

    calendar = agent.generate_content_calendar("Real Estate", weeks=2)
    ok(f"Content calendar: {len(calendar)} items across 2 weeks")


# ── Demo 4: AI Auditor ────────────────────────────────────────────
async def demo_ai_auditor():
    section("AGENT 4 — AI Auditor")
    from agents.ai_auditor import AIAuditor, Invoice, InvoiceStatus
    from datetime import datetime, timedelta

    auditor = AIAuditor()

    today = datetime.now()
    invoices = [
        Invoice("INV-001", "Apex Consulting",    4500.00, InvoiceStatus.OVERDUE,  (today - timedelta(45)).strftime("%Y-%m-%d"), (today - timedelta(75)).strftime("%Y-%m-%d"), "Monthly retainer Q1", days_overdue=45),
        Invoice("INV-002", "MedCare Clinics",    8200.00, InvoiceStatus.OVERDUE,  (today - timedelta(12)).strftime("%Y-%m-%d"), (today - timedelta(42)).strftime("%Y-%m-%d"), "AVA setup + monthly", days_overdue=12),
        Invoice("INV-003", "GrowthLab",          2100.00, InvoiceStatus.PAID,     (today - timedelta(30)).strftime("%Y-%m-%d"), (today - timedelta(60)).strftime("%Y-%m-%d"), "Content package"),
        Invoice("INV-004", "TechStart",          6750.00, InvoiceStatus.SENT,     (today + timedelta(15)).strftime("%Y-%m-%d"), (today - timedelta(15)).strftime("%Y-%m-%d"), "Lead capture deployment"),
        Invoice("INV-005", "RetailMax",          3300.00, InvoiceStatus.OVERDUE,  (today - timedelta(65)).strftime("%Y-%m-%d"), (today - timedelta(95)).strftime("%Y-%m-%d"), "AI Auditor licence", days_overdue=65),
        Invoice("INV-006", "Apex Consulting",    4500.00, InvoiceStatus.OVERDUE,  (today - timedelta(45)).strftime("%Y-%m-%d"), (today - timedelta(75)).strftime("%Y-%m-%d"), "Monthly retainer Q1 — DUPLICATE?", days_overdue=45),
    ]

    report = auditor.generate_full_audit("SYN Systems Portfolio", invoices)
    ok(f"Financial audit complete")
    info(f"   Revenue (paid):  ${report.total_revenue_aud:,.2f} AUD")
    info(f"   Outstanding:     ${report.total_outstanding_aud:,.2f} AUD")
    info(f"   Recovery target: ${report.recovery_potential_aud:,.2f} AUD")
    info(f"   Discrepancies:   {len(report.discrepancies)} found")
    info(f"   Cash flow:       {report.cash_flow_status}")

    for disc in report.discrepancies[:2]:
        info(f"   [{disc.severity.upper()}] {disc.description}")

    chase_email = auditor.generate_chase_email(invoices[0])
    ok(f"Chase email generated for INV-001")
    info(f"   Subject: {chase_email.get('subject', 'N/A')}")


# ── Demo 5: AVA ───────────────────────────────────────────────────
async def demo_ava():
    section("AGENT 5 — AVA (AI Receptionist)")
    from agents.ava import AVAReceptionist, CallContext, CallIntent

    ava = AVAReceptionist()

    system_prompt = ava.build_system_prompt(
        client_id="medcare",
        business_name="MedCare Clinics",
        industry="Healthcare",
        agent_name="AVA",
        custom_info="GP clinic open Mon-Sat 8am-6pm. Dr Smith and Dr Jones. Bulk billing available.",
    )
    ok("AVA system prompt generated for MedCare Clinics")
    info(f"   Length: {len(system_prompt)} chars")
    info(f"   Preview: {system_prompt[:120]}...")

    history = []
    response1 = ava.process_turn(system_prompt, history, "Hi, I need to book an appointment")
    ok(f"Turn 1 processed")
    info(f"   AVA: {response1[:120]}...")

    response2 = ava.process_turn(system_prompt, history, "Tomorrow morning if possible, for a general checkup")
    ok(f"Turn 2 processed")
    info(f"   AVA: {response2[:120]}...")

    intent = ava.classify_intent("I need to book an appointment for tomorrow")
    ok(f"Intent classified: {intent.value}")

    vapi_config = ava.generate_vapi_config("MedCare Clinics", "Healthcare", "AVA")
    ok(f"VAPI config generated")
    info(f"   Model: {vapi_config['model']['model']}")
    info(f"   Voice: {vapi_config['voice']['provider']} / {vapi_config['voice']['voiceId']}")
    info(f"   Language: {vapi_config['transcriber']['language']}")
    info(f"   First message: \"{vapi_config['firstMessage']}\"")


# ── Demo 6: Knowledge Base ────────────────────────────────────────
async def demo_knowledge_base():
    section("KNOWLEDGE BASE — Document Ingestion")
    from core.knowledge_base import KnowledgeBaseManager

    kb = KnowledgeBaseManager()
    client_id = "demo_growthlab"

    kb_obj = kb.create_client(client_id, "GrowthLab (Demo)", "SaaS")
    ok(f"Knowledge base created: {kb_obj.client_name}")

    doc = kb.ingest_document(
        client_id=client_id,
        doc_type="sop",
        title="Customer Onboarding SOP",
        text="""
        GrowthLab Customer Onboarding Standard Operating Procedure

        Step 1: Welcome email sent within 1 hour of signup
        Step 2: Schedule onboarding call within 48 hours
        Step 3: Workspace setup — admin creates account, invites team
        Step 4: Data migration — customer provides CSV export from previous tool
        Step 5: Training session — 60 min video call covering core features
        Step 6: 30-day check-in — success manager reviews usage metrics

        Escalation: If customer hasn't logged in after 7 days, escalate to CS manager.
        Churn risk indicators: No logins for 14 days, support tickets > 3 in first month.

        Brand voice: Friendly, technical but accessible, startup energy.
        Never use corporate jargon. Use "you" not "the customer".
        """,
    )
    ok(f"Document ingested: {doc.title}")
    info(f"   Summary: {doc.summary[:100]}...")
    info(f"   Key facts: {len(doc.key_facts)} extracted")
    info(f"   Escalation triggers: {doc.escalation_triggers[:2]}")

    results = kb.search(client_id, "what to do if customer hasn't logged in")
    ok(f"KB search working: {len(results)} results")

    system_prompt = kb.get_agent_system_prompt(client_id)
    ok(f"Agent system prompt generated: {len(system_prompt)} chars")

    import shutil
    shutil.rmtree(f"data/knowledge_bases/{client_id}.json", ignore_errors=True)
    try:
        os.remove(f"data/knowledge_bases/{client_id}.json")
    except FileNotFoundError:
        pass


# ── Demo 7: Reporting ─────────────────────────────────────────────
async def demo_reporting():
    section("REPORTING — Automated Reports")
    from workflows.reporting import ReportingEngine

    engine = ReportingEngine()
    report = engine.build_report("daily")

    ok(f"Daily report generated")
    info(f"   Period: {report.period}")
    info(f"   Health: {report.overall_health}")
    info(f"   Leads: {report.total_leads} total | {report.total_hot_leads} hot")
    info(f"   Bookings: {report.total_bookings}")
    info(f"   Revenue recovered: ${report.total_revenue_recovered:,.0f} AUD")
    info(f"   Highlights: {len(report.highlights)}")
    info(f"   Warnings: {len(report.warnings)}")

    formatted = engine.format_for_telegram(report)
    ok(f"Telegram-formatted report: {len(formatted)} chars")


# ── Main ──────────────────────────────────────────────────────────
async def main():
    print(f"\n{BOLD}{CYAN}")
    print("  ╔═══════════════════════════════════════════╗")
    print("  ║   SYN Systems — Connor-CLAW Demo Run     ║")
    print("  ║   Testing all 5 AI agents + KB + Reports ║")
    print("  ╚═══════════════════════════════════════════╝")
    print(f"{NC}")

    demos = [
        ("Lead Capture Agent",    demo_lead_capture),
        ("Sales Follow-Up Agent", demo_sales_followup),
        ("Content & SEO Agent",   demo_content_seo),
        ("AI Auditor",            demo_ai_auditor),
        ("AVA — AI Receptionist", demo_ava),
        ("Knowledge Base",        demo_knowledge_base),
        ("Reporting Engine",      demo_reporting),
    ]

    passed = 0
    failed = 0

    for name, demo_fn in demos:
        try:
            await demo_fn()
            passed += 1
        except Exception as e:
            print(f"{RED}  ✗ {name} failed: {e}{NC}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{CYAN}{'═' * 55}{NC}")
    print(f"{BOLD}  Results: {GREEN}{passed} passed{NC}{BOLD} | {RED}{failed} failed{NC}")
    print(f"{CYAN}{'═' * 55}{NC}\n")

    if failed == 0:
        print(f"{GREEN}{BOLD}  All agents operational. Ready to go live! 🚀{NC}\n")
    else:
        print(f"{YELLOW}  Some agents need attention. Check .env and API keys.{NC}\n")


if __name__ == "__main__":
    asyncio.run(main())
