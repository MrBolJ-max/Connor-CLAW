"""
SYN Systems — Automated Reporting & Monitoring
Generates daily, weekly, and monthly performance reports
across all AI agents. Delivers via Telegram on schedule.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import httpx
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from core.claude_client import claude
from core.config import settings

REPORTS_DIR = Path(__file__).parent.parent / "data" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class AgentMetrics:
    agent_name: str
    calls_handled: int = 0
    leads_captured: int = 0
    leads_qualified: int = 0
    hot_leads: int = 0
    emails_sent: int = 0
    content_pieces: int = 0
    invoices_chased: int = 0
    revenue_recovered_aud: float = 0.0
    bookings_made: int = 0
    resolution_rate_pct: float = 0.0
    conversion_rate_pct: float = 0.0


@dataclass
class SystemReport:
    period: str
    period_type: str   # daily, weekly, monthly
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    agent_metrics: list[AgentMetrics] = field(default_factory=list)
    total_leads: int = 0
    total_hot_leads: int = 0
    total_revenue_recovered: float = 0.0
    total_bookings: int = 0
    overall_health: str = "Healthy"
    highlights: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    ai_commentary: str = ""


class ReportingEngine:
    """
    Automated reporting engine.
    Collects metrics from all agents, generates AI commentary,
    and delivers reports to Telegram on schedule.
    """

    def _load_metrics_from_logs(self, since_hours: int = 24) -> list[AgentMetrics]:
        """
        In production: query DB/Redis for real metrics.
        Here we generate realistic simulated metrics for demonstration.
        """
        agents = [
            AgentMetrics(
                agent_name="AVA (AI Receptionist)",
                calls_handled=max(0, 23 + (hash(datetime.now().date()) % 10)),
                bookings_made=max(0, 8 + (hash(datetime.now().date()) % 5)),
                resolution_rate_pct=94.5 + (hash(datetime.now().date()) % 5) * 0.2,
            ),
            AgentMetrics(
                agent_name="Lead Capture Agent",
                leads_captured=max(0, 12 + (hash(datetime.now().date()) % 8)),
                leads_qualified=max(0, 9 + (hash(datetime.now().date()) % 5)),
                hot_leads=max(0, 3 + (hash(datetime.now().date()) % 3)),
                conversion_rate_pct=72.0 + (hash(datetime.now().date()) % 8),
            ),
            AgentMetrics(
                agent_name="Sales Follow-Up Agent",
                emails_sent=max(0, 18 + (hash(datetime.now().date()) % 7)),
                leads_qualified=max(0, 4 + (hash(datetime.now().date()) % 4)),
                conversion_rate_pct=28.0 + (hash(datetime.now().date()) % 10),
            ),
            AgentMetrics(
                agent_name="Content & SEO Agent",
                content_pieces=max(0, 2 + (hash(datetime.now().date()) % 3)),
            ),
            AgentMetrics(
                agent_name="AI Auditor",
                invoices_chased=max(0, 5 + (hash(datetime.now().date()) % 4)),
                revenue_recovered_aud=max(0, 4200 + (hash(datetime.now().date()) % 3000)),
            ),
        ]
        return agents

    def build_report(self, period_type: str = "daily") -> SystemReport:
        """Build a full system performance report."""
        now = datetime.now()
        if period_type == "daily":
            period = now.strftime("%d %B %Y")
            since_hours = 24
        elif period_type == "weekly":
            week_start = now - timedelta(days=now.weekday())
            period = f"Week of {week_start.strftime('%d %B %Y')}"
            since_hours = 168
        else:
            period = now.strftime("%B %Y")
            since_hours = 720

        metrics = self._load_metrics_from_logs(since_hours)

        total_leads = sum(m.leads_captured for m in metrics)
        total_hot = sum(m.hot_leads for m in metrics)
        total_revenue = sum(m.revenue_recovered_aud for m in metrics)
        total_bookings = sum(m.bookings_made for m in metrics)
        avg_resolution = sum(m.resolution_rate_pct for m in metrics if m.resolution_rate_pct > 0)
        avg_resolution = avg_resolution / max(1, sum(1 for m in metrics if m.resolution_rate_pct > 0))

        highlights = []
        warnings = []

        if total_hot >= 3:
            highlights.append(f"{total_hot} hot leads generated — sales team notified")
        if total_revenue > 3000:
            highlights.append(f"${total_revenue:,.2f} AUD recovered by AI Auditor")
        if avg_resolution >= 93:
            highlights.append(f"AVA maintaining {avg_resolution:.1f}% first-call resolution")
        if total_bookings >= 5:
            highlights.append(f"{total_bookings} appointments booked automatically")

        if total_leads < 5:
            warnings.append("Lead capture below target — review ad spend / web traffic")
        if avg_resolution < 90:
            warnings.append("AVA resolution rate dropping — review escalation rules")

        overall_health = "Excellent" if len(warnings) == 0 and len(highlights) >= 2 else \
                        "Healthy" if len(warnings) == 0 else \
                        "Needs Attention" if len(warnings) == 1 else "Critical"

        ai_commentary = claude.chat(
            system_prompt=(
                "You are SYN Systems' performance analytics AI. "
                "Write brief, insightful commentary on agent performance. "
                "Be specific, actionable, and positive but honest."
            ),
            user_message=(
                f"Write a 3-sentence performance commentary for:\n"
                f"Period: {period} ({period_type})\n"
                f"Total Leads: {total_leads} ({total_hot} hot)\n"
                f"Revenue Recovered: ${total_revenue:,.2f} AUD\n"
                f"Bookings: {total_bookings}\n"
                f"AVA Resolution Rate: {avg_resolution:.1f}%\n"
                f"Highlights: {highlights}\n"
                f"Warnings: {warnings}\n"
                f"Overall Health: {overall_health}"
            ),
            max_tokens=200,
        )

        report = SystemReport(
            period=period,
            period_type=period_type,
            agent_metrics=metrics,
            total_leads=total_leads,
            total_hot_leads=total_hot,
            total_revenue_recovered=total_revenue,
            total_bookings=total_bookings,
            overall_health=overall_health,
            highlights=highlights,
            warnings=warnings,
            ai_commentary=ai_commentary,
        )

        self._save_report(report)
        return report

    def _save_report(self, report: SystemReport):
        filename = f"{report.period_type}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        path = REPORTS_DIR / filename
        path.write_text(json.dumps({
            "period": report.period,
            "period_type": report.period_type,
            "generated_at": report.generated_at,
            "total_leads": report.total_leads,
            "total_hot_leads": report.total_hot_leads,
            "total_revenue_recovered": report.total_revenue_recovered,
            "total_bookings": report.total_bookings,
            "overall_health": report.overall_health,
            "highlights": report.highlights,
            "warnings": report.warnings,
            "ai_commentary": report.ai_commentary,
        }, indent=2), encoding="utf-8")
        logger.info(f"Report saved: {filename}")

    def format_for_telegram(self, report: SystemReport) -> str:
        health_emoji = {
            "Excellent": "🌟", "Healthy": "✅",
            "Needs Attention": "⚠️", "Critical": "🚨"
        }.get(report.overall_health, "📊")

        metrics_lines = []
        for m in report.agent_metrics:
            parts = []
            if m.calls_handled:
                parts.append(f"{m.calls_handled} calls")
            if m.leads_captured:
                parts.append(f"{m.leads_captured} leads")
            if m.hot_leads:
                parts.append(f"🔥{m.hot_leads} hot")
            if m.emails_sent:
                parts.append(f"{m.emails_sent} emails")
            if m.content_pieces:
                parts.append(f"{m.content_pieces} pieces")
            if m.invoices_chased:
                parts.append(f"{m.invoices_chased} chased")
            if m.revenue_recovered_aud:
                parts.append(f"${m.revenue_recovered_aud:,.0f} recovered")
            if m.bookings_made:
                parts.append(f"{m.bookings_made} booked")
            if m.resolution_rate_pct:
                parts.append(f"{m.resolution_rate_pct:.0f}% resolved")
            if m.conversion_rate_pct:
                parts.append(f"{m.conversion_rate_pct:.0f}% conv.")
            line = f"  • *{m.agent_name}*: {', '.join(parts)}" if parts else f"  • *{m.agent_name}*: No activity"
            metrics_lines.append(line)

        highlights_text = "\n".join(f"  ✅ {h}" for h in report.highlights) or "  None"
        warnings_text = "\n".join(f"  ⚠️ {w}" for w in report.warnings) or "  None"

        return (
            f"{health_emoji} *SYN Systems — {report.period_type.title()} Report*\n"
            f"📅 {report.period}\n\n"
            f"*Agent Performance:*\n"
            f"{chr(10).join(metrics_lines)}\n\n"
            f"*Summary:*\n"
            f"  🎯 {report.total_leads} leads | 🔥 {report.total_hot_leads} hot\n"
            f"  📅 {report.total_bookings} bookings\n"
            f"  💰 ${report.total_revenue_recovered:,.0f} AUD recovered\n\n"
            f"*Highlights:*\n{highlights_text}\n\n"
            f"*Warnings:*\n{warnings_text}\n\n"
            f"*AI Commentary:*\n_{report.ai_commentary}_\n\n"
            f"Overall: *{report.overall_health}* {health_emoji}"
        )

    async def send_to_telegram(self, message: str):
        """Send a report to the admin Telegram chat."""
        if not (settings.telegram_bot_token and settings.telegram_admin_chat_id):
            logger.warning("Telegram not configured — printing report to stdout")
            print(message)
            return
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                    json={
                        "chat_id": settings.telegram_admin_chat_id,
                        "text": message,
                        "parse_mode": "Markdown",
                    },
                    timeout=10.0,
                )
                logger.info(f"Report sent to Telegram")
        except httpx.RequestError as e:
            logger.error(f"Telegram send failed: {e}")

    async def run_daily_report(self):
        """Scheduled job: generate and send daily report."""
        logger.info("Running daily report...")
        report = self.build_report("daily")
        message = self.format_for_telegram(report)
        await self.send_to_telegram(message)

    async def run_weekly_report(self):
        """Scheduled job: generate and send weekly report."""
        logger.info("Running weekly report...")
        report = self.build_report("weekly")
        message = self.format_for_telegram(report)
        await self.send_to_telegram(message)


def setup_scheduler() -> AsyncIOScheduler:
    """Configure and return the APScheduler instance."""
    engine = ReportingEngine()
    scheduler = AsyncIOScheduler(timezone="Australia/Sydney")

    # Daily report — 8:00 AM AEST
    scheduler.add_job(
        engine.run_daily_report,
        trigger="cron",
        hour=8,
        minute=0,
        id="daily_report",
        name="Daily Performance Report",
    )

    # Weekly report — Monday 8:30 AM AEST
    scheduler.add_job(
        engine.run_weekly_report,
        trigger="cron",
        day_of_week="mon",
        hour=8,
        minute=30,
        id="weekly_report",
        name="Weekly Performance Report",
    )

    logger.info("Scheduler configured: daily @ 08:00, weekly Mon @ 08:30 AEST")
    return scheduler


reporting = ReportingEngine()
