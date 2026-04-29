from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Listing(BaseModel):
    id: str
    title: str
    price: float
    url: str
    seller_id: Optional[str] = None
    seller_type: Optional[str] = None
    images_count: int = 0
    location: Optional[str] = None
    category: Optional[str] = None
    seen_at: Optional[datetime] = None
    status: str = "new"
    seller_listing_count: int = 0
    age_minutes: Optional[float] = None


class PriceHistoryEntry(BaseModel):
    search_term: str
    price: float
    seen_at: datetime


class Alert(BaseModel):
    id: Optional[int] = None
    listing_id: str
    title: str
    price: float
    url: str
    score: int
    expected_profit: float
    rolling_average: float
    price_delta_percent: float
    location: Optional[str] = None
    images_count: int = 0
    age_minutes: Optional[float] = None
    alerted_at: Optional[datetime] = None
    user_action: Optional[str] = None


class AlertUpdate(BaseModel):
    user_action: str


class SearchProfile(BaseModel):
    id: Optional[int] = None
    name: str
    query: str
    category_id: Optional[str] = None
    max_price: Optional[float] = None
    min_price: Optional[float] = None
    active: bool = True
    custom_threshold: Optional[float] = None


class BlacklistEntry(BaseModel):
    seller_id: str
    reason: Optional[str] = None
    added_at: Optional[datetime] = None


class WatchlistEntry(BaseModel):
    seller_id: str
    note: Optional[str] = None
    added_at: Optional[datetime] = None


class ConfigUpdate(BaseModel):
    MAX_BUDGET_EUR: Optional[float] = None
    MIN_PROFIT_EUR: Optional[float] = None
    PRICE_THRESHOLD_PERCENT: Optional[float] = None
    ROLLING_AVERAGE_DAYS: Optional[int] = None
    SCRAPE_INTERVAL_MINUTES: Optional[int] = None
    MIN_LISTING_IMAGES: Optional[int] = None
    ALERT_COOLDOWN_HOURS: Optional[int] = None
    MAX_SELLER_LISTINGS: Optional[int] = None
    LOG_LEVEL: Optional[str] = None


class Stats(BaseModel):
    today_seen: int
    today_alerts: int
    week_alerts: int
    total_alerts: int
    best_margin_today: Optional[float] = None
    total_profit_interested: float = 0.0
    top_search_terms: list = Field(default_factory=list)


class ScoredListing(BaseModel):
    listing: Listing
    score: int
    expected_profit: float
    rolling_average: float
    price_delta_percent: float
