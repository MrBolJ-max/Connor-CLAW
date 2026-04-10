"""
SYN Systems — Lead Capture Agent
Multi-Channel Qualification Pipeline

Sources: Web forms, Facebook Ads, Google Ads, Zapier webhooks
Actions: Qualify → Score → Route → CRM push → Telegram alert
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional
import httpx
from loguru import logger
from core.claude_client import claude
from core.config import settings


class LeadStatus(str, Enum):
    NEW = "new"
    QUALIFIED = "qualified"
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"
    DISQUALIFIED = "disqualified"


class LeadSource(str, Enum):
    WEB_FORM = "web_form"
    FACEBOOK = "facebook"
    GOOGLE_ADS = "google_ads"
    TELEGRAM = "telegram"
    REFERRAL = "referral"
    ZAPIER = "zapier"
    MANUAL = "manual"


@dataclass
class Lead:
    name: str
    email: str
    phone: str = ""
    company: str = ""
    industry: str = ""
    pain_point: str = ""
    budget: str = ""
    source: LeadSource = LeadSource.WEB_FORM
    status: LeadStatus = LeadStatus.NEW
    score: int = 0
    qualification_summary: str = ""
    recommended_action: str = ""
    crm_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def is_hot(self) -> bool:
        return self.score >= 7

    def is_disqualified(self) -> bool:
        return self.score <= 2


# ── Scoring Engine ────────────────────────────────────────────────
BUDGET_SCORES = {
    "< $1k/mo": 1,
    "$1k–$5k/mo": 4,
    "$5k–$15k/mo": 7,
    "$15k+/mo": 10,
}

INDUSTRY_SCORES = {
    "B2B Services": 9,
    "Healthcare": 8,
    "SaaS": 9,
    "Technology": 8,
    "Real Estate": 7,
    "E-commerce": 7,
}


def score_lead_heuristic(lead: Lead) -> int:
    """Fast rule-based score (0-10) before Claude qualification."""
    score = 5  # baseline
    score += BUDGET_SCORES.get(lead.budget, 0) // 2
    score += INDUSTRY_SCORES.get(lead.industry, 0) // 3
    if lead.phone:
        score += 1
    if lead.company:
        score += 1
    if len(lead.pain_point) > 30:
        score += 1
    return min(max(score, 0), 10)


# ── Core Agent ────────────────────────────────────────────────────
class LeadCaptureAgent:
    """
    Captures leads from multiple channels, qualifies with Claude,
    routes hot leads immediately, pushes to CRM, and alerts via Telegram.
    """

    SYSTEM_PROMPT = """You are SYN Systems' Lead Qualification AI.

Your job: analyse incoming leads and determine their quality and fit for SYN Systems' AI agent services.

SYN Systems serves: B2B Services, Healthcare, SaaS, Technology, Real Estate, E-commerce.
Ideal client: $5k+/mo budget, clear operational pain points, 5+ staff, AU/US/UK based.
Disqualify: solo operators with no budget, students, competitors.

Respond with valid JSON only:
{
  "score": <1-10 integer>,
  "status": <"hot"|"warm"|"cold"|"disqualified">,
  "summary": "<2-sentence qualification summary>",
  "recommended_action": "<Call now|Send proposal|Email nurture sequence|Disqualify>",
  "tags": ["<tag1>", "<tag2>"],
  "talking_points": ["<point1>", "<point2>", "<point3>"]
}"""

    def __init__(self):
        self.processed_count = 0
        self.hot_leads_today = 0

    def qualify(self, lead: Lead) -> Lead:
        """Run Claude qualification on a lead."""
        heuristic_score = score_lead_heuristic(lead)
        lead_data = {
            "name": lead.name,
            "email": lead.email,
            "company": lead.company,
            "industry": lead.industry,
            "pain_point": lead.pain_point,
            "budget": lead.budget,
            "source": lead.source,
            "heuristic_score": heuristic_score,
        }

        try:
            raw = claude.extract_json(
                system_prompt=self.SYSTEM_PROMPT,
                user_message=json.dumps(lead_data),
                max_tokens=400,
            )
            result = json.loads(raw)
            lead.score = int(result.get("score", heuristic_score))
            lead.status = LeadStatus(result.get("status", "warm"))
            lead.qualification_summary = result.get("summary", "")
            lead.recommended_action = result.get("recommended_action", "Email nurture sequence")
            lead.tags = result.get("tags", [])
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Claude qualification parse error: {e} — falling back to heuristic")
            lead.score = heuristic_score
            lead.status = LeadStatus.HOT if heuristic_score >= 7 else LeadStatus.WARM if heuristic_score >= 4 else LeadStatus.COLD

        self.processed_count += 1
        if lead.is_hot():
            self.hot_leads_today += 1
            logger.info(f"🔥 HOT LEAD: {lead.name} | Score: {lead.score} | {lead.industry}")
        else:
            logger.info(f"Lead qualified: {lead.name} | Score: {lead.score} | Status: {lead.status}")

        return lead

    def generate_follow_up_email(self, lead: Lead) -> str:
        """Generate a personalised follow-up email for the lead."""
        return claude.chat(
            system_prompt=(
                "You are SYN Systems' Sales Follow-Up Agent. "
                "Write personalised, conversion-focused emails. "
                "Reference the lead's specific industry and pain point. "
                "Be warm but professional. End with a clear CTA to book a call."
            ),
            user_message=(
                f"Write a follow-up email for:\n"
                f"Name: {lead.name}\n"
                f"Company: {lead.company}\n"
                f"Industry: {lead.industry}\n"
                f"Pain Point: {lead.pain_point}\n"
                f"Budget: {lead.budget}\n"
                f"Source: {lead.source}\n\n"
                "Keep it under 200 words. Include subject line."
            ),
            max_tokens=400,
        )

    def generate_proposal_outline(self, lead: Lead) -> str:
        """Generate a tailored proposal outline for hot leads."""
        return claude.chat(
            system_prompt=(
                "You are SYN Systems' proposal specialist. "
                "Create tailored AI agent solution proposals. "
                "Always recommend the most relevant agents based on industry and pain points."
            ),
            user_message=(
                f"Create a proposal outline for {lead.name} at {lead.company}.\n"
                f"Industry: {lead.industry}\n"
                f"Pain Point: {lead.pain_point}\n"
                f"Budget: {lead.budget}\n\n"
                "Include: Executive Summary, Recommended Agents, Expected ROI, "
                "Timeline, Investment. Keep concise — this is an outline."
            ),
            max_tokens=600,
        )

    async def push_to_crm(self, lead: Lead) -> bool:
        """Push qualified lead to HubSpot CRM."""
        if not settings.hubspot_api_key:
            logger.warning("HubSpot API key not configured — skipping CRM push")
            return False
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "properties": {
                        "firstname": lead.name.split()[0],
                        "lastname": " ".join(lead.name.split()[1:]) if len(lead.name.split()) > 1 else "",
                        "email": lead.email,
                        "phone": lead.phone,
                        "company": lead.company,
                        "industry": lead.industry,
                        "hs_lead_status": lead.status.value.upper(),
                        "lead_score": str(lead.score),
                        "pain_point__c": lead.pain_point,
                        "budget__c": lead.budget,
                        "lead_source": lead.source.value,
                    }
                }
                response = await client.post(
                    "https://api.hubapi.com/crm/v3/objects/contacts",
                    headers={
                        "Authorization": f"Bearer {settings.hubspot_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=10.0,
                )
                if response.status_code in (200, 201):
                    data = response.json()
                    lead.crm_id = data.get("id", "")
                    logger.info(f"Lead pushed to HubSpot: {lead.crm_id}")
                    return True
                logger.error(f"HubSpot error {response.status_code}: {response.text}")
                return False
        except httpx.RequestError as e:
            logger.error(f"HubSpot request failed: {e}")
            return False

    async def send_telegram_alert(self, lead: Lead):
        """Fire a Telegram alert for hot/warm leads."""
        if not (settings.telegram_bot_token and settings.telegram_admin_chat_id):
            return
        emoji = "🔥" if lead.is_hot() else "👋"
        msg = (
            f"{emoji} *New Lead — Score {lead.score}/10*\n\n"
            f"👤 {lead.name}\n"
            f"📧 {lead.email}\n"
            f"📱 {lead.phone or 'N/A'}\n"
            f"🏭 {lead.industry}\n"
            f"💰 {lead.budget}\n"
            f"📍 Source: {lead.source}\n\n"
            f"*AI Assessment:* {lead.qualification_summary}\n"
            f"*Action:* {lead.recommended_action}"
        )
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                    json={
                        "chat_id": settings.telegram_admin_chat_id,
                        "text": msg,
                        "parse_mode": "Markdown",
                    },
                    timeout=5.0,
                )
        except httpx.RequestError as e:
            logger.error(f"Telegram alert failed: {e}")

    async def process(self, lead: Lead) -> Lead:
        """Full pipeline: qualify → CRM → alert."""
        lead = self.qualify(lead)
        if not lead.is_disqualified():
            await self.push_to_crm(lead)
            await self.send_telegram_alert(lead)
        return lead


# ── Webhook Handler (FastAPI compatible) ─────────────────────────
async def handle_webhook(payload: dict, source: str = "web_form") -> dict:
    """
    Entry point for incoming webhooks from Zapier, web forms, Facebook, etc.
    Expected payload: {name, email, phone?, company?, industry?, pain_point?, budget?}
    """
    agent = LeadCaptureAgent()
    lead = Lead(
        name=payload.get("name", "Unknown"),
        email=payload.get("email", ""),
        phone=payload.get("phone", ""),
        company=payload.get("company", ""),
        industry=payload.get("industry", ""),
        pain_point=payload.get("pain_point", payload.get("message", "")),
        budget=payload.get("budget", ""),
        source=LeadSource(source) if source in LeadSource._value2member_map_ else LeadSource.WEB_FORM,
    )
    lead = await agent.process(lead)
    return {
        "status": "processed",
        "lead_id": lead.crm_id,
        "score": lead.score,
        "qualification": lead.status.value,
        "action": lead.recommended_action,
    }
