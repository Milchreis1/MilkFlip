import asyncio
import json as _json
import logging
import random
import re
import requests as _requests
from datetime import datetime, timezone
from typing import List, Optional

import aiohttp

import database
from config import settings

logger = logging.getLogger(__name__)

# HTML search page — Willhaben is Next.js; listings are in __NEXT_DATA__ JSON.
SEARCH_URL = "https://www.willhaben.at/iad/kaufen-und-verkaufen/marktplatz"

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-AT,de;q=0.9,en;q=0.8",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

_NEXT_DATA_RE = re.compile(
    r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
    re.DOTALL,
)

_semaphore: Optional[asyncio.Semaphore] = None

# Log one raw item per scrape run so field names are always visible
_raw_logged = False

_LIVENESS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def is_listing_active(url: str) -> bool:
    try:
        resp = _requests.head(
            url,
            timeout=5,
            allow_redirects=True,
            headers=_LIVENESS_HEADERS,
        )
        return resp.status_code == 200
    except Exception as e:
        logger.warning(f"Liveness check failed for {url}: {e}")
        return False


def get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(2)
    return _semaphore


def _flatten_attributes(attrs) -> dict:
    """Convert [{name, values}, ...] → {NAME: first_value} dict."""
    result: dict = {}
    if isinstance(attrs, dict):
        attrs = attrs.get("attribute") or []
    if not isinstance(attrs, list):
        return result
    for attr in attrs:
        if not isinstance(attr, dict):
            continue
        name = (attr.get("name") or "").upper()
        values = attr.get("values") or []
        if name and values:
            result[name] = values[0]
    return result


def _parse_listing(item: dict) -> Optional[dict]:
    try:
        ad_id = str(item.get("id") or item.get("advertId") or "")
        if not ad_id:
            return None

        title = item.get("description") or item.get("heading") or ""

        attrs = _flatten_attributes(item.get("attributes") or [])

        price_raw = attrs.get("PRICE") or attrs.get("PRICE_SUGGESTING_TEXT")
        if price_raw is None:
            price_info = item.get("advertPriceInfo") or {}
            price_raw = price_info.get("amount")
        if price_raw is None:
            return None
        try:
            price = float(
                str(price_raw)
                .replace(",", ".")
                .replace(" ", "")
                .replace("€", "")
                .strip()
            )
        except (ValueError, TypeError):
            return None

        url = (
            f"https://www.willhaben.at"
            f"/iad/kaufen-und-verkaufen/marktplatz/d/{ad_id}"
        )

        seller_info = item.get("advertiserInfo") or item.get("sellerInfo") or {}
        seller_id = str(seller_info.get("userId") or seller_info.get("id") or "")
        seller_type = str(seller_info.get("type") or seller_info.get("sellerType") or "")

        location = (
            attrs.get("LOCATION")
            or attrs.get("DISTRICT")
            or attrs.get("STATE")
            or (item.get("location") if isinstance(item.get("location"), str) else None)
        )

        images = item.get("advertImageList") or item.get("images") or []
        if isinstance(images, dict):
            images = images.get("advertImage") or []
        images_count = len(images) if isinstance(images, list) else 0

        publish_date = (
            item.get("publishDate")
            or attrs.get("PUBLISHED")
            or item.get("startDate")
        )
        age_minutes: Optional[float] = None
        if publish_date:
            try:
                pub_dt = datetime.fromisoformat(
                    str(publish_date).replace("Z", "+00:00")
                )
                age_minutes = (
                    datetime.now(timezone.utc) - pub_dt
                ).total_seconds() / 60
            except Exception:
                pass

        return {
            "id": ad_id,
            "title": title,
            "price": price,
            "url": url,
            "seller_id": seller_id,
            "seller_type": seller_type,
            "images_count": images_count,
            "location": location,
            "category": item.get("categoryPath") or attrs.get("CATEGORY"),
            "age_minutes": age_minutes,
            "seen_at": datetime.now(timezone.utc),
        }
    except Exception as e:
        logger.error(f"Failed to parse listing: {e}", exc_info=True)
        return None


async def _fetch_page(
    session: aiohttp.ClientSession,
    keyword: str,
    page: int = 0,
    max_price: Optional[float] = None,
    min_price: Optional[float] = None,
    category_id: Optional[str] = None,
) -> List[dict]:
    global _raw_logged

    # Willhaben HTML pages are 1-indexed; page=0 here → page=1 in URL.
    params: dict = {"keyword": keyword, "page": page + 1}
    if max_price is not None:
        params["PRICE_TO"] = int(max_price)
    if min_price is not None:
        params["PRICE_FROM"] = int(min_price)
    if category_id:
        params["areaId"] = category_id

    logger.info(f"GET {SEARCH_URL}?keyword={keyword}&page={page + 1}")

    async with get_semaphore():
        for attempt in range(3):
            try:
                async with session.get(
                    SEARCH_URL,
                    params=params,
                    headers=HEADERS,
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    logger.info(
                        f"HTTP {resp.status} | '{keyword}' page {page} "
                        f"attempt {attempt + 1}"
                    )

                    if resp.status == 429:
                        wait = 60 * (attempt + 1)
                        logger.warning(f"Rate limited (429), waiting {wait}s")
                        await asyncio.sleep(wait)
                        continue

                    if resp.status == 403:
                        logger.critical("HTTP 403 — möglicherweise geblockt")
                        return []

                    if resp.status != 200:
                        text = await resp.text()
                        logger.error(
                            f"HTTP {resp.status} | '{keyword}' | body[:200]: {text[:200]}"
                        )
                        return []

                    html = await resp.text()

                    match = _NEXT_DATA_RE.search(html)
                    if not match:
                        logger.error(
                            f"__NEXT_DATA__ not found for '{keyword}' page {page}. "
                            f"HTML length: {len(html)}"
                        )
                        return []

                    try:
                        data = _json.loads(match.group(1))
                    except Exception as e:
                        logger.error(f"__NEXT_DATA__ JSON parse error for '{keyword}': {e}")
                        return []

                    # Navigate: props.pageProps.searchResult.advertSummaryList.advertSummary
                    page_props = data.get("props", {}).get("pageProps", {})
                    search_result = page_props.get("searchResult") or {}
                    ads = (
                        (search_result.get("advertSummaryList") or {}).get("advertSummary")
                        or []
                    )

                    if not isinstance(ads, list):
                        logger.error(
                            f"Unexpected __NEXT_DATA__ shape for '{keyword}'. "
                            f"pageProps keys: {list(page_props.keys())}"
                        )
                        return []

                    if ads and not _raw_logged:
                        _raw_logged = True
                        logger.info(
                            f"RAW first item for '{keyword}':\n"
                            + _json.dumps(ads[0], ensure_ascii=False, indent=2)
                        )

                    listings = [p for ad in ads if (p := _parse_listing(ad)) is not None]
                    logger.info(
                        f"Parsed {len(listings)}/{len(ads)} listings "
                        f"for '{keyword}' page {page}"
                    )
                    return listings

            except asyncio.TimeoutError:
                logger.warning(
                    f"Timeout for '{keyword}' page {page} attempt {attempt + 1}"
                )
                if attempt < 2:
                    await asyncio.sleep(5)
            except aiohttp.ClientError as e:
                logger.error(f"Network error for '{keyword}': {e}")
                if attempt < 2:
                    await asyncio.sleep(5)

    return []


async def scrape_profile(profile: dict) -> List[dict]:
    keyword = profile["query"]
    max_price = profile.get("max_price") or settings.MAX_BUDGET_EUR
    min_price = profile.get("min_price")
    category_id = profile.get("category_id")

    results: List[dict] = []

    async with aiohttp.ClientSession() as session:
        page = 0
        while True:
            await asyncio.sleep(random.uniform(3, 8))

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
                active = await asyncio.to_thread(is_listing_active, listing["url"])
                if not active:
                    logger.info(f"Skipping inactive listing: '{listing.get('title')}' {listing['url']}")
                    continue
                results.append(listing)

            if len(listings) < 30:
                break

            page += 1
            if page >= 5:
                break

    logger.info(f"Scraped {len(results)} listings for '{keyword}'")
    return results


# ── Listing liveness checks ────────────────────────────────────────────────────

async def verify_url(url: str) -> Optional[bool]:
    """
    HEAD-check a Willhaben listing URL.
    Returns True  → HTTP 200, listing is live.
    Returns False → HTTP 404, listing is gone.
    Returns None  → other status / network error (do not act on uncertainty).
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(
                url,
                headers=HEADERS,
                allow_redirects=True,
                timeout=aiohttp.ClientTimeout(total=8),
            ) as resp:
                if resp.status == 200:
                    return True
                if resp.status == 404:
                    return False
                logger.debug(f"verify_url: HTTP {resp.status} for {url}")
                return None
    except Exception as e:
        logger.debug(f"verify_url error for {url}: {e}")
        return None


async def check_stale_listings(older_than_hours: int = 24) -> int:
    """
    Verify listings in the DB that haven't been seen recently.
    Marks listings inactive when they return HTTP 404.
    Returns the number of listings marked inactive.
    """
    stale = database.get_stale_active_listings(older_than_hours)
    if not stale:
        return 0

    logger.info(f"Checking {len(stale)} stale listings for liveness")
    marked = 0
    for row in stale:
        result = await verify_url(row["url"])
        if result is False:
            database.mark_listing_inactive(row["id"])
            marked += 1
            logger.info(f"Marked inactive (404): '{row['title']}' [{row['id']}]")
        await asyncio.sleep(random.uniform(1, 3))

    logger.info(f"Stale check done: {marked}/{len(stale)} marked inactive")
    return marked
