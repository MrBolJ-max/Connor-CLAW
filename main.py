"""
SYN Systems — Connor-CLAW
AI Workforce Platform

Entry point. Starts:
  - FastAPI server (webhooks, API)
  - Telegram bot (polling or webhook mode)
  - APScheduler (automated reports)

Deployment modes:
  - Local / Railway:  python main.py all   (polling + API + scheduler)
  - Vercel:           ASGI app exported as `app` (webhook mode for Telegram)
"""

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from loguru import logger
import uvicorn
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from agents.lead_capture import handle_webhook as handle_lead_webhook
from workflows.reporting import setup_scheduler, reporting


# ── Logging ───────────────────────────────────────────────────────
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
    level=settings.log_level,
)
# File logging only when not on Vercel (read-only filesystem)
if not os.environ.get("VERCEL"):
    try:
        os.makedirs("data/logs", exist_ok=True)
        logger.add(
            "data/logs/synsystems_{time:YYYY-MM-DD}.log",
            rotation="1 day",
            retention="30 days",
            level="DEBUG",
        )
    except Exception:
        pass


# ── App Lifespan ──────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== SYN Systems — Connor-CLAW Starting ===")

    # Scheduler only runs on persistent deployments (Railway, local)
    # Vercel is serverless — no persistent process for cron jobs
    scheduler = None
    if not os.environ.get("VERCEL"):
        scheduler = setup_scheduler()
        scheduler.start()
        logger.info("Scheduler started")
    else:
        logger.info("Vercel mode — scheduler disabled (use Vercel Cron or Railway for reports)")

    yield

    if scheduler:
        scheduler.shutdown(wait=False)
    logger.info("=== SYN Systems — Shutting Down ===")


# ── FastAPI App ───────────────────────────────────────────────────
app = FastAPI(
    title="SYN Systems — Connor-CLAW",
    description="AI Workforce Platform — Lead Capture, AVA, Auditor, Content & SEO",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health Check ─────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "operational",
        "version": "1.0.0",
        "agents": ["ava", "lead_capture", "sales_followup", "content_seo", "ai_auditor"],
        "env": settings.app_env,
    }


# ── Lead Capture Webhooks ─────────────────────────────────────────
@app.post("/webhook/lead")
async def webhook_lead(request: Request, background_tasks: BackgroundTasks):
    """
    Universal lead capture webhook.
    Accepts leads from web forms, Zapier, Make, Facebook, Google Ads.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    source = request.headers.get("X-Lead-Source", "web_form")
    background_tasks.add_task(handle_lead_webhook, payload, source)
    return {"status": "received", "message": "Lead is being processed"}


@app.post("/webhook/facebook-lead")
async def webhook_facebook(request: Request, background_tasks: BackgroundTasks):
    """Facebook Lead Ads webhook."""
    payload = await request.json()
    entry = payload.get("entry", [{}])[0]
    changes = entry.get("changes", [{}])[0]
    lead_data = changes.get("value", {})

    normalized = {
        "name": lead_data.get("full_name", ""),
        "email": lead_data.get("email", ""),
        "phone": lead_data.get("phone_number", ""),
        "pain_point": lead_data.get("custom_disclaimer", ""),
    }
    background_tasks.add_task(handle_lead_webhook, normalized, "facebook")
    return {"status": "received"}


@app.post("/webhook/zapier")
async def webhook_zapier(request: Request, background_tasks: BackgroundTasks):
    """Zapier webhook — accepts any mapped payload."""
    payload = await request.json()
    background_tasks.add_task(handle_lead_webhook, payload, "zapier")
    return {"status": "received"}


# ── AVA Voice Webhooks (VAPI) ─────────────────────────────────────
@app.post("/webhook/ava/call-start")
async def ava_call_start(request: Request):
    """VAPI calls this when a call begins."""
    payload = await request.json()
    call_id = payload.get("call", {}).get("id", "unknown")
    logger.info(f"AVA call started: {call_id}")
    return {"status": "ok"}


@app.post("/webhook/ava/call-end")
async def ava_call_end(request: Request, background_tasks: BackgroundTasks):
    """VAPI calls this when a call ends — process summary and log to CRM."""
    payload = await request.json()
    call_id = payload.get("call", {}).get("id", "unknown")
    duration = payload.get("call", {}).get("duration", 0)
    logger.info(f"AVA call ended: {call_id} | Duration: {duration}s")
    return {"status": "ok"}


# ── Report Endpoints ──────────────────────────────────────────────
@app.get("/report/daily")
async def get_daily_report():
    """Generate and return daily report on demand."""
    report = reporting.build_report("daily")
    return {
        "period": report.period,
        "overall_health": report.overall_health,
        "total_leads": report.total_leads,
        "total_hot_leads": report.total_hot_leads,
        "total_bookings": report.total_bookings,
        "total_revenue_recovered": report.total_revenue_recovered,
        "highlights": report.highlights,
        "warnings": report.warnings,
        "ai_commentary": report.ai_commentary,
    }


@app.get("/report/weekly")
async def get_weekly_report():
    """Generate and return weekly report on demand."""
    report = reporting.build_report("weekly")
    return {
        "period": report.period,
        "overall_health": report.overall_health,
        "total_leads": report.total_leads,
        "highlights": report.highlights,
        "ai_commentary": report.ai_commentary,
    }


# ── Telegram Webhook (Vercel / serverless mode) ───────────────────
_telegram_app = None

async def _get_telegram_app():
    """Lazy-init the Telegram Application for webhook mode."""
    global _telegram_app
    if _telegram_app is None:
        from integrations.telegram_bot import build_app
        _telegram_app = build_app()
        await _telegram_app.initialize()
    return _telegram_app


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """
    Telegram sends updates here when running in webhook mode (Vercel).
    Set the webhook via:
      https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<your-vercel-url>/webhook/telegram
    """
    try:
        from telegram import Update
        data = await request.json()
        tg_app = await _get_telegram_app()
        update = Update.de_json(data, tg_app.bot)
        await tg_app.process_update(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Telegram webhook error: {e}")
        return {"ok": False, "error": str(e)}


# ── Telegram Bot (separate process — polling mode) ────────────────
def run_telegram_bot():
    """Run the Telegram bot in polling mode (separate from FastAPI)."""
    from integrations.telegram_bot import build_app
    bot_app = build_app()
    logger.info("Telegram bot starting in polling mode...")
    bot_app.run_polling(drop_pending_updates=True)


# ── Entry Points ──────────────────────────────────────────────────
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "api"

    if mode == "telegram":
        run_telegram_bot()
    elif mode == "api":
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=settings.app_port,
            reload=settings.app_env == "development",
            log_level=settings.log_level.lower(),
        )
    elif mode == "all":
        import threading
        t = threading.Thread(target=run_telegram_bot, daemon=True)
        t.start()
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=settings.app_port,
            log_level=settings.log_level.lower(),
        )
    else:
        print("Usage: python main.py [api|telegram|all]")
        sys.exit(1)
