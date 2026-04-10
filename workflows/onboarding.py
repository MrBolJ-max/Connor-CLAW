"""
SYN Systems — Client Onboarding Workflow
Automates the 3-step SYN Systems onboarding process:
  01. Ingest Documents
  02. Train Agents
  03. Deploy & Go Live

Triggered via Telegram /onboard command or API endpoint.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from loguru import logger
from core.claude_client import claude
from core.knowledge_base import kb_manager
from agents.ava import ava


class OnboardingStep(str, Enum):
    INTAKE = "intake"
    INGESTION = "ingestion"
    TRAINING = "training"
    DEPLOYMENT = "deployment"
    LIVE = "live"


@dataclass
class OnboardingSession:
    session_id: str
    client_id: str
    client_name: str
    industry: str
    business_name: str
    contact_name: str
    contact_email: str
    step: OnboardingStep = OnboardingStep.INTAKE
    documents_ingested: int = 0
    agents_configured: list[str] = field(default_factory=list)
    vapi_assistant_id: str = ""
    deployment_notes: str = ""
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: str = ""
    errors: list[str] = field(default_factory=list)


class OnboardingWorkflow:
    """
    Automates the full SYN Systems client onboarding.
    Step 01 → 02 → 03 in 48 hours.
    """

    async def run(
        self,
        client_name: str,
        industry: str,
        business_name: str,
        contact_name: str,
        contact_email: str,
        document_texts: Optional[list[dict]] = None,
        agents_to_deploy: Optional[list[str]] = None,
    ) -> OnboardingSession:
        """
        Run the full onboarding pipeline.
        document_texts: list of {"title": str, "type": str, "text": str}
        agents_to_deploy: ["ava", "lead_capture", "sales_followup", "content_seo", "ai_auditor"]
        """
        client_id = client_name.lower().replace(" ", "_")[:20]
        session = OnboardingSession(
            session_id=f"onboard_{client_id}_{datetime.now().strftime('%Y%m%d%H%M')}",
            client_id=client_id,
            client_name=client_name,
            industry=industry,
            business_name=business_name,
            contact_name=contact_name,
            contact_email=contact_email,
        )

        logger.info(f"Starting onboarding: {client_name} | {industry}")

        # ── STEP 01: Ingest Documents ─────────────────────────────
        session.step = OnboardingStep.INGESTION
        logger.info("Step 01: Ingesting documents...")

        try:
            kb_manager.create_client(client_id, client_name, industry)

            if document_texts:
                for doc in document_texts:
                    kb_manager.ingest_document(
                        client_id=client_id,
                        doc_type=doc.get("type", "sop"),
                        title=doc.get("title", "Untitled"),
                        text=doc.get("text", ""),
                    )
                    session.documents_ingested += 1
            else:
                # Generate a starter KB from business description
                starter_content = self._generate_starter_kb(client_name, industry, business_name)
                kb_manager.ingest_document(
                    client_id=client_id,
                    doc_type="brand_voice",
                    title=f"{client_name} — AI-Generated Starter Guide",
                    text=starter_content,
                )
                session.documents_ingested = 1

            logger.info(f"Step 01 complete: {session.documents_ingested} documents ingested")
        except Exception as e:
            session.errors.append(f"Ingestion error: {str(e)}")
            logger.error(f"Ingestion failed: {e}")

        # ── STEP 02: Train Agents ─────────────────────────────────
        session.step = OnboardingStep.TRAINING
        logger.info("Step 02: Training agents...")

        agents = agents_to_deploy or ["ava", "lead_capture"]
        kb = kb_manager.load(client_id)
        kb_instructions = kb.agent_instructions if kb else ""

        for agent_name in agents:
            try:
                if agent_name == "ava":
                    vapi_config = ava.generate_vapi_config(
                        business_name=business_name,
                        industry=industry,
                        kb_instructions=kb_instructions,
                    )
                    session.agents_configured.append("AVA (AI Receptionist)")
                    logger.debug(f"AVA config generated for {business_name}")
                elif agent_name == "lead_capture":
                    session.agents_configured.append("Lead Capture Agent")
                elif agent_name == "sales_followup":
                    session.agents_configured.append("Sales Follow-Up Agent")
                elif agent_name == "content_seo":
                    session.agents_configured.append("Content & SEO Agent")
                elif agent_name == "ai_auditor":
                    session.agents_configured.append("AI Auditor")
            except Exception as e:
                session.errors.append(f"Training error ({agent_name}): {str(e)}")

        logger.info(f"Step 02 complete: {len(session.agents_configured)} agents configured")

        # ── STEP 03: Deploy ───────────────────────────────────────
        session.step = OnboardingStep.DEPLOYMENT
        logger.info("Step 03: Deploying agents...")

        deployment_notes = claude.chat(
            system_prompt=(
                "You are SYN Systems' deployment specialist. "
                "Write clear deployment checklists and go-live summaries."
            ),
            user_message=(
                f"Generate a deployment summary for:\n"
                f"Client: {client_name}\n"
                f"Industry: {industry}\n"
                f"Agents Deployed: {', '.join(session.agents_configured)}\n"
                f"Documents Ingested: {session.documents_ingested}\n\n"
                "Include: what's live, integration steps needed (Zapier, phone number), "
                "first 48hr monitoring focus, and expected outcomes."
            ),
            max_tokens=400,
        )
        session.deployment_notes = deployment_notes

        session.step = OnboardingStep.LIVE
        session.completed_at = datetime.utcnow().isoformat()
        logger.info(f"Onboarding complete: {client_name} | {len(session.agents_configured)} agents live")

        return session

    def _generate_starter_kb(self, client_name: str, industry: str, business_name: str) -> str:
        """Generate a starter knowledge base document from basic business info."""
        return claude.chat(
            system_prompt=(
                "You are an AI business analyst. "
                "Create detailed operational knowledge base documents for AI agent training."
            ),
            user_message=(
                f"Create a comprehensive knowledge base document for AI agent training:\n\n"
                f"Business: {business_name}\n"
                f"Industry: {industry}\n\n"
                f"Include:\n"
                f"1. Standard operating procedures for {industry} businesses\n"
                f"2. Common customer enquiries and answers\n"
                f"3. Escalation guidelines\n"
                f"4. Professional communication style guide\n"
                f"5. Key services/offerings typical for {industry}\n\n"
                "This will be used to train AI agents. Be specific and practical."
            ),
            max_tokens=1000,
        )

    def format_completion_message(self, session: OnboardingSession) -> str:
        """Format onboarding completion message for Telegram."""
        status = "✅" if not session.errors else "⚠️"
        return (
            f"{status} *Onboarding Complete — {session.client_name}*\n\n"
            f"🏭 Industry: {session.industry}\n"
            f"📚 Documents Ingested: {session.documents_ingested}\n"
            f"🤖 Agents Configured: {len(session.agents_configured)}\n"
            f"  • " + "\n  • ".join(session.agents_configured) + "\n\n"
            f"*Deployment Notes:*\n_{session.deployment_notes[:400]}_\n\n"
            f"{'⚠️ Errors: ' + str(session.errors) if session.errors else '🚀 All systems go!'}\n"
            f"_Session: {session.session_id}_"
        )


onboarding = OnboardingWorkflow()
