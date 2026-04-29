import asyncio
import logging
import logging.handlers
import sys

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import database
import analyzer
import scraper
import telegram_bot
from api import app as fastapi_app
from config import settings

# ── Logging setup ──────────────────────────────────────────────────────────────

def setup_logging():
    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    file_handler = logging.handlers.RotatingFileHandler(
        "flipper.log", maxBytes=5 * 1024 * 1024, backupCount=3
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(fmt)

    root.addHandler(file_handler)
    root.addHandler(console_handler)


logger = logging.getLogger(__name__)

# ── Scraper job ────────────────────────────────────────────────────────────────

async def scrape_job():
    if settings.is_paused():
        logger.info("Scraper is paused, skipping cycle")
        return

    profiles = database.get_active_profiles()
    if not profiles:
        logger.info("No active profiles, skipping scrape cycle")
        return

    logger.info(f"Starting scrape cycle for {len(profiles)} profiles")

    for profile in profiles:
        try:
            listings = await scraper.scrape_profile(profile)
            search_term = profile["query"]

            for listing in listings:
                is_new = database.upsert_listing(listing)
                database.add_price_history(search_term, listing["price"], listing["id"])

                if not is_new:
                    continue
                if not analyzer.should_alert(listing):
                    continue
                if database.was_recently_alerted(listing["id"], settings.ALERT_COOLDOWN_HOURS):
                    continue

                scored = analyzer.analyze_listing(listing, search_term)
                if scored is None:
                    continue

                alert_dict = {
                    "listing_id": scored.listing.id,
                    "title": scored.listing.title,
                    "price": scored.listing.price,
                    "url": scored.listing.url,
                    "score": scored.score,
                    "expected_profit": scored.expected_profit,
                    "rolling_average": scored.rolling_average,
                    "price_delta_percent": scored.price_delta_percent,
                    "location": scored.listing.location,
                    "images_count": scored.listing.images_count,
                    "age_minutes": scored.listing.age_minutes,
                }
                database.save_alert(alert_dict)
                await telegram_bot.send_alert(scored)
                logger.info(
                    f"Alert: '{scored.listing.title}' {scored.listing.price}€ "
                    f"(score={scored.score}, profit=~{scored.expected_profit:.0f}€)"
                )

        except Exception as e:
            logger.error(f"Error scraping profile '{profile.get('name')}': {e}", exc_info=True)

    logger.info("Scrape cycle complete")


# ── Startup banner ─────────────────────────────────────────────────────────────

def print_banner():
    profiles = database.get_active_profiles()
    print(
        "\n"
        "╔══════════════════════════════╗\n"
        "║   Willhaben Flipper v1.0     ║\n"
        "╠══════════════════════════════╣\n"
        f"║ Profile aktiv:    {len(profiles):<11}║\n"
        f"║ Scrape-Interval:  {settings.SCRAPE_INTERVAL_MINUTES} min        ║\n"
        f"║ Budget-Limit:     {settings.MAX_BUDGET_EUR:.0f}€        ║\n"
        f"║ Threshold:        {settings.PRICE_THRESHOLD_PERCENT:.0f}%         ║\n"
        f"║ DB:               {settings.DATABASE_PATH:<11}║\n"
        f"║ Dashboard:        :{settings.API_PORT:<5}        ║\n"
        "╚══════════════════════════════╝\n"
    )


# ── Main ───────────────────────────────────────────────────────────────────────

async def main():
    setup_logging()

    database.init_db()
    database.migrate()
    database.seed_default_profiles()

    print_banner()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        scrape_job,
        "interval",
        minutes=settings.SCRAPE_INTERVAL_MINUTES,
        id="scrape_job",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()

    uvicorn_config = uvicorn.Config(
        fastapi_app,
        host="0.0.0.0",
        port=settings.API_PORT,
        log_level="warning",
    )
    server = uvicorn.Server(uvicorn_config)

    tg_app = telegram_bot.create_application()

    async def run_uvicorn():
        await server.serve()

    async def run_telegram():
        if tg_app is None:
            return
        await tg_app.initialize()
        await tg_app.start()
        await tg_app.updater.start_polling(allowed_updates=["message", "callback_query"])
        logger.info("Telegram bot started")
        while True:
            await asyncio.sleep(3600)

    tasks = [
        asyncio.create_task(run_uvicorn(), name="uvicorn"),
        asyncio.create_task(run_telegram(), name="telegram"),
    ]

    await asyncio.sleep(5)
    await scrape_job()

    try:
        await asyncio.gather(*tasks)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
        scheduler.shutdown(wait=False)
        server.should_exit = True
        if tg_app:
            await tg_app.updater.stop()
            await tg_app.stop()
            await tg_app.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
