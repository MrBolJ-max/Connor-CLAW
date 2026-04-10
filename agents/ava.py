"""
SYN Systems — AVA (AI Receptionist)
24/7 voice agent that books jobs, qualifies leads, and handles payments.
Answers every call instantly with the warmth of your best team member.
95%+ first-call resolution rate.

Integrations: Calendly, HubSpot, Xero, Stripe, VAPI, Twilio
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import httpx
from loguru import logger
from core.claude_client import claude
from core.config import settings


class CallIntent(str, Enum):
    BOOK_APPOINTMENT = "book_appointment"
    GET_QUOTE = "get_quote"
    SUPPORT = "support"
    BILLING = "billing"
    GENERAL_ENQUIRY = "general_enquiry"
    COMPLAINT = "complaint"
    SALES = "sales"
    UNKNOWN = "unknown"


class CallOutcome(str, Enum):
    BOOKED = "booked"
    QUOTE_SENT = "quote_sent"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    CALLBACK_SCHEDULED = "callback_scheduled"
    VOICEMAIL = "voicemail"
    HUNG_UP = "hung_up"


@dataclass
class CallContext:
    client_id: str
    caller_name: str = ""
    caller_phone: str = ""
    caller_email: str = ""
    intent: CallIntent = CallIntent.UNKNOWN
    transcript: list[dict] = field(default_factory=list)
    outcome: Optional[CallOutcome] = None
    booking_id: str = ""
    notes: str = ""
    call_duration_seconds: int = 0
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class AVAReceptionist:
    """
    AVA — SYN Systems' AI Receptionist.

    Handles inbound calls via VAPI/Twilio, uses Claude to process
    conversation turns, books appointments via Calendly, and escalates
    when needed. Integrates with HubSpot for CRM logging.
    """

    # ── System Prompts per Industry ──────────────────────────────
    BASE_SYSTEM_PROMPT = """You are {agent_name}, an AI receptionist for {business_name}.

Your personality: {personality}

Your role:
- Answer calls warmly and professionally
- Understand why the caller is contacting {business_name}
- Book appointments, provide information, or take messages
- Qualify potential leads without being salesy
- Escalate only when absolutely necessary (complex complaints, medical emergencies, legal matters)

Business information:
{business_info}

Response guidelines:
- Keep responses concise and conversational (this is voice, not text)
- Use natural language, contractions, and warmth
- Never say "I am an AI" unless directly asked
- If unsure, say you'll check and follow up rather than guessing
- Always confirm bookings and next steps clearly

Escalation triggers: {escalation_triggers}"""

    INDUSTRY_CONFIGS = {
        "Healthcare": {
            "personality": "warm, calm, reassuring — like a trusted receptionist at a GP clinic",
            "business_info": "medical practice offering appointments, results inquiries, and referrals",
            "escalation_triggers": "medical emergencies, urgent symptoms, medication queries, anything clinical",
            "booking_duration_mins": 15,
        },
        "B2B Services": {
            "personality": "professional, knowledgeable, efficient — like a top EA",
            "business_info": "B2B consulting firm offering strategy, implementation, and advisory services",
            "escalation_triggers": "contract disputes, C-suite escalations, sensitive negotiations",
            "booking_duration_mins": 30,
        },
        "Real Estate": {
            "personality": "friendly, enthusiastic, knowledgeable about property — like a great agent",
            "business_info": "real estate agency handling property sales, rentals, and appraisals",
            "escalation_triggers": "legal disputes, contract issues, urgent settlement matters",
            "booking_duration_mins": 20,
        },
        "E-commerce": {
            "personality": "helpful, upbeat, solution-focused — like excellent customer support",
            "business_info": "e-commerce business handling orders, returns, shipping, and product enquiries",
            "escalation_triggers": "fraud claims, large refunds, legal threats, media inquiries",
            "booking_duration_mins": 10,
        },
        "SaaS": {
            "personality": "tech-savvy, helpful, clear — like a great product support rep",
            "business_info": "SaaS company offering software subscriptions, onboarding, and technical support",
            "escalation_triggers": "enterprise contract issues, major outages, security incidents",
            "booking_duration_mins": 30,
        },
        "Technology": {
            "personality": "knowledgeable, clear, patient — like a great technical account manager",
            "business_info": "technology company providing IT solutions, development, and support",
            "escalation_triggers": "critical system failures, enterprise negotiations, legal matters",
            "booking_duration_mins": 30,
        },
    }

    def build_system_prompt(
        self,
        client_id: str,
        business_name: str,
        industry: str,
        agent_name: str = "AVA",
        custom_info: str = "",
        kb_instructions: str = "",
    ) -> str:
        """Build a customised AVA system prompt for a specific client."""
        config = self.INDUSTRY_CONFIGS.get(industry, self.INDUSTRY_CONFIGS["B2B Services"])
        business_info = custom_info or config["business_info"]
        if kb_instructions:
            business_info += f"\n\nAdditional context from knowledge base:\n{kb_instructions}"

        return self.BASE_SYSTEM_PROMPT.format(
            agent_name=agent_name,
            business_name=business_name,
            personality=config["personality"],
            business_info=business_info,
            escalation_triggers=config["escalation_triggers"],
        )

    def process_turn(
        self,
        system_prompt: str,
        conversation_history: list[dict],
        caller_message: str,
    ) -> str:
        """Process a single conversation turn — called each time the caller speaks."""
        conversation_history.append({"role": "user", "content": caller_message})

        response = claude.chat_with_history(
            system_prompt=system_prompt,
            messages=conversation_history,
            max_tokens=200,
            temperature=0.8,
        )

        conversation_history.append({"role": "assistant", "content": response})
        return response

    def classify_intent(self, transcript_text: str) -> CallIntent:
        """Classify the caller's primary intent from conversation."""
        intent = claude.classify(
            text=transcript_text,
            categories=[i.value for i in CallIntent],
            context="This is a business phone call transcript.",
        )
        try:
            return CallIntent(intent)
        except ValueError:
            return CallIntent.UNKNOWN

    def generate_call_summary(self, ctx: CallContext) -> str:
        """Generate a structured call summary for CRM logging."""
        transcript_text = "\n".join(
            f"{turn['role'].upper()}: {turn['content']}"
            for turn in ctx.transcript
        )
        return claude.chat(
            system_prompt=(
                "You are a call summary AI. Write concise, structured summaries "
                "for CRM logging. Include: caller intent, key information gathered, "
                "outcome, and next steps."
            ),
            user_message=(
                f"Summarise this call:\n\n"
                f"Caller: {ctx.caller_name} ({ctx.caller_phone})\n"
                f"Intent: {ctx.intent.value}\n"
                f"Outcome: {ctx.outcome.value if ctx.outcome else 'unknown'}\n"
                f"Duration: {ctx.call_duration_seconds}s\n\n"
                f"Transcript:\n{transcript_text[:3000]}"
            ),
            max_tokens=250,
        )

    async def book_via_calendly(
        self,
        invitee_name: str,
        invitee_email: str,
        event_type_uri: str,
    ) -> dict:
        """Book an appointment via Calendly API."""
        if not settings.calendly_api_key:
            logger.warning("Calendly not configured")
            return {}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.calendly.com/scheduling_links",
                    headers={
                        "Authorization": f"Bearer {settings.calendly_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "max_event_count": 1,
                        "owner": event_type_uri,
                        "owner_type": "EventType",
                    },
                    timeout=10.0,
                )
                if response.status_code == 201:
                    data = response.json()
                    logger.info(f"Calendly link created for {invitee_name}")
                    return {"booking_url": data.get("resource", {}).get("booking_url", "")}
                logger.error(f"Calendly error {response.status_code}")
                return {}
        except httpx.RequestError as e:
            logger.error(f"Calendly request failed: {e}")
            return {}

    async def log_to_hubspot(self, ctx: CallContext, summary: str) -> bool:
        """Log call to HubSpot as an activity."""
        if not settings.hubspot_api_key:
            return False
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "engagement": {
                        "active": True,
                        "type": "CALL",
                        "timestamp": int(datetime.utcnow().timestamp() * 1000),
                    },
                    "associations": {},
                    "metadata": {
                        "body": summary,
                        "fromNumber": ctx.caller_phone,
                        "status": "COMPLETED",
                        "durationMilliseconds": ctx.call_duration_seconds * 1000,
                        "recordingUrl": "",
                        "disposition": ctx.outcome.value if ctx.outcome else "unknown",
                    },
                }
                response = await client.post(
                    "https://api.hubapi.com/engagements/v1/engagements",
                    headers={
                        "Authorization": f"Bearer {settings.hubspot_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=10.0,
                )
                return response.status_code in (200, 201)
        except httpx.RequestError as e:
            logger.error(f"HubSpot log failed: {e}")
            return False

    def generate_vapi_config(
        self,
        business_name: str,
        industry: str,
        agent_name: str = "AVA",
        phone_number_id: Optional[str] = None,
        kb_instructions: str = "",
    ) -> dict:
        """
        Generate a VAPI assistant configuration.
        This config is deployed to VAPI to create the live voice agent.
        """
        system_prompt = self.build_system_prompt(
            client_id="",
            business_name=business_name,
            industry=industry,
            agent_name=agent_name,
            kb_instructions=kb_instructions,
        )
        config = {
            "name": f"{agent_name} — {business_name}",
            "model": {
                "provider": "anthropic",
                "model": "claude-opus-4-6",
                "systemPrompt": system_prompt,
                "temperature": 0.8,
                "maxTokens": 200,
            },
            "voice": {
                "provider": "11labs",
                "voiceId": "rachel",
                "stability": 0.5,
                "similarityBoost": 0.75,
            },
            "transcriber": {
                "provider": "deepgram",
                "model": "nova-2",
                "language": "en-AU",
            },
            "firstMessage": (
                f"Thank you for calling {business_name}, this is {agent_name} speaking. "
                "How can I help you today?"
            ),
            "endCallMessage": "Thanks for calling. Have a wonderful day!",
            "endCallPhrases": ["goodbye", "bye", "thanks bye", "that's all"],
            "silenceTimeoutSeconds": 30,
            "maxDurationSeconds": 1800,
            "backgroundSound": "off",
            "backchannelingEnabled": True,
            "backgroundDenoisingEnabled": True,
        }

        if phone_number_id or settings.vapi_phone_number_id:
            config["phoneNumberId"] = phone_number_id or settings.vapi_phone_number_id

        return config

    async def deploy_vapi_assistant(self, config: dict) -> dict:
        """Deploy AVA to VAPI."""
        if not settings.vapi_api_key:
            logger.warning("VAPI not configured — returning config only")
            return {"config": config, "status": "not_deployed"}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.vapi.ai/assistant",
                    headers={
                        "Authorization": f"Bearer {settings.vapi_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=config,
                    timeout=15.0,
                )
                if response.status_code in (200, 201):
                    data = response.json()
                    logger.info(f"AVA deployed to VAPI: {data.get('id')}")
                    return {"assistant_id": data.get("id"), "status": "deployed", "config": config}
                logger.error(f"VAPI deploy error {response.status_code}: {response.text[:200]}")
                return {"status": "failed", "error": response.text[:200]}
        except httpx.RequestError as e:
            logger.error(f"VAPI deploy failed: {e}")
            return {"status": "failed", "error": str(e)}


ava = AVAReceptionist()
