import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import database
from config import settings
from models import (
    AlertUpdate,
    BlacklistEntry,
    ConfigUpdate,
    SearchProfile,
)

logger = logging.getLogger(__name__)

app = FastAPI(title="Willhaben Flipper API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/alerts")
def list_alerts(
    page: int = Query(default=0, ge=0),
    page_size: int = Query(default=20, ge=1, le=100),
    min_score: Optional[int] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    user_action: Optional[str] = Query(default=None),
):
    alerts = database.get_alerts(
        page=page,
        page_size=page_size,
        min_score=min_score,
        date_from=date_from,
        date_to=date_to,
        user_action=user_action,
    )
    return {"alerts": alerts, "page": page, "page_size": page_size}


@app.get("/api/alerts/{alert_id}")
def get_alert(alert_id: int):
    alert = database.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@app.patch("/api/alerts/{alert_id}")
def update_alert(alert_id: int, body: AlertUpdate):
    alert = database.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    database.update_alert_action(alert_id, body.user_action)
    return {"ok": True}


@app.get("/api/price-history/{search_term}")
def price_history(search_term: str, days: int = Query(default=30, ge=1, le=365)):
    history = database.get_price_history(search_term, days)
    return {"search_term": search_term, "days": days, "history": history}


@app.get("/api/profiles")
def list_profiles():
    return {"profiles": database.get_profiles()}


@app.post("/api/profiles", status_code=201)
def create_profile(profile: SearchProfile):
    profile_id = database.create_profile(profile.model_dump(exclude={"id"}))
    return {"id": profile_id}


@app.patch("/api/profiles/{profile_id}")
def update_profile(profile_id: int, profile: SearchProfile):
    updates = profile.model_dump(exclude_none=True, exclude={"id"})
    database.update_profile(profile_id, updates)
    return {"ok": True}


@app.delete("/api/profiles/{profile_id}")
def delete_profile(profile_id: int):
    database.delete_profile(profile_id)
    return {"ok": True}


@app.get("/api/stats")
def get_stats():
    return database.get_stats()


@app.get("/api/config")
def get_config():
    return {
        "MAX_BUDGET_EUR": settings.MAX_BUDGET_EUR,
        "MIN_PROFIT_EUR": settings.MIN_PROFIT_EUR,
        "PRICE_THRESHOLD_PERCENT": settings.PRICE_THRESHOLD_PERCENT,
        "ROLLING_AVERAGE_DAYS": settings.ROLLING_AVERAGE_DAYS,
        "SCRAPE_INTERVAL_MINUTES": settings.SCRAPE_INTERVAL_MINUTES,
        "MIN_LISTING_IMAGES": settings.MIN_LISTING_IMAGES,
        "ALERT_COOLDOWN_HOURS": settings.ALERT_COOLDOWN_HOURS,
        "MAX_SELLER_LISTINGS": settings.MAX_SELLER_LISTINGS,
        "LOG_LEVEL": settings.LOG_LEVEL,
        "scraper_paused": settings.is_paused(),
    }


@app.patch("/api/config")
def update_config(body: ConfigUpdate):
    updates = body.model_dump(exclude_none=True)
    for key, value in updates.items():
        object.__setattr__(settings, key, value)
        settings.update_env_file(key, str(value))
    return {"ok": True, "updated": list(updates.keys())}


@app.get("/api/blacklist")
def list_blacklist():
    return {"blacklist": database.get_blacklist()}


@app.post("/api/blacklist", status_code=201)
def add_blacklist(entry: BlacklistEntry):
    database.add_to_blacklist(entry.seller_id, entry.reason)
    return {"ok": True}


@app.delete("/api/blacklist/{seller_id}")
def remove_blacklist(seller_id: str):
    database.remove_from_blacklist(seller_id)
    return {"ok": True}
