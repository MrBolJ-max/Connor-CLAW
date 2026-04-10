"""
SYN Systems — Sales Follow-Up Agent
Follows up leads, handles objections, closes deals via email.
Never lets a hot lead go cold. 3x conversion improvement.

Integrations: HubSpot, Salesforce, Pipedrive
"""

import json
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import httpx
from loguru import logger
from core.claude_client import claude
from core.config import settings


class FollowUpStage(str, Enum):
    INITIAL = "initial"           # First contact after lead capture
    DAY_2 = "day_2"              # Value-add follow-up
    DAY_5 = "day_5"              # Objection handling
    DAY_10 = "day_10"            # Final push / last chance
    PROPOSAL_SENT = "proposal_sent"
    MEETING_BOOKED = "meeting_booked"
    WON = "won"
    LOST = "lost"


@dataclass
class FollowUpContext:
    lead_name: str
    lead_email: str
    company: str
    industry: str
    pain_point: str
    budget: str
    stage: FollowUpStage
    previous_interactions: list[str]
    objections_raised: list[str]
    score: int = 5


class SalesFollowUpAgent:
    """
    AI-powered sales follow-up agent.
    Generates personalised email sequences, handles objections,
    and knows when to escalate to a human closer.
    """

    SYSTEM_PROMPT = """You are SYN Systems' Sales Follow-Up AI — the best closer on the team.

You follow up leads who have shown interest in AI automation services.
Your goal: book a demo call or send a proposal.

SYN Systems' value props:
- AI agents deployed in 48 hours
- 95%+ first-call resolution (AVA)
- 3x conversion improvement
- 40+ hrs/week reclaimed
- Clients: B2B, Healthcare, SaaS, Tech, Real Estate, E-commerce

Always: personalise to their industry & pain point, be helpful not pushy,
use social proof, create urgency without pressure.

Never: use generic templates, ignore previous interactions, be aggressive."""

    OBJECTION_HANDLERS = {
        "too expensive": (
            "Acknowledge the investment concern. Reframe as ROI: "
            "if they save 40hrs/week at $50/hr, that's $2k/week or $100k/year. "
            "Offer a phased start with one agent."
        ),
        "not ready": (
            "Validate their position. Share a case study of a client who said the same "
            "and deployed in 48hrs. Offer a no-obligation discovery call."
        ),
        "already have staff": (
            "Position AI as augmentation not replacement. Staff freed from admin = "
            "higher-value work. Reference 40+ hrs/week reclaimed stat."
        ),
        "need to think": (
            "Offer something concrete to think about: send a custom audit or proposal. "
            "Set a specific follow-up date."
        ),
        "competitors": (
            "Ask what they're comparing. Highlight 48hr deployment, "
            "no lock-in contracts, and AU-based support."
        ),
    }

    def generate_email(self, ctx: FollowUpContext) -> dict:
        """Generate a personalised follow-up email for the given stage."""
        stage_guidance = {
            FollowUpStage.INITIAL: (
                "First email after lead capture. Warm, personalised, reference their pain point. "
                "Invite them to a 15-min discovery call. No selling yet."
            ),
            FollowUpStage.DAY_2: (
                "Value-add email. Share a relevant case study or insight about their industry. "
                "Position SYN Systems as experts. Soft CTA."
            ),
            FollowUpStage.DAY_5: (
                "Address potential hesitations. Share ROI stats. "
                "Offer a free AI readiness audit. Stronger CTA."
            ),
            FollowUpStage.DAY_10: (
                "Final follow-up. Create gentle urgency (limited slots, price increase). "
                "Make it easy to say yes OR give a clear reason to close the loop."
            ),
            FollowUpStage.PROPOSAL_SENT: (
                "Follow up on sent proposal. Ask if they have questions. "
                "Offer a call to walk through it together."
            ),
        }

        objection_context = ""
        if ctx.objections_raised:
            handlers = []
            for obj in ctx.objections_raised:
                for key, handler in self.OBJECTION_HANDLERS.items():
                    if key in obj.lower():
                        handlers.append(handler)
            if handlers:
                objection_context = f"\nHandle these objections: {'; '.join(handlers)}"

        guidance = stage_guidance.get(ctx.stage, "Write a relevant follow-up email.")

        result = claude.extract_json(
            system_prompt=self.SYSTEM_PROMPT,
            user_message=(
                f"Generate a follow-up email.\n\n"
                f"Stage: {ctx.stage.value}\n"
                f"Guidance: {guidance}{objection_context}\n\n"
                f"Lead: {ctx.lead_name}\n"
                f"Company: {ctx.company}\n"
                f"Industry: {ctx.industry}\n"
                f"Pain Point: {ctx.pain_point}\n"
                f"Budget: {ctx.budget}\n"
                f"Previous interactions: {json.dumps(ctx.previous_interactions[-3:])}\n\n"
                "Return JSON: {\"subject\": \"...\", \"body\": \"...\", \"cta\": \"...\"}"
            ),
            max_tokens=600,
        )
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"subject": "Following up", "body": result, "cta": "Book a call"}

    def handle_objection(self, objection: str, ctx: FollowUpContext) -> str:
        """Generate a direct objection-handling response."""
        handler_hint = ""
        for key, hint in self.OBJECTION_HANDLERS.items():
            if key in objection.lower():
                handler_hint = f"Strategy hint: {hint}"
                break

        return claude.chat(
            system_prompt=self.SYSTEM_PROMPT,
            user_message=(
                f"Handle this objection from {ctx.lead_name} ({ctx.industry}):\n"
                f"Objection: '{objection}'\n"
                f"Their pain point: {ctx.pain_point}\n"
                f"Budget: {ctx.budget}\n"
                f"{handler_hint}\n\n"
                "Write a short, empathetic response that re-engages them. Under 150 words."
            ),
            max_tokens=250,
        )

    def generate_sequence(self, ctx: FollowUpContext) -> list[dict]:
        """Generate the full 4-email follow-up sequence for a lead."""
        sequence = []
        stages = [
            FollowUpStage.INITIAL,
            FollowUpStage.DAY_2,
            FollowUpStage.DAY_5,
            FollowUpStage.DAY_10,
        ]
        send_days = [0, 2, 5, 10]
        for stage, day in zip(stages, send_days):
            ctx.stage = stage
            email = self.generate_email(ctx)
            email["send_day"] = day
            email["stage"] = stage.value
            sequence.append(email)
            logger.debug(f"Generated {stage.value} email for {ctx.lead_name}")
        return sequence

    def should_escalate(self, ctx: FollowUpContext) -> bool:
        """Determine if this lead needs a human to step in."""
        if ctx.score >= 9:
            return True
        if ctx.budget in ("$15k+/mo",) and ctx.stage == FollowUpStage.DAY_2:
            return True
        if len(ctx.objections_raised) >= 3:
            return True
        return False

    def escalation_brief(self, ctx: FollowUpContext) -> str:
        """Generate a brief for the human closer taking over this lead."""
        return claude.chat(
            system_prompt="You are a sales intelligence AI. Write concise handover briefs.",
            user_message=(
                f"Write a handover brief for a human closer taking over this lead:\n"
                f"Name: {ctx.lead_name} | Company: {ctx.company}\n"
                f"Industry: {ctx.industry} | Budget: {ctx.budget}\n"
                f"Pain Point: {ctx.pain_point}\n"
                f"Score: {ctx.score}/10 | Stage: {ctx.stage.value}\n"
                f"Objections: {ctx.objections_raised}\n"
                f"Interactions: {ctx.previous_interactions}\n\n"
                "Include: key context, recommended approach, and 3 talking points. Under 200 words."
            ),
            max_tokens=350,
        )


sales_agent = SalesFollowUpAgent()
