"""
SYN Systems — AI Auditor
Financial Intelligence Agent

Reviews financials, flags discrepancies, and chases invoices automatically.
Catches errors humans miss and keeps cash flow healthy.
23%+ more revenue collected on average.

Integrations: Xero, Stripe
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
import httpx
from loguru import logger
from core.claude_client import claude
from core.config import settings


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    OVERDUE = "overdue"
    PAID = "paid"
    DISPUTED = "disputed"
    WRITTEN_OFF = "written_off"


class DiscrepancyType(str, Enum):
    DUPLICATE_CHARGE = "duplicate_charge"
    MISSING_PAYMENT = "missing_payment"
    AMOUNT_MISMATCH = "amount_mismatch"
    OVERDUE_INVOICE = "overdue_invoice"
    UNUSUAL_EXPENSE = "unusual_expense"
    UNCATEGORISED = "uncategorised"


@dataclass
class Invoice:
    invoice_id: str
    client_name: str
    amount_aud: float
    status: InvoiceStatus
    due_date: str
    issued_date: str
    description: str = ""
    days_overdue: int = 0
    chase_count: int = 0
    last_chased: str = ""

    def is_overdue(self) -> bool:
        return self.status == InvoiceStatus.OVERDUE or self.days_overdue > 0

    def urgency(self) -> str:
        if self.days_overdue > 60:
            return "critical"
        if self.days_overdue > 30:
            return "high"
        if self.days_overdue > 7:
            return "medium"
        return "low"


@dataclass
class Discrepancy:
    discrepancy_id: str
    type: DiscrepancyType
    description: str
    amount_aud: Optional[float]
    severity: str  # low, medium, high, critical
    recommended_action: str
    auto_resolvable: bool = False
    resolved: bool = False


@dataclass
class AuditReport:
    client_name: str
    period: str
    total_revenue_aud: float
    total_outstanding_aud: float
    overdue_invoices: list[Invoice]
    discrepancies: list[Discrepancy]
    cash_flow_status: str
    ai_recommendations: list[str]
    recovery_potential_aud: float
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def summary(self) -> str:
        return (
            f"Audit: {self.client_name} | {self.period}\n"
            f"Outstanding: ${self.total_outstanding_aud:,.2f} AUD\n"
            f"Overdue invoices: {len(self.overdue_invoices)}\n"
            f"Discrepancies: {len(self.discrepancies)}\n"
            f"Recovery potential: ${self.recovery_potential_aud:,.2f} AUD\n"
            f"Cash flow: {self.cash_flow_status}"
        )


class AIAuditor:
    """
    Financial intelligence agent.
    Analyses Xero/Stripe data, flags issues, generates chase emails,
    and provides actionable financial recommendations.
    """

    SYSTEM_PROMPT = """You are SYN Systems' AI Auditor — a financial intelligence specialist.

You review business financials with the precision of a chartered accountant
combined with the pattern recognition of AI.

Your responsibilities:
- Identify overdue invoices and chase sequences
- Flag financial discrepancies and errors
- Monitor cash flow health
- Recommend actions to improve revenue collection
- Spot unusual transactions

Always be specific with amounts (AUD), dates, and action steps.
Prioritise by financial impact and urgency."""

    def analyse_invoices(self, invoices: list[Invoice]) -> list[Discrepancy]:
        """Detect discrepancies and anomalies in invoice data."""
        discrepancies = []
        seen_amounts = {}

        for inv in invoices:
            # Duplicate detection
            key = f"{inv.client_name}_{inv.amount_aud}"
            if key in seen_amounts:
                discrepancies.append(Discrepancy(
                    discrepancy_id=f"dup_{inv.invoice_id}",
                    type=DiscrepancyType.DUPLICATE_CHARGE,
                    description=f"Possible duplicate: {inv.client_name} ${inv.amount_aud:,.2f}",
                    amount_aud=inv.amount_aud,
                    severity="high",
                    recommended_action="Review both invoices — confirm if duplicate or valid separate charge",
                    auto_resolvable=False,
                ))
            else:
                seen_amounts[key] = inv.invoice_id

            # Overdue flag
            if inv.is_overdue():
                urgency = inv.urgency()
                discrepancies.append(Discrepancy(
                    discrepancy_id=f"overdue_{inv.invoice_id}",
                    type=DiscrepancyType.OVERDUE_INVOICE,
                    description=f"Overdue {inv.days_overdue}d: {inv.client_name} ${inv.amount_aud:,.2f}",
                    amount_aud=inv.amount_aud,
                    severity=urgency,
                    recommended_action=self._chase_action(inv),
                    auto_resolvable=True,
                ))

        return discrepancies

    def _chase_action(self, inv: Invoice) -> str:
        if inv.days_overdue > 60:
            return "Escalate to debt recovery / legal demand letter"
        if inv.days_overdue > 30:
            return "Phone call + formal notice"
        if inv.chase_count == 0:
            return "Send polite payment reminder email"
        return "Send firm follow-up email with payment link"

    def generate_chase_email(self, invoice: Invoice) -> dict:
        """Generate an invoice chase email tailored to urgency."""
        urgency_tone = {
            "low": "polite and friendly",
            "medium": "professional and firm",
            "high": "urgent and direct",
            "critical": "formal legal notice tone",
        }
        tone = urgency_tone.get(invoice.urgency(), "professional")

        result = claude.extract_json(
            system_prompt=self.SYSTEM_PROMPT,
            user_message=(
                f"Generate an invoice chase email.\n\n"
                f"Client: {invoice.client_name}\n"
                f"Amount: ${invoice.amount_aud:,.2f} AUD\n"
                f"Invoice ID: {invoice.invoice_id}\n"
                f"Days Overdue: {invoice.days_overdue}\n"
                f"Due Date: {invoice.due_date}\n"
                f"Description: {invoice.description}\n"
                f"Previous chase count: {invoice.chase_count}\n"
                f"Tone: {tone}\n\n"
                'Return JSON: {"subject": "...", "body": "...", "urgency": "..."}'
            ),
            max_tokens=400,
        )
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"subject": f"Invoice #{invoice.invoice_id} Overdue", "body": result, "urgency": invoice.urgency()}

    def generate_full_audit(
        self,
        client_name: str,
        invoices: list[Invoice],
        period: str = "Last 30 days",
        additional_context: str = "",
    ) -> AuditReport:
        """Run a complete financial audit for a client."""
        logger.info(f"Running financial audit: {client_name}")

        total_outstanding = sum(inv.amount_aud for inv in invoices if inv.status != InvoiceStatus.PAID)
        total_revenue = sum(inv.amount_aud for inv in invoices if inv.status == InvoiceStatus.PAID)
        overdue = [inv for inv in invoices if inv.is_overdue()]
        recovery_potential = sum(inv.amount_aud for inv in overdue)

        discrepancies = self.analyse_invoices(invoices)

        # AI analysis of overall financial health
        invoice_summary = json.dumps([{
            "id": inv.invoice_id,
            "client": inv.client_name,
            "amount": inv.amount_aud,
            "status": inv.status.value,
            "days_overdue": inv.days_overdue,
        } for inv in invoices[:20]])  # limit for token efficiency

        analysis = claude.chat(
            system_prompt=self.SYSTEM_PROMPT,
            user_message=(
                f"Analyse the financial health for: {client_name}\n"
                f"Period: {period}\n"
                f"Total Revenue (paid): ${total_revenue:,.2f} AUD\n"
                f"Total Outstanding: ${total_outstanding:,.2f} AUD\n"
                f"Overdue Invoices: {len(overdue)}\n"
                f"Recovery Potential: ${recovery_potential:,.2f} AUD\n"
                f"Discrepancies Found: {len(discrepancies)}\n"
                f"Invoice Data: {invoice_summary}\n"
                f"Additional Context: {additional_context}\n\n"
                "Provide: cash flow status (1 phrase), and 5 specific actionable recommendations. "
                "Be specific with AUD amounts and timeframes."
            ),
            max_tokens=500,
        )

        # Parse recommendations
        recommendations = [
            line.strip().lstrip("•-123456789. ")
            for line in analysis.split("\n")
            if line.strip() and len(line.strip()) > 10
        ][:7]

        cash_flow_status = recommendations[0] if recommendations else "Requires review"
        recommendations = recommendations[1:] if len(recommendations) > 1 else recommendations

        return AuditReport(
            client_name=client_name,
            period=period,
            total_revenue_aud=total_revenue,
            total_outstanding_aud=total_outstanding,
            overdue_invoices=overdue,
            discrepancies=discrepancies,
            cash_flow_status=cash_flow_status,
            ai_recommendations=recommendations,
            recovery_potential_aud=recovery_potential,
        )

    async def fetch_xero_invoices(self, tenant_id: str, access_token: str) -> list[dict]:
        """Fetch invoices from Xero API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.xero.com/api.xro/2.0/Invoices",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Xero-tenant-id": tenant_id,
                        "Accept": "application/json",
                    },
                    params={"Statuses": "AUTHORISED,OVERDUE", "page": 1},
                    timeout=15.0,
                )
                if response.status_code == 200:
                    return response.json().get("Invoices", [])
                logger.error(f"Xero error {response.status_code}")
                return []
        except httpx.RequestError as e:
            logger.error(f"Xero fetch failed: {e}")
            return []

    async def fetch_stripe_charges(self, limit: int = 100) -> list[dict]:
        """Fetch recent charges from Stripe."""
        if not settings.stripe_secret_key:
            return []
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.stripe.com/v1/charges",
                    auth=(settings.stripe_secret_key, ""),
                    params={"limit": limit},
                    timeout=15.0,
                )
                if response.status_code == 200:
                    return response.json().get("data", [])
                logger.error(f"Stripe error {response.status_code}")
                return []
        except httpx.RequestError as e:
            logger.error(f"Stripe fetch failed: {e}")
            return []

    def format_audit_for_telegram(self, report: AuditReport) -> str:
        """Format audit report for Telegram message."""
        overdue_lines = "\n".join(
            f"  • {inv.client_name}: ${inv.amount_aud:,.2f} ({inv.days_overdue}d overdue)"
            for inv in report.overdue_invoices[:5]
        )
        disc_lines = "\n".join(
            f"  • [{d.severity.upper()}] {d.description}"
            for d in report.discrepancies[:4]
        )
        recs = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(report.ai_recommendations[:4]))

        return (
            f"🔍 *Financial Audit — {report.client_name}*\n"
            f"📅 Period: {report.period}\n\n"
            f"💰 Revenue (paid): ${report.total_revenue_aud:,.2f} AUD\n"
            f"⏳ Outstanding: ${report.total_outstanding_aud:,.2f} AUD\n"
            f"🚨 Recovery potential: ${report.recovery_potential_aud:,.2f} AUD\n"
            f"📊 Cash flow: _{report.cash_flow_status}_\n\n"
            f"*Overdue Invoices ({len(report.overdue_invoices)}):*\n{overdue_lines or '  None'}\n\n"
            f"*Discrepancies ({len(report.discrepancies)}):*\n{disc_lines or '  None found'}\n\n"
            f"*AI Recommendations:*\n{recs}"
        )


auditor = AIAuditor()
