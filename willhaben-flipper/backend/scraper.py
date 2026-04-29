import asyncio
import base64
import hashlib
import hmac as hmac_lib
import logging
import os
import random
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import aiohttp

from config import settings

logger = logging.getLogger(__name__)

# Real Willhaben mobile API (reverse-engineered from Android app).
# www.willhaben.at/iad/... serves HTML only — not a JSON API.
API_BASE = "https://api.willhaben.at"
TOKEN_PATH = "/restapi/v2/application-data"
SEARCH_PATH = "/restapi/v2/search/atz/seo/kaufen-und-verkaufen/marktplatz"

ORGANIZATION = "api@tailored-apps.com"
CLIENT_HEADER = "api@tailored-apps.com;willhabenapp;android;8.15.0;responsive_app"
# HMAC-SHA1 key from the willhaben Android app
_HMAC_KEY = base64.b64decode("JDJhJDEwJHFUd2lnSFoyclJqQ2pSS3dQLlM2Vy4=")

_token_cache: Optional[str] = None
_token_expires: Optional[datetime] = None
_semaphore: Optional[asyncio.Semaphore] = None


def get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(2)
    return _semaphore


# ── Token acquisition ──────────────────────────────────────────────────────────

def _make_token_payload() -> dict:
    salt = base64.b64encode(os.urandom(12)).decode()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")
    message = f"{salt};{timestamp};{ORGANIZATION}".encode()
    signature = base64.b64encode(
        hmac_lib.new(_HMAC_KEY, message, hashlib.sha1).digest()
    ).decode()
    return {
        "organization": ORGANIZATION,
        "salt": salt,
        "timestamp": timestamp,
        "signature": signature,
    }


async def _fetch_token(session: aiohttp.ClientSession) -> Optional[str]:
    url = f"{API_BASE}{TOKEN_PATH}"
    payload = _make_token_payload()
    logger.info(f"Fetching application token: POST {url}")
    try:
        async with session.post(
            url,
            json=payload,
            headers={
                "content-type": "application/json",
                "x-wh-client": CLIENT_HEADER,
            },
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            logger.info(f"Token response: HTTP {resp.status} from {url}")
            if resp.status != 200:
                text = await resp.text()
                logger.error(f"Token fetch failed HTTP {resp.status} | body: {text[:300]}")
                return None
            data = await resp.json(content_type=None)
            token_obj = (data.get("applicationToken") or {})
            token = token_obj.get("value")
            expire_in = token_obj.get("expireInSeconds", 3600)
            logger.info(f"Application token acquired (expires in {expire_in}s)")
            return token
    except Exception as e:
        logger.error(f"Token fetch exception: {e}")
        return None


async def get_token(session: aiohttp.ClientSession) -> Optional[str]:
    global _token_cache, _token_expires
    now = datetime.now(timezone.utc)
    if _token_cache and _token_expires and now < _token_expires:
        return _token_cache
    token = await _fetch_token(session)
    if token:
        _token_cache = token
        _token_expires = now + timedelta(seconds=3300)  # refresh 5 min before expiry
    return token


# ── Listing parser ─────────────────────────────────────────────────────────────

def _flatten_attributes(attrs) -> dict:
    """Convert attributes list [{name, values}, ...] → {NAME: value} dict."""
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

        # Mobile API uses "description" for the listing title
        title = item.get("description") or item.get("heading") or ""

        attrs = _flatten_attributes(item.get("attributes") or [])

        # Price: try attributes first, then advertPriceInfo
        price_raw = attrs.get("PRICE") or attrs.get("PRICE_SUGGESTING_TEXT")
        if price_raw is None:
            price_info = item.get("advertPriceInfo") or {}
            price_raw = price_info.get("amount")
        if price_raw is None:
            return None
        try:
            price = float(
                str(price_raw).replace(",", ".").replace(" ", "").replace("€", "").strip()
            )
        except (ValueError, TypeError):
            return None

        # Canonical Willhaben listing URL — always built from the ad ID.
        # contextLinkList entries from the API are unreliable/malformed.
        url = f"https://www.willhaben.at/iad/kaufen-und-verkaufen/marktplatz/d/{ad_id}"

        # Seller
        seller_info = item.get("advertiserInfo") or item.get("sellerInfo") or {}
        seller_id = str(seller_info.get("userId") or seller_info.get("id") or "")
        seller_type = str(seller_info.get("type") or seller_info.get("sellerType") or "")

        # Location
        location = (
            attrs.get("LOCATION")
            or attrs.get("DISTRICT")
            or attrs.get("STATE")
            or (item.get("location") if isinstance(item.get("location"), str) else None)
        )

        # Images
        images = item.get("advertImageList") or item.get("images") or []
        if isinstance(images, dict):
            images = images.get("advertImage") or []
        images_count = len(images) if isinstance(images, list) else 0

        # Age
        publish_date = item.get("publishDate") or attrs.get("PUBLISHED") or item.get("startDate")
        age_minutes: Optional[float] = None
        if publish_date:
            try:
                pub_dt = datetime.fromisoformat(str(publish_date).replace("Z", "+00:00"))
                age_minutes = (datetime.now(timezone.utc) - pub_dt).total_seconds() / 60
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
        }
    except Exception as e:
        logger.error(f"Failed to parse listing: {e}", exc_info=True)
        return None


# ── HTTP fetch ─────────────────────────────────────────────────────────────────

async def _fetch_page(
    session: aiohttp.ClientSession,
    keyword: str,
    page: int = 0,
    max_price: Optional[float] = None,
    min_price: Optional[float] = None,
    category_id: Optional[str] = None,
) -> List[dict]:
    global _token_cache

    token = await get_token(session)

    headers = {
        "Accept": "application/json",
        "x-wh-client": CLIENT_HEADER,
    }
    if token:
        headers["x-wh-application-token"] = token

    params: dict = {
        "keyword": keyword,
        "page": page,
        "rows": 30,
        "sort": 1,  # 1=latest first
    }
    if max_price is not None:
        params["PRICE_TO"] = int(max_price)
    if min_price is not None:
        params["PRICE_FROM"] = int(min_price)
    if category_id:
        params["areaId"] = category_id

    url = f"{API_BASE}{SEARCH_PATH}"
    debug_qs = "&".join(f"{k}={v}" for k, v in params.items())
    logger.info(f"GET {url}?{debug_qs}")

    async with get_semaphore():
        for attempt in range(3):
            try:
                async with session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    logger.info(
                        f"Response: HTTP {resp.status} | '{keyword}' page {page} attempt {attempt+1}"
                    )

                    if resp.status == 429:
                        wait = 60 * (attempt + 1)
                        logger.warning(f"Rate limited, waiting {wait}s (attempt {attempt+1}/3)")
                        await asyncio.sleep(wait)
                        continue

                    if resp.status == 401:
                        logger.warning("HTTP 401 — token invalid, forcing refresh")
                        _token_cache = None
                        token = await get_token(session)
                        if token:
                            headers["x-wh-application-token"] = token
                        await asyncio.sleep(2)
                        continue

                    if resp.status == 403:
                        logger.critical(
                            f"HTTP 403 from {url} — IP or token blocked"
                        )
                        return []

                    if resp.status != 200:
                        text = await resp.text()
                        logger.error(
                            f"HTTP {resp.status} | URL: {url}?{debug_qs} | body: {text[:400]}"
                        )
                        return []

                    try:
                        data = await resp.json(content_type=None)
                    except Exception as e:
                        text = await resp.text()
                        logger.error(f"JSON parse error: {e} | snippet: {text[:300]}")
                        return []

                    ads = (
                        (data.get("advertSummaryList") or {}).get("advertSummary")
                        or data.get("ads")
                        or data.get("items")
                        or []
                    )

                    if not isinstance(ads, list):
                        logger.error(
                            f"Unexpected response shape for '{keyword}'. "
                            f"Top-level keys: {list(data.keys())}"
                        )
                        return []

                    # Log the first raw item once (page 0 only) so field names are visible
                    if page == 0 and ads:
                        import json as _json
                        logger.info(
                            f"RAW first item sample for '{keyword}':\n"
                            + _json.dumps(ads[0], ensure_ascii=False, indent=2)
                        )

                    listings = [p for ad in ads if (p := _parse_listing(ad)) is not None]
                    logger.info(f"Parsed {len(listings)}/{len(ads)} listings for '{keyword}' page {page}")
                    return listings

            except asyncio.TimeoutError:
                logger.warning(f"Timeout for '{keyword}' page {page} attempt {attempt+1}")
                if attempt < 2:
                    await asyncio.sleep(5)
            except aiohttp.ClientError as e:
                logger.error(f"Network error for '{keyword}': {e}")
                if attempt < 2:
                    await asyncio.sleep(5)

    return []


# ── Profile scrape ─────────────────────────────────────────────────────────────

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
                session, keyword,
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
