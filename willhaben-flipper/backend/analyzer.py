import logging
from datetime import datetime, timezone
from typing import Optional

import database
from config import settings
from models import ScoredListing, Listing

logger = logging.getLogger(__name__)

JUNK_KEYWORDS = {"defekt", "bastler", "ersatzteile", "kaputt", "defective", "broken"}


def weighted_rolling_average(search_term: str, days: int) -> Optional[float]:
    """Compute age-weighted average — newer prices have higher weight."""
    history = database.get_price_history(search_term, days)
    if not history:
        return None

    now = datetime.utcnow()
    total_weight = 0.0
    weighted_sum = 0.0

    for entry in history:
        seen_at = entry["seen_at"]
        if isinstance(seen_at, str):
            try:
                seen_at = datetime.fromisoformat(seen_at)
            except ValueError:
                seen_at = now
        age_days = max((now - seen_at).total_seconds() / 86400, 0.001)
        weight = 1.0 / age_days
        weighted_sum += entry["price"] * weight
        total_weight += weight

    if total_weight == 0:
        return None
    return weighted_sum / total_weight


def compute_score(listing: dict, rolling_avg: float, threshold_pct: float) -> int:
    price = listing["price"]
    if rolling_avg <= 0 or price <= 0:
        return 0

    delta_pct = (rolling_avg - price) / rolling_avg * 100

    if delta_pct >= 60:
        base = 100
    elif delta_pct >= 40:
        base = 75
    elif delta_pct >= 30:
        base = 50
    elif delta_pct >= 20:
        base = 25
    elif delta_pct >= threshold_pct:
        base = 10
    else:
        return 0

    bonus = 0

    seller_id = listing.get("seller_id")
    if seller_id:
        count = database.get_seller_listing_count(seller_id)
        if count < 3:
            bonus += 10

    if listing.get("images_count", 0) >= 3:
        bonus += 10

    age_minutes = listing.get("age_minutes")
    if age_minutes is not None and age_minutes < 120:
        bonus += 5

    title_lower = (listing.get("title") or "").lower()
    if not any(kw in title_lower for kw in JUNK_KEYWORDS):
        bonus += 5

    if database.is_blacklisted(seller_id or ""):
        bonus -= 15

    return max(0, min(100, base + bonus))


def expected_profit(price: float, rolling_avg: float) -> float:
    resale_price = rolling_avg * 0.85
    return resale_price - price


def analyze_listing(listing: dict, search_term: str) -> Optional[ScoredListing]:
    rolling_avg = weighted_rolling_average(search_term, settings.ROLLING_AVERAGE_DAYS)
    if rolling_avg is None:
        return None

    threshold = settings.PRICE_THRESHOLD_PERCENT
    score = compute_score(listing, rolling_avg, threshold)
    if score == 0:
        return None

    price = listing["price"]
    profit = expected_profit(price, rolling_avg)
    if profit < settings.MIN_PROFIT_EUR:
        return None

    delta_pct = (rolling_avg - price) / rolling_avg * 100

    pydantic_listing = Listing(
        id=listing["id"],
        title=listing.get("title", ""),
        price=price,
        url=listing.get("url", ""),
        seller_id=listing.get("seller_id"),
        seller_type=listing.get("seller_type"),
        images_count=listing.get("images_count", 0),
        location=listing.get("location"),
        category=listing.get("category"),
        age_minutes=listing.get("age_minutes"),
    )

    return ScoredListing(
        listing=pydantic_listing,
        score=score,
        expected_profit=profit,
        rolling_average=rolling_avg,
        price_delta_percent=delta_pct,
    )


def should_alert(listing: dict) -> bool:
    """Check budget, image count, and seller listing count filters."""
    if listing["price"] > settings.MAX_BUDGET_EUR:
        return False
    if listing.get("images_count", 0) < settings.MIN_LISTING_IMAGES:
        return False
    seller_id = listing.get("seller_id", "")
    if seller_id:
        count = database.get_seller_listing_count(seller_id)
        if count > settings.MAX_SELLER_LISTINGS:
            logger.debug(f"Skipping dealer seller {seller_id} ({count} listings)")
            return False
    return True
