import asyncio
import json
import logging
import random
import re
from datetime import datetime
from typing import List, Optional

import aiohttp

from config import settings

logger = logging.getLogger(__name__)

# Willhaben is a Next.js SSR app. The search page returns HTML containing
# a <script id="__NEXT_DATA__"> tag with all listing data as embedded JSON.
# There is no separate JSON REST endpoint — the old /iad/search/atz/seo/... URL
# returns 404. The correct search URL is below.
BASE_URL = "https://www.willhaben.at/iad/kaufen-und-verkaufen/marktplatz"

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-AT,de;q=0.9,en;q=0.8",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

# Compiled once — extracts the JSON blob from the __NEXT_DATA__ script tag
_NEXT_DATA_RE = re.compile(
    r'<script\s+id="__NEXT_DATA__"\s+type="application/json">(.*?)</script>',
    re.DOTALL,
)

_semaphore: Optional[asyncio.Semaphore] = None


def get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(2)
    return _semaphore


def _extract_next_data(html: str) -> Optional[dict]:
    """Pull the __NEXT_DATA__ JSON blob out of an SSR HTML page."""
    match = _NEXT_DATA_RE.search(html)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse __NEXT_DATA__ JSON: {e}")
        return None


def _parse_listing(item: dict) -> Optional[dict]:
    try:
        # advertId is the canonical field; fall back to id for safety
        ad_id = str(item.get("advertId") or item.get("id") or "")
        if not ad_id:
            return None

        heading = item.get("heading") or item.get("description", "")

        # Price lives under advertPriceInfo.amount
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

        seller_info = item.get("advertiserInfo") or item.get("sellerInfo") or {}
        seller_id = str(seller_info.get("userId") or seller_info.get("id") or "")
        seller_type = seller_info.get("type") or seller_info.get("sellerType") or ""

        # Location is inside an attributes.attribute list:
        # [{"name": "LOCATION", "values": ["Wien"]}, ...]
        location: Optional[str] = None
        attributes = item.get("attributes") or {}
        attr_list = []
        if isinstance(attributes, dict):
            attr_list = attributes.get("attribute") or []
        elif isinstance(attributes, list):
            attr_list = attributes
        for attr in attr_list:
            if not isinstance(attr, dict):
                continue
            name = (attr.get("name") or "").upper()
            if name in ("LOCATION", "DISTRICT", "STATE"):
                vals = attr.get("values") or []
                if vals:
                    location = str(vals[0])
                    break

        # advertImageList is a list of image objects
        images = item.get("advertImageList") or item.get("images") or []
        if isinstance(images, dict):
            images = images.get("advertImage") or []
        images_count = len(images) if isinstance(images, list) else 0

        publish_date = item.get("publishDate") or item.get("startDate")
        age_minutes: Optional[float] = None
        if publish_date:
            try:
                pub_dt = datetime.fromisoformat(
                    str(publish_date).replace("Z", "+00:00")
                )
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
    page: int = 1,
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

    # Build the full URL for debug logging before the request
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    full_url = f"{BASE_URL}?{query_string}"
    logger.info(f"Fetching: {full_url}")

    async with get_semaphore():
        for attempt in range(3):
            try:
                async with session.get(
                    BASE_URL,
                    params=params,
                    headers=HEADERS,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    logger.info(
                        f"Response: HTTP {resp.status} for '{keyword}' page {page} "
                        f"(attempt {attempt+1})"
                    )

                    if resp.status == 429:
                        wait = 60 * (attempt + 1)
                        logger.warning(
                            f"Rate limited (429), waiting {wait}s — attempt {attempt+1}/3"
                        )
                        await asyncio.sleep(wait)
                        continue
                    if resp.status == 403:
                        logger.critical(
                            "HTTP 403 from Willhaben — möglicherweise geblockt, "
                            "User-Agent prüfen"
                        )
                        return []
                    if resp.status != 200:
                        text = await resp.text()
                        logger.error(
                            f"Unexpected HTTP {resp.status} for '{keyword}' | "
                            f"snippet: {text[:300]}"
                        )
                        return []

                    html = await resp.text()
                    next_data = _extract_next_data(html)
                    if not next_data:
                        logger.error(
                            f"No __NEXT_DATA__ found in response for '{keyword}' "
                            f"page {page} | HTML snippet: {html[:300]}"
                        )
                        return []

                    # Path: props → pageProps → searchResult →
                    #         advertSummaryList → advertSummary
                    try:
                        ads = (
                            next_data["props"]["pageProps"]["searchResult"]
                            ["advertSummaryList"]["advertSummary"]
                        )
                    except (KeyError, TypeError):
                        logger.error(
                            f"Unexpected __NEXT_DATA__ structure for '{keyword}'. "
                            f"Top-level keys: {list(next_data.get('props', {}).get('pageProps', {}).keys())}"
                        )
                        return []

                    listings = []
                    for ad in ads:
                        parsed = _parse_listing(ad)
                        if parsed:
                            listings.append(parsed)

                    logger.info(
                        f"Parsed {len(listings)} listings for '{keyword}' page {page}"
                    )
                    return listings

            except asyncio.TimeoutError:
                logger.warning(
                    f"Timeout fetching '{keyword}' page {page} (attempt {attempt+1})"
                )
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
        page = 1  # Willhaben pagination is 1-based
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
            if page > 5:
                break

    logger.info(f"Scraped {len(results)} listings for '{keyword}'")
    return results
