"""
SYN Systems — Telegram Bot
Central control & comms hub for all AI agents.

Commands:
  /start        — Welcome & menu
  /lead         — Submit a new lead manually
  /status       — System status across all agents
  /report       — Generate instant performance report
  /ask          — Ask Claude anything (admin Q&A)
  /content      — Trigger content generation
  /audit        — Trigger financial audit
  /kb           — Knowledge base management
  /help         — Full command reference
"""

import asyncio
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from loguru import logger
from core.config import settings
from core.claude_client import claude

# ── Conversation states ────────────────────────────────────────────
LEAD_NAME, LEAD_EMAIL, LEAD_PHONE, LEAD_INDUSTRY, LEAD_PAIN, LEAD_BUDGET = range(6)
CONTENT_TOPIC, CONTENT_TYPE, CONTENT_TARGET = range(6, 9)
KB_CLIENT, KB_DOC_TYPE = range(9, 11)


# ── Auth guard ────────────────────────────────────────────────────
def admin_only(func):
    """Decorator: restrict handler to admin chat ID."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = str(update.effective_chat.id)
        if chat_id != settings.telegram_admin_chat_id:
            await update.message.reply_text("Access denied.")
            return
        return await func(update, context)
    return wrapper


# ── Helpers ───────────────────────────────────────────────────────
async def send_alert(app: Application, message: str, parse_mode: str = "Markdown"):
    """Send an alert to the admin chat."""
    chat_id = settings.telegram_alert_chat_id or settings.telegram_admin_chat_id
    await app.bot.send_message(chat_id=chat_id, text=message, parse_mode=parse_mode)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📥 New Lead", callback_data="menu_lead"),
            InlineKeyboardButton("📊 Report", callback_data="menu_report"),
        ],
        [
            InlineKeyboardButton("✍️ Content", callback_data="menu_content"),
            InlineKeyboardButton("🔍 Audit", callback_data="menu_audit"),
        ],
        [
            InlineKeyboardButton("📚 Knowledge Base", callback_data="menu_kb"),
            InlineKeyboardButton("⚙️ Status", callback_data="menu_status"),
        ],
        [
            InlineKeyboardButton("🤖 Ask Claude", callback_data="menu_ask"),
        ],
    ])


# ── Command Handlers ─────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "*SYN Systems — AI Control Centre* 🧠\n\n"
        "All your AI agents are live and ready.\n"
        "Choose an action below or use a command:\n"
    )
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "*SYN Systems Bot — Commands*\n\n"
        "`/start` — Main menu\n"
        "`/lead` — Add a new lead\n"
        "`/status` — Agent status overview\n"
        "`/report` — Generate performance report\n"
        "`/ask <question>` — Ask Claude directly\n"
        "`/content` — Generate content piece\n"
        "`/audit` — Run financial audit\n"
        "`/kb` — Manage knowledge base\n"
        "`/help` — This message\n"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now().strftime("%d %b %Y, %H:%M AEST")
    status_text = (
        f"*SYN Systems — Agent Status*\n`{now}`\n\n"
        "🟢 *AVA* (AI Receptionist) — Online\n"
        "🟢 *Lead Capture Agent* — Monitoring\n"
        "🟢 *Sales Follow-Up Agent* — Active\n"
        "🟢 *Content & SEO Agent* — Ready\n"
        "🟢 *AI Auditor* — Scheduled\n"
        "🟢 *Knowledge Base* — Indexed\n\n"
        "_All systems operational._"
    )
    await update.message.reply_text(status_text, parse_mode="Markdown")


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Generating report...", parse_mode="Markdown")
    prompt = (
        "Generate a concise daily performance report for a SYN Systems AI agency. "
        "Include: leads captured today (simulate 3-8), conversion rate, calls handled by AVA, "
        "invoices chased, content pieces published, and a brief health summary. "
        "Format nicely for Telegram with emoji. Keep it under 300 words."
    )
    report = claude.chat(
        system_prompt="You are the SYN Systems reporting agent. Generate realistic, professional performance summaries.",
        user_message=prompt,
        max_tokens=512,
    )
    await update.message.reply_text(f"📊 *Daily Report*\n\n{report}", parse_mode="Markdown")


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/ask <your question>`", parse_mode="Markdown")
        return
    question = " ".join(context.args)
    await update.message.reply_text("🤔 Thinking...", parse_mode="Markdown")
    answer = claude.chat(
        system_prompt=(
            "You are the SYN Systems AI assistant. You know everything about the business: "
            "AI agents (AVA, Lead Capture, Sales Follow-Up, Content & SEO, AI Auditor), "
            "client industries (B2B, Healthcare, SaaS, Tech, Real Estate, E-commerce), "
            "integrations (HubSpot, Salesforce, Xero, Stripe, Zapier, Calendly), "
            "and the 3-step onboarding process (Ingest, Train, Deploy). "
            "Answer helpfully and concisely."
        ),
        user_message=question,
        max_tokens=1024,
    )
    await update.message.reply_text(f"🤖 {answer}", parse_mode="Markdown")


# ── Lead Capture Conversation ─────────────────────────────────────
async def lead_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📥 *New Lead — Step 1/6*\n\nWhat is the lead's full name?",
        parse_mode="Markdown",
    )
    return LEAD_NAME


async def lead_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["lead"] = {"name": update.message.text}
    await update.message.reply_text("📧 *Step 2/6* — Email address?", parse_mode="Markdown")
    return LEAD_EMAIL


async def lead_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["lead"]["email"] = update.message.text
    await update.message.reply_text("📱 *Step 3/6* — Phone number?", parse_mode="Markdown")
    return LEAD_PHONE


async def lead_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["lead"]["phone"] = update.message.text
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("B2B Services", callback_data="ind_b2b"),
         InlineKeyboardButton("Healthcare", callback_data="ind_health")],
        [InlineKeyboardButton("SaaS", callback_data="ind_saas"),
         InlineKeyboardButton("Technology", callback_data="ind_tech")],
        [InlineKeyboardButton("Real Estate", callback_data="ind_realestate"),
         InlineKeyboardButton("E-commerce", callback_data="ind_ecom")],
    ])
    await update.message.reply_text(
        "🏭 *Step 4/6* — Industry?", reply_markup=keyboard, parse_mode="Markdown"
    )
    return LEAD_INDUSTRY


async def lead_industry_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    industry_map = {
        "ind_b2b": "B2B Services", "ind_health": "Healthcare",
        "ind_saas": "SaaS", "ind_tech": "Technology",
        "ind_realestate": "Real Estate", "ind_ecom": "E-commerce",
    }
    context.user_data["lead"]["industry"] = industry_map.get(query.data, "Unknown")
    await query.edit_message_text(
        "😤 *Step 5/6* — What is their main pain point or challenge?",
        parse_mode="Markdown",
    )
    return LEAD_PAIN


async def lead_pain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["lead"]["pain_point"] = update.message.text
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("< $1k/mo", callback_data="bud_low"),
         InlineKeyboardButton("$1k–$5k/mo", callback_data="bud_mid")],
        [InlineKeyboardButton("$5k–$15k/mo", callback_data="bud_high"),
         InlineKeyboardButton("$15k+/mo", callback_data="bud_enterprise")],
    ])
    await update.message.reply_text(
        "💰 *Step 6/6* — Monthly budget range?",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    return LEAD_BUDGET


async def lead_budget_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    budget_map = {
        "bud_low": "< $1k/mo", "bud_mid": "$1k–$5k/mo",
        "bud_high": "$5k–$15k/mo", "bud_enterprise": "$15k+/mo",
    }
    context.user_data["lead"]["budget"] = budget_map.get(query.data, "Unknown")
    lead = context.user_data["lead"]

    # Qualify the lead with Claude
    qualification = claude.chat(
        system_prompt=(
            "You are SYN Systems' lead qualification AI. "
            "Score leads from 1-10 and provide a brief qualification summary (2-3 sentences). "
            "Higher scores for: larger budgets, clear pain points, industries SYN Systems serves well. "
            "Format: Score: X/10\nSummary: [your summary]\nRecommended action: [Call/Email/Nurture/Pass]"
        ),
        user_message=json.dumps(lead),
        max_tokens=200,
        temperature=0.3,
    )

    score_line = qualification.split("\n")[0] if qualification else "Score: N/A"
    summary = f"""
✅ *Lead Captured*

👤 {lead.get('name')}
📧 {lead.get('email')}
📱 {lead.get('phone')}
🏭 {lead.get('industry')}
😤 _{lead.get('pain_point')}_
💰 {lead.get('budget')}

*AI Qualification:*
{qualification}
"""
    await query.edit_message_text(summary, parse_mode="Markdown")
    logger.info(f"New lead captured: {lead.get('name')} | {lead.get('industry')} | {score_line}")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ── Content Generation Conversation ──────────────────────────────
async def content_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Blog Post", callback_data="ct_blog"),
         InlineKeyboardButton("LinkedIn Post", callback_data="ct_linkedin")],
        [InlineKeyboardButton("Email Sequence", callback_data="ct_email"),
         InlineKeyboardButton("Ad Copy", callback_data="ct_ad")],
        [InlineKeyboardButton("Case Study", callback_data="ct_casestudy"),
         InlineKeyboardButton("SEO Article", callback_data="ct_seo")],
    ])
    await update.message.reply_text(
        "✍️ *Content Agent* — What type of content?",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    return CONTENT_TYPE


async def content_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    type_map = {
        "ct_blog": "Blog Post", "ct_linkedin": "LinkedIn Post",
        "ct_email": "Email Sequence", "ct_ad": "Ad Copy",
        "ct_casestudy": "Case Study", "ct_seo": "SEO Article",
    }
    context.user_data["content_type"] = type_map.get(query.data, "Blog Post")
    await query.edit_message_text(
        f"*Content Type:* {context.user_data['content_type']}\n\n"
        "What topic or keyword should this cover?",
        parse_mode="Markdown",
    )
    return CONTENT_TOPIC


async def content_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["content_topic"] = update.message.text
    await update.message.reply_text("Who is the target audience?", parse_mode="Markdown")
    return CONTENT_TARGET


async def content_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.message.text
    content_type = context.user_data.get("content_type", "Blog Post")
    topic = context.user_data.get("content_topic", "AI automation")
    await update.message.reply_text("⏳ Generating content...", parse_mode="Markdown")

    content = claude.chat(
        system_prompt=(
            "You are SYN Systems' Content & SEO Agent. You create high-quality, "
            "conversion-focused content for AI automation services targeting Australian businesses. "
            "Write in a confident, expert tone. Always include a strong CTA."
        ),
        user_message=(
            f"Create a {content_type} about '{topic}' targeting {target}. "
            f"Make it compelling, SEO-optimised, and tailored for SYN Systems' brand. "
            f"Include a headline, body, and CTA."
        ),
        max_tokens=1500,
    )

    # Split if too long for one Telegram message
    if len(content) > 4000:
        await update.message.reply_text(content[:4000], parse_mode="Markdown")
        await update.message.reply_text(content[4000:], parse_mode="Markdown")
    else:
        await update.message.reply_text(f"✍️ *Generated {content_type}*\n\n{content}", parse_mode="Markdown")
    return ConversationHandler.END


# ── Audit Command ─────────────────────────────────────────────────
async def audit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 *AI Auditor* — Running financial scan...", parse_mode="Markdown")
    audit = claude.chat(
        system_prompt=(
            "You are SYN Systems' AI Auditor — a financial intelligence agent. "
            "Analyse financial health, flag overdue invoices, and provide actionable recommendations."
        ),
        user_message=(
            "Simulate a financial audit for a SYN Systems client. "
            "Include: outstanding invoices (3–7 items), cash flow status, discrepancies found, "
            "and recommended actions. Format clearly for Telegram with amounts in AUD."
        ),
        max_tokens=800,
    )
    await update.message.reply_text(f"🔍 *Financial Audit Report*\n\n{audit}", parse_mode="Markdown")


# ── Knowledge Base Command ────────────────────────────────────────
async def kb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Upload Document", callback_data="kb_upload"),
         InlineKeyboardButton("🔎 Search KB", callback_data="kb_search")],
        [InlineKeyboardButton("📋 List Clients", callback_data="kb_list"),
         InlineKeyboardButton("🗑 Remove Entry", callback_data="kb_remove")],
    ])
    await update.message.reply_text(
        "📚 *Knowledge Base Manager*\n\nSelect an action:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


async def kb_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "kb_list":
        await query.edit_message_text(
            "📋 *Active Knowledge Bases*\n\n"
            "1. Apex Consulting — B2B Services ✅\n"
            "2. MedCare Clinics — Healthcare ✅\n"
            "3. GrowthLab — SaaS ✅\n"
            "4. TechStart — Technology ✅\n"
            "5. Urban Property Group — Real Estate ✅\n"
            "6. RetailMax — E-commerce ✅\n",
            parse_mode="Markdown",
        )
    elif query.data == "kb_upload":
        await query.edit_message_text(
            "📤 Send me the document (PDF, DOCX, or paste text) and I'll ingest it into the knowledge base.",
            parse_mode="Markdown",
        )
    elif query.data == "kb_search":
        await query.edit_message_text(
            "🔎 Send me a query and I'll search the knowledge base for relevant information.",
            parse_mode="Markdown",
        )
    elif query.data == "kb_remove":
        await query.edit_message_text(
            "🗑 Send me the client name to remove their knowledge base entry.",
            parse_mode="Markdown",
        )


# ── Inline Menu Callbacks ─────────────────────────────────────────
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    routing = {
        "menu_lead": "/lead — Use /lead to add a new lead.",
        "menu_report": None,
        "menu_content": "/content — Use /content to generate content.",
        "menu_audit": None,
        "menu_kb": "/kb — Use /kb to manage the knowledge base.",
        "menu_status": None,
        "menu_ask": "/ask <question> — Use /ask followed by your question.",
    }
    if query.data == "menu_report":
        await query.edit_message_text("⏳ Generating report...")
        prompt = "Generate a brief daily performance summary for SYN Systems AI agents with emoji. Under 200 words."
        report = claude.chat(
            system_prompt="You are the SYN Systems reporting agent.",
            user_message=prompt,
            max_tokens=400,
        )
        await query.edit_message_text(f"📊 *Report*\n\n{report}", parse_mode="Markdown")
    elif query.data == "menu_status":
        now = datetime.now().strftime("%d %b %Y, %H:%M")
        await query.edit_message_text(
            f"*Status — {now}*\n\n🟢 All 5 agents operational.",
            parse_mode="Markdown",
        )
    elif query.data == "menu_audit":
        await query.edit_message_text("🔍 Running audit — use /audit for full report.")
    else:
        msg = routing.get(query.data, "Unknown action.")
        if msg:
            await query.edit_message_text(msg)


# ── General message handler ───────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pass any unhandled message to Claude as a general assistant query."""
    text = update.message.text
    response = claude.chat(
        system_prompt=(
            "You are the SYN Systems AI assistant embedded in a Telegram bot. "
            "Help the admin with questions about leads, agents, clients, and operations. "
            "Be concise — Telegram messages should be under 500 words."
        ),
        user_message=text,
        max_tokens=600,
    )
    await update.message.reply_text(response, parse_mode="Markdown")


# ── App Builder ───────────────────────────────────────────────────
def build_app() -> Application:
    app = Application.builder().token(settings.telegram_bot_token).build()

    # Lead capture conversation
    lead_conv = ConversationHandler(
        entry_points=[CommandHandler("lead", lead_command)],
        states={
            LEAD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, lead_name)],
            LEAD_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, lead_email)],
            LEAD_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, lead_phone)],
            LEAD_INDUSTRY: [CallbackQueryHandler(lead_industry_callback, pattern="^ind_")],
            LEAD_PAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, lead_pain)],
            LEAD_BUDGET: [CallbackQueryHandler(lead_budget_callback, pattern="^bud_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Content generation conversation
    content_conv = ConversationHandler(
        entry_points=[CommandHandler("content", content_command)],
        states={
            CONTENT_TYPE: [CallbackQueryHandler(content_type_callback, pattern="^ct_")],
            CONTENT_TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, content_topic)],
            CONTENT_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, content_target)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(lead_conv)
    app.add_handler(content_conv)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CommandHandler("ask", ask_command))
    app.add_handler(CommandHandler("audit", audit_command))
    app.add_handler(CommandHandler("kb", kb_command))
    app.add_handler(CallbackQueryHandler(kb_callback, pattern="^kb_"))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Telegram bot handlers registered.")
    return app


if __name__ == "__main__":
    app = build_app()
    logger.info("Starting SYN Systems Telegram bot...")
    app.run_polling(drop_pending_updates=True)
