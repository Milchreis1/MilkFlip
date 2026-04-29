import asyncio
import logging
import random
import time
from datetime import datetime
from typing import List, Optional

import aiohttp

from config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://www.willhaben.at/iad/search/atz/seo/kaufen-und-verkaufen/marktplatz"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "x-wh-client": "api=PDO;client=responsive_web;version=—;auditId=—",
}

_semaphore: Optional[asyncio.Semaphore] = None


def get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(2)
    return _semaphore


def _parse_listing(item: dict) -> Optional[dict]:
    try:
        ad_id = str(item.get("id", ""))
        if not ad_id:
            return None

        heading = item.get("heading") or item.get("description", "")

        advert_price_info = item.get("advertPriceInfo") or {}
        price_raw = advert_price_info.get("amount") or item.get("price")
        if price_raw is None:
            return None
        try:
            price = float(str(price_raw).replace(",", ".").replace(" ", ""))
        except (ValueError, TypeError):
            return None

        advert_url = item.get("advertUrl") or item.get("slug", "")
        full_url = f"https://www.willhaben.at{advert_url}" if advert_url else ""

        seller_info = item.get("sellerInfo") or item.get("advertiserInfo") or {}
        seller_id = str(seller_info.get("userId") or seller_info.get("id") or "")
        seller_type = seller_info.get("type") or seller_info.get("sellerType") or ""

        attributes = item.get("attributes") or {}
        attr_map: dict = {}
        if isinstance(attributes, list):
            for attr in attributes:
                if isinstance(attr, dict):
                    attr_map[attr.get("name", "")] = attr.get("values", [])
        elif isinstance(attributes, dict):
            attr_map = attributes

        location_parts = []
        for loc_key in ("location", "district", "state", "postcode"):
            val = attr_map.get(loc_key)
            if val:
                if isinstance(val, list) and val:
                    location_parts.append(str(val[0]))
                elif isinstance(val, str):
                    location_parts.append(val)
        location = ", ".join(location_parts) if location_parts else None

        images = item.get("advertImageList") or item.get("images") or []
        images_count = len(images) if isinstance(images, list) else 0

        publish_date = item.get("publishDate") or item.get("startDate")
        age_minutes: Optional[float] = None
        if publish_date:
            try:
                if isinstance(publish_date, str):
                    pub_dt = datetime.fromisoformat(publish_date.replace("Z", "+00:00"))
                    now_utc = datetime.utcnow().replace(tzinfo=pub_dt.tzinfo)
                    age_minutes = (now_utc - pub_dt).total_seconds() / 60
            except Exception:
                pass

        return {
            "id": ad_id,
            "title": heading,
            "price": price,
            "url": full_url,
            "seller_id": seller_id,
            "seller_type": seller_type,
            "images_count": images_count,
            "location": location,
            "category": item.get("categoryPath") or item.get("category"),
            "age_minutes": age_minutes,
        }
    except Exception as e:
        logger.error(f"Failed to parse listing: {e}")
        return None


async def _fetch_page(
    session: aiohttp.ClientSession,
    keyword: str,
    page: int = 0,
    max_price: Optional[float] = None,
    min_price: Optional[float] = None,
    category_id: Optional[str] = None,
) -> List[dict]:
    params: dict = {
        "keyword": keyword,
        "page": page,
        "rows": 30,
    }
    if max_price is not None:
        params["PRICE_TO"] = int(max_price)
    if min_price is not None:
        params["PRICE_FROM"] = int(min_price)
    if category_id:
        params["areaId"] = category_id

    async with get_semaphore():
        for attempt in range(3):
            try:
                async with session.get(
                    BASE_URL,
                    params=params,
                    headers=HEADERS,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 429:
                        wait = 60 * (attempt + 1)
                        logger.warning(f"Rate limited (429), waiting {wait}s — attempt {attempt+1}/3")
                        await asyncio.sleep(wait)
                        continue
                    if resp.status == 403:
                        logger.critical(
                            "HTTP 403 from Willhaben — möglicherweise geblockt, User-Agent prüfen"
                        )
                        return []
                    if resp.status != 200:
                        logger.error(f"Unexpected HTTP {resp.status} for keyword '{keyword}'")
                        return []

                    try:
                        data = await resp.json(content_type=None)
                    except Exception as e:
                        text = await resp.text()
                        logger.error(f"JSON parse error for '{keyword}': {e} | snippet: {text[:200]}")
                        return []

                    ads = (
                        data.get("advertSummaryList", {}).get("advertSummary")
                        or data.get("ads")
                        or data.get("items")
                        or []
                    )
                    listings = []
                    for ad in ads:
                        parsed = _parse_listing(ad)
                        if parsed:
                            listings.append(parsed)
                    return listings

            except asyncio.TimeoutError:
                logger.warning(f"Timeout fetching '{keyword}' page {page} (attempt {attempt+1})")
                if attempt < 2:
                    await asyncio.sleep(5)
            except aiohttp.ClientError as e:
                logger.error(f"Network error fetching '{keyword}': {e}")
                if attempt < 2:
                    await asyncio.sleep(5)

    return []


async def scrape_profile(profile: dict) -> List[dict]:
    """Scrape all pages for a single search profile."""
    keyword = profile["query"]
    max_price = profile.get("max_price") or settings.MAX_BUDGET_EUR
    min_price = profile.get("min_price")
    category_id = profile.get("category_id")

    results: List[dict] = []

    async with aiohttp.ClientSession() as session:
        page = 0
        while True:
            delay = random.uniform(3, 8)
            await asyncio.sleep(delay)

            listings = await _fetch_page(
                session,
                keyword,
                page=page,
                max_price=max_price,
                min_price=min_price,
                category_id=category_id,
            )

            if not listings:
                break

            for listing in listings:
                listing["search_term"] = keyword
                if listing["price"] > max_price:
                    continue
                if min_price and listing["price"] < min_price:
                    continue
                results.append(listing)

            if len(listings) < 30:
                break

            page += 1
            if page >= 5:
                break

    logger.info(f"Scraped {len(results)} listings for '{keyword}'")
    return results
