import logging
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

import asyncio
import database
from config import settings
from models import ScoredListing
from scraper import is_listing_active

logger = logging.getLogger(__name__)

_application: Optional[Application] = None


def _format_age(minutes: Optional[float]) -> str:
    if minutes is None:
        return "Unbekannt"
    if minutes < 60:
        return f"Vor {int(minutes)} Minuten"
    hours = int(minutes / 60)
    return f"Vor {hours} Stunden"


def _text_price_chart(history: list, rolling_avg: float) -> str:
    if not history:
        return "Keine Preishistorie verfügbar."
    prices = [h["price"] for h in history]
    min_p = min(prices)
    max_p = max(prices)
    span = max_p - min_p or 1
    bar_width = 20

    lines = [f"📊 Preishistorie (letzte {len(history)} Einträge)\n"]
    for entry in history[-10:]:
        p = entry["price"]
        filled = int((p - min_p) / span * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        lines.append(f"{p:6.0f}€ |{bar}|")
    lines.append(f"\nRolling Avg: {rolling_avg:.0f}€")
    lines.append(f"Min: {min_p:.0f}€  Max: {max_p:.0f}€")
    return "\n".join(lines)


def build_alert_message(scored: ScoredListing) -> str:
    listing = scored.listing
    age_str = _format_age(listing.age_minutes)
    return (
        f"🔥 Score: {scored.score}/100\n\n"
        f"{listing.title} — {listing.price:.0f}€\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Marktdurchschnitt: {scored.rolling_average:.0f}€\n"
        f"💰 Erwarteter Gewinn: ~{scored.expected_profit:.0f}€\n"
        f"📍 {listing.location or 'Ort unbekannt'}\n"
        f"🕐 {age_str} inseriert\n"
        f"🖼 {listing.images_count} Fotos\n\n"
        f"🔗 {listing.url}"
    )


def build_alert_keyboard(listing_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Interessiert", callback_data=f"action:interested:{listing_id}"),
            InlineKeyboardButton("❌ Skip", callback_data=f"action:skipped:{listing_id}"),
        ],
        [
            InlineKeyboardButton("📊 Preisdetails", callback_data=f"pricedetail:{listing_id}"),
        ],
    ])


async def send_alert(scored: ScoredListing):
    if not _application:
        logger.debug("Telegram not configured, skipping alert")
        return
    chat_id = settings.TELEGRAM_CHAT_ID
    if not chat_id:
        return
    active = await asyncio.to_thread(is_listing_active, scored.listing.url)
    if not active:
        database.mark_listing_inactive(scored.listing.id)
        logger.info(f"Skipped Telegram alert — listing gone: '{scored.listing.title}'")
        return
    text = build_alert_message(scored)
    keyboard = build_alert_keyboard(scored.listing.id)
    try:
        await _application.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=keyboard,
            disable_web_page_preview=False,
        )
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")


async def _cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    profiles = database.get_active_profiles()
    stats = database.get_stats()
    text = (
        f"📡 Willhaben Flipper Status\n\n"
        f"Aktive Profile: {len(profiles)}\n"
        f"Heute gesehen: {stats['today_seen']}\n"
        f"Heute Alerts: {stats['today_alerts']}\n"
        f"Scraper: {'⏸ Pausiert' if settings.is_paused() else '▶️ Aktiv'}"
    )
    await update.message.reply_text(text)


async def _cmd_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Verwendung: /budget <betrag>")
        return
    try:
        value = float(context.args[0])
        object.__setattr__(settings, "MAX_BUDGET_EUR", value)
        settings.update_env_file("MAX_BUDGET_EUR", str(value))
        await update.message.reply_text(f"✅ Budget auf {value:.0f}€ gesetzt")
    except ValueError:
        await update.message.reply_text("❌ Ungültiger Betrag")


async def _cmd_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Verwendung: /threshold <prozent>")
        return
    try:
        value = float(context.args[0])
        object.__setattr__(settings, "PRICE_THRESHOLD_PERCENT", value)
        settings.update_env_file("PRICE_THRESHOLD_PERCENT", str(value))
        await update.message.reply_text(f"✅ Threshold auf {value:.0f}% gesetzt")
    except ValueError:
        await update.message.reply_text("❌ Ungültiger Wert")


async def _cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings.pause()
    await update.message.reply_text("⏸ Scraper pausiert")


async def _cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings.resume()
    await update.message.reply_text("▶️ Scraper fortgesetzt")


async def _cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = database.get_stats()
    top = stats.get("top_search_terms", [])
    lines = ["📊 Top-Kategorien nach Alert-Rate (7 Tage)\n"]
    for i, t in enumerate(top, 1):
        lines.append(f"{i}. {t['search_term']} — {t['cnt']} Preise")
    if not top:
        lines.append("Noch keine Daten")
    await update.message.reply_text("\n".join(lines))


async def _cmd_blacklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Verwendung: /blacklist <seller_id>")
        return
    seller_id = context.args[0]
    database.add_to_blacklist(seller_id)
    await update.message.reply_text(f"✅ Seller {seller_id} zur Blacklist hinzugefügt")


async def _handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data.startswith("action:"):
        parts = data.split(":", 2)
        if len(parts) == 3:
            _, action, listing_id = parts
            alerts = database.get_alerts()
            alert_id = None
            for a in alerts:
                if a["listing_id"] == listing_id:
                    alert_id = a["id"]
                    break
            if alert_id:
                database.update_alert_action(alert_id, action)
                label = "✅ Als Interessiert markiert" if action == "interested" else "❌ Übersprungen"
                await query.edit_message_reply_markup(reply_markup=None)
                await query.message.reply_text(label)

    elif data.startswith("pricedetail:"):
        listing_id = data.split(":", 1)[1]
        alerts = database.get_alerts()
        rolling_avg = 0.0
        search_term = None
        for a in alerts:
            if a["listing_id"] == listing_id:
                rolling_avg = a.get("rolling_average", 0)
                break
        history = (
            database.get_price_history(search_term, 30)
            if search_term
            else database.get_price_history_by_listing(listing_id)
        )
        chart = _text_price_chart(history, rolling_avg)
        await query.message.reply_text(f"```\n{chart}\n```", parse_mode="Markdown")


def create_application() -> Optional[Application]:
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.warning("Telegram deaktiviert — kein TELEGRAM_BOT_TOKEN gesetzt")
        return None

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("status", _cmd_status))
    app.add_handler(CommandHandler("budget", _cmd_budget))
    app.add_handler(CommandHandler("threshold", _cmd_threshold))
    app.add_handler(CommandHandler("pause", _cmd_pause))
    app.add_handler(CommandHandler("resume", _cmd_resume))
    app.add_handler(CommandHandler("stats", _cmd_stats))
    app.add_handler(CommandHandler("blacklist", _cmd_blacklist))
    app.add_handler(CallbackQueryHandler(_handle_callback))

    global _application
    _application = app
    return app
