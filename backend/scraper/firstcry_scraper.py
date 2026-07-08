from __future__ import annotations

import json
import logging
import os
import re
import time
import requests
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
PAGE_TIMEOUT_SECONDS = 30         # balanced: enough for JS-heavy pages, never forever
ELEMENT_TIMEOUT_SECONDS = 12
SEARCH_RESULTS_TIMEOUT = 20       # explicit wait for product cards to render on search
PRODUCT_CONTENT_TIMEOUT = 20      # explicit wait for product-detail content to render
EXTRACTION_RETRY_ROUNDS = 4       # re-extract when mandatory fields are still loading
MAX_PRODUCT_CANDIDATES = 4        # matching results to try before giving up on a keyword
TOTAL_TIME_BUDGET_SECONDS = 35    # soft budget for the review-collection phase
HARD_DEADLINE_SECONDS = 75        # absolute wall-clock cap for the whole scrape
MAX_RETRIES = 3                   # whole-attempt retries (page reload) as a safety net
REVIEW_LOAD_MORE_ROUNDS = 10      # bounded "load more"/scroll rounds when collecting reviews

BASE_URL = "https://www.firstcry.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Real firstcry product-detail URLs look like:
#   /<brand>/<slug>/<numeric-id>/product-detail?sterm=...
PRODUCT_LINK_TOKENS = ("/product-detail", "/p/", "/product/")
# Fallback: every FirstCry product URL embeds a long numeric product id segment,
# so we can still recognise product links even if the path suffix changes.
_PRODUCT_URL_ID_RE = re.compile(r"/\d{5,}(?:[/?]|$)")
# Brand / category LISTING pages look like `/<brand-slug>/6/0/1002995` (three
# numeric path segments) and are heavily present in the search page's nav/menu
# dropdowns (e.g. `?ref2=menu_dd_...`). They are NOT products and carry no
# reviews, so they must never be opened. Real product pages always contain
# `/product-detail`; this pattern lets us reject the listing pages that would
# otherwise slip through the loose numeric-id fallback above (e.g. the brand
# 'Toy Balloon Kids' -> /toy-balloon-kids/6/0/1002995 matching a 'toys' search).
_CATEGORY_LISTING_RE = re.compile(r"/\d+/\d+/\d+")


def _is_product_link(href: str) -> bool:
    """True only for real product-detail links, never brand/category listings."""
    if not href:
        return False
    href_lower = href.lower()
    if "product-detail" in href_lower:
        return True  # definitive product page
    if _CATEGORY_LISTING_RE.search(href):
        return False  # brand/category listing (e.g. /6/0/1002995) - not a product
    if any(token in href_lower for token in PRODUCT_LINK_TOKENS):
        return True
    return bool(_PRODUCT_URL_ID_RE.search(href))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


# ----------------------------------------------------------------------------
# Selenium driver helpers
# ----------------------------------------------------------------------------
def _build_driver(headless: bool = True) -> webdriver.Chrome | None:
    chrome_options = Options()
    if headless or os.getenv("SELENIUM_HEADLESS") == "1":
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(f"--user-agent={HEADERS['User-Agent']}")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    # NOTE: we deliberately do NOT disable images/CSS here - some sites lazy
    # -load price/review blocks only once layout has settled.
    chrome_options.page_load_strategy = "eager"

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    except Exception as exc:
        logger.warning("Driver setup via webdriver_manager failed: %s", exc)
        try:
            driver = webdriver.Chrome(options=chrome_options)
        except Exception as fallback_exc:
            logger.warning("Driver fallback failed: %s", fallback_exc)
            return None

    # hide the obvious "navigator.webdriver" automation flag
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
        )
    except Exception:
        pass

    driver.set_page_load_timeout(PAGE_TIMEOUT_SECONDS)
    driver.set_script_timeout(PAGE_TIMEOUT_SECONDS)
    logger.info("STEP: Browser launched (headless=%s, page-load timeout=%ss)", headless, PAGE_TIMEOUT_SECONDS)
    return driver


def _wait_body(driver: webdriver.Chrome, timeout: int = ELEMENT_TIMEOUT_SECONDS) -> None:
    try:
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except Exception:
        pass


def _wait_for_page_ready(driver: webdriver.Chrome, timeout: int = PAGE_TIMEOUT_SECONDS) -> bool:
    """Page-ready-state validation: wait until the document has finished its
    initial parse/load so we don't read the DOM mid-render."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
        )
        return True
    except Exception:
        return False


def _wait_for_product_cards(driver: webdriver.Chrome, timeout: int = SEARCH_RESULTS_TIMEOUT) -> bool:
    """Explicit wait until real product-detail links have rendered on the search
    results page (FirstCry renders these via JS after the initial HTML)."""
    css = ", ".join(PRODUCT_LINK_TOKENS_AS_CSS())
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, css)) > 0
        )
        return True
    except TimeoutException:
        return False
    except Exception:
        return False


def _wait_for_product_content(driver: webdriver.Chrome, timeout: int = PRODUCT_CONTENT_TIMEOUT) -> bool:
    """Explicit wait until the product page has rendered its title AND a
    price/rating/structured-data region, i.e. the dynamic content we extract."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: bool(d.find_elements(By.CSS_SELECTOR, "h1, [class*='title' i]"))
            and bool(
                d.find_elements(
                    By.CSS_SELECTOR,
                    "[class*='price' i], [itemprop='price'], [class*='rating' i], "
                    "script[type='application/ld+json']",
                )
            )
        )
        return True
    except TimeoutException:
        return False
    except Exception:
        return False


def _has_mandatory_fields(details: dict, product_url: str | None) -> bool:
    """Mandatory fields that must be present before we call a scrape successful:
    product name, image, price and product URL. Missing values here usually mean
    the page has not finished loading, so the caller should retry rather than
    return partial N/A data."""
    name = details.get("product_name")
    return bool(
        name
        and _looks_like_valid_title(name)
        and details.get("product_image")
        and (details.get("current_price") is not None)
        and product_url
    )


def _wait_for_any_selector(driver: webdriver.Chrome, selectors: list[str], timeout: int = ELEMENT_TIMEOUT_SECONDS) -> bool:
    """Wait until at least one of the given selectors appears, OR give up after timeout."""
    end_time = time.time() + timeout
    css = ", ".join(selectors)
    while time.time() < end_time:
        try:
            if driver.find_elements(By.CSS_SELECTOR, css):
                return True
        except Exception:
            pass
        time.sleep(0.4)
    return False


def _scroll_to_bottom(driver: webdriver.Chrome, steps: int = 4, pause: float = 0.4) -> None:
    last_height = 0
    for _ in range(steps):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)
        try:
            new_height = driver.execute_script("return document.body.scrollHeight")
        except Exception:
            break
        if new_height == last_height:
            break
        last_height = new_height


# ----------------------------------------------------------------------------
# Small text / number normalizers
# ----------------------------------------------------------------------------
def _clean_text(raw_value: str | None) -> str:
    cleaned = re.sub(r"\s+", " ", (raw_value or "")).strip()
    return cleaned if len(cleaned) >= 2 else ""


def _normalize_rating(raw_value) -> float:
    if raw_value is None:
        return 0.0
    if isinstance(raw_value, (int, float)):
        return round(float(raw_value), 1)
    match = re.search(r"(\d+(?:\.\d+)?)", str(raw_value))
    if not match:
        return 0.0
    rating = float(match.group(1))
    if rating > 5:
        rating = round(rating / 10, 1)
    return round(rating, 1)


def _valid_product_rating(raw_value) -> float | None:
    """Parse a *product* star rating and return it ONLY if it is a plausible
    5-point value (0 < r <= 5). Returns None for missing / zero / implausible
    values, so a real rating is never confused with 'no rating' and a review
    *count* (e.g. '1,200 Ratings') can never be mistaken for a rating.

    An explicit 10-point scale ('8.6 / 10', 'out of 10') is converted to 5-point.
    """
    if raw_value is None or isinstance(raw_value, bool):
        return None
    if isinstance(raw_value, (int, float)):
        rating = float(raw_value)
    else:
        text = str(raw_value)
        # a bare count like "1200 ratings" / "300 reviews" is NOT a rating
        if re.search(r"\d[\d,]*\s*(?:ratings?|reviews?)\b", text, re.I):
            return None
        ten_scale = re.search(r"(\d+(?:\.\d+)?)\s*(?:/|out of)\s*10\b", text, re.I)
        match = re.search(r"(\d+(?:\.\d+)?)", text)
        if not match:
            return None
        rating = float(ten_scale.group(1)) / 2.0 if ten_scale else float(match.group(1))
    rating = round(rating, 1)
    if 0 < rating <= 5:
        return rating
    return None


def _normalize_price(raw_value) -> float | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, (int, float)):
        return float(raw_value)
    match = re.search(r"(\d[\d,]*(?:\.\d+)?)", str(raw_value).replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _format_inr(value: float | int | None) -> str | None:
    if value is None:
        return None
    digits = int(round(float(value)))
    s = str(digits)
    if len(s) <= 3:
        return f"₹{s}"
    last3, rest = s[-3:], s[:-3]
    parts = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return f"₹{','.join(parts)},{last3}"


def _looks_like_valid_title(text: str | None) -> bool:
    if not text:
        return False
    cleaned = _clean_text(text)
    if len(cleaned) < 3:
        return False
    lowered = cleaned.lower()
    # Unambiguous multi-word chrome phrases: safe as a substring match.
    for phrase in ("search results", "sign in", "my account", "add to cart", "shopping cart"):
        if phrase in lowered:
            return False
    # Standalone chrome words matched on WORD BOUNDARIES so real brand/product
    # names are never rejected by an accidental substring - e.g. the brand
    # "Carter's" contains "cart", "Cartoon" contains "cart", etc.
    for word in ("cart", "wishlist", "firstcry", "signin", "login"):
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            return False
    return True


def _looks_like_blocked_page(html: str) -> bool:
    lowered = html.lower()
    markers = ["captcha", "verify you are human", "access denied", "temporarily unavailable", "are you a robot"]
    return any(m in lowered for m in markers)


# ----------------------------------------------------------------------------
# JSON-LD / embedded-state extraction (most reliable when present)
# ----------------------------------------------------------------------------
def _safe_json_loads(value: str):
    try:
        return json.loads(value)
    except Exception:
        try:
            cleaned = re.sub(r"^\s*window\.[^=]+=", "", value)
            cleaned = re.sub(r";\s*$", "", cleaned.strip())
            return json.loads(cleaned)
        except Exception:
            return None


def _iter_json_objects(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _iter_json_objects(v)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_json_objects(item)


def _find_product_candidate(node) -> dict | None:
    if not isinstance(node, dict):
        return None
    product_keys = (
        "name",
        "productName",
        "title",
        "price",
        "current_price",
        "salePrice",
        "sellingPrice",
        "originalPrice",
        "mrp",
        "rating",
        "ratingValue",
        "averageRating",
        "productRating",
        "ratings",
        "reviewCount",
        "reviews",
        "totalReviews",
        "discountPercentage",
        "image",
    )
    if any(key in node for key in product_keys):
        return node
    for key in ("product", "productDetails", "pageProps", "props", "data"):
        child = node.get(key)
        if isinstance(child, dict):
            found = _find_product_candidate(child)
            if found is not None:
                return found
    return None


def _extract_product_jsonld(html: str) -> dict:
    """Look for schema.org Product markup: name, image, offers.price, aggregateRating."""
    logger.info("Attempting to extract JSON-LD product data...")
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.select('script[type="application/ld+json"]')
    logger.debug(f"Found {len(scripts)} JSON-LD script tags")
    for script in scripts:
        payload = _safe_json_loads(script.string or "")
        if not payload:
            continue
        for obj in _iter_json_objects(payload):
            if not isinstance(obj, dict):
                continue
            obj_type = obj.get("@type") if isinstance(obj, dict) else None
            type_matches = obj_type == "Product" or (isinstance(obj_type, list) and "Product" in obj_type)
            if not type_matches:
                continue

            offers = obj.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            aggregate = obj.get("aggregateRating") or {}

            result = {
                "product_name": _clean_text(obj.get("name") or obj.get("productName") or obj.get("title")),
                "product_image": obj.get("image") if isinstance(obj.get("image"), str) else (obj.get("image") or [None])[0],
                "description": _clean_text(obj.get("description")),
                "current_price": _normalize_price(offers.get("price") or offers.get("priceValue") or offers.get("lowPrice")),
                # MRP / strikethrough price only - never mirror the selling price
                # here, otherwise the discount math and MRP display break.
                "original_price": _normalize_price(offers.get("highPrice") or offers.get("listPrice") or offers.get("mrp")),
                "rating": _valid_product_rating(aggregate.get("ratingValue")) if aggregate else None,
                "total_ratings": int(aggregate["ratingCount"]) if aggregate.get("ratingCount") else None,
                "total_reviews": int(aggregate["reviewCount"]) if aggregate.get("reviewCount") else None,
            }
            logger.debug(f"JSON-LD extracted: name={result['product_name']}, price={result['current_price']}, rating={result['rating']}")
            reviews = []
            raw_reviews = obj.get("review") or []
            if isinstance(raw_reviews, dict):
                raw_reviews = [raw_reviews]
            for r in raw_reviews:
                text = _clean_text(r.get("reviewBody") or r.get("description") or r.get("comment"))
                if not text:
                    continue
                author = r.get("author")
                reviewer_name = author.get("name") if isinstance(author, dict) else (author or "")
                r_rating = r.get("reviewRating") or {}
                reviews.append({
                    "review_text": text,
                    "rating": int(_normalize_rating(r_rating.get("ratingValue"))) if isinstance(r_rating, dict) else 0,
                    "review_rating": int(_normalize_rating(r_rating.get("ratingValue"))) if isinstance(r_rating, dict) else 0,
                    "reviewer_name": _clean_text(reviewer_name),
                    "review_date": _clean_text(r.get("datePublished") or r.get("date")),
                    "verified_purchase": bool(r.get("verified") or r.get("verifiedPurchase")),
                    "platform": "firstcry",
                })
            result["reviews"] = reviews
            logger.info("Selector succeeded: JSON-LD product data")
            return {k: v for k, v in result.items() if v not in (None, "", [])}
    logger.info("Selector failed: JSON-LD product data not found")
    return {}


def _extract_embedded_json_payload(html: str) -> dict:
    logger.info("Attempting to extract embedded JSON payload...")
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.find_all("script")
    logger.debug(f"Found {len(scripts)} script tags")
    for script in scripts:
        content = script.string or script.get_text(" ", strip=True) or ""
        if not content:
            continue
        payload = _safe_json_loads(content)
        if not payload:
            continue
        for obj in _iter_json_objects(payload):
            if not isinstance(obj, dict):
                continue
            product_candidate = _find_product_candidate(obj)
            if product_candidate is None:
                continue
            obj_type = obj.get("@type")
            type_matches = obj_type == "Product" or (isinstance(obj_type, list) and "Product" in obj_type)
            if not type_matches:
                if not any(
                    key in product_candidate
                    for key in (
                        "name",
                        "productName",
                        "title",
                        "price",
                        "current_price",
                        "salePrice",
                        "sellingPrice",
                        "originalPrice",
                        "mrp",
                        "rating",
                        "ratingValue",
                        "averageRating",
                        "productRating",
                        "ratings",
                        "reviewCount",
                        "reviews",
                        "totalReviews",
                        "discountPercentage",
                        "image",
                    )
                ):
                    continue
            result = {
                "product_name": _clean_text(product_candidate.get("name") or product_candidate.get("productName") or product_candidate.get("title")),
                "product_image": product_candidate.get("image") if isinstance(product_candidate.get("image"), str) else (product_candidate.get("image") or [None])[0],
                "description": _clean_text(product_candidate.get("description")),
                "current_price": _normalize_price(product_candidate.get("price") or product_candidate.get("current_price") or product_candidate.get("salePrice") or product_candidate.get("sellingPrice")),
                "original_price": _normalize_price(product_candidate.get("originalPrice") or product_candidate.get("original_price") or product_candidate.get("mrp") or product_candidate.get("strikethroughPrice")),
                "discount_percentage": int(product_candidate.get("discountPercentage")) if isinstance(product_candidate.get("discountPercentage"), int) else None,
                "rating": _valid_product_rating(product_candidate.get("rating") or product_candidate.get("ratingValue") or product_candidate.get("averageRating") or product_candidate.get("productRating")),
                "total_ratings": int(re.sub(r"[^\d]", "", str(product_candidate.get("ratings") or product_candidate.get("ratingCount") or product_candidate.get("totalRatings") or ""))) if re.search(r"\d", str(product_candidate.get("ratings") or product_candidate.get("ratingCount") or product_candidate.get("totalRatings") or "")) else None,
                "total_reviews": int(re.sub(r"[^\d]", "", str(product_candidate.get("reviews") or product_candidate.get("reviewCount") or product_candidate.get("totalReviews") or ""))) if re.search(r"\d", str(product_candidate.get("reviews") or product_candidate.get("reviewCount") or product_candidate.get("totalReviews") or "")) else None,
            }
            if result.get("product_name") or result.get("current_price") or result.get("rating"):
                logger.debug(f"Embedded JSON extracted: name={result['product_name']}, price={result['current_price']}, rating={result['rating']}")
                logger.info("Selector succeeded: embedded JSON payload")
                return {k: v for k, v in result.items() if v not in (None, "", [])}
    logger.info("Selector failed: embedded JSON payload not found")
    return {}


# ----------------------------------------------------------------------------
# Fallback: scan raw text for price / rating patterns (works even if class
# names change, since it doesn't rely on any CSS selector at all)
# ----------------------------------------------------------------------------
def _find_price_mrp_discount_pattern(soup: BeautifulSoup) -> tuple[float | None, float | None, int | None]:
    """FirstCry (and most Indian e-commerce sites) render prices as a fixed
    sequence: '₹976 MRP: ₹2579 62% OFF'. Matching that exact sequence is far
    more reliable than scanning every ₹ amount on the page, since it can't
    accidentally grab a bank-offer/EMI/variant price sitting elsewhere."""
    logger.info("Attempting to extract price/MRP/discount pattern...")
    text = soup.get_text(" ", strip=True)
    # FirstCry renders the paise as a superscript, so the selling price comes
    # through the text as "₹652 86" (rupees and paise separated by a space)
    # rather than "₹652.86". Capture that optional space-separated 2-digit paise
    # group and fold it back in. We also use [^\d₹] (not \D) to bridge to the
    # "MRP" label so the matcher can never leap across another ₹ block or a
    # stray number and grab a different product's price.
    def _compose(rupees: str, paise: str | None) -> float | None:
        base = _normalize_price(rupees)
        if base is None:
            return None
        if paise and "." not in rupees:
            return float(f"{int(base)}.{paise}")
        return base

    pattern = re.compile(
        r"₹\s?([\d,]+(?:\.\d{1,2})?)(?:\s+(\d{2})\b)?"
        r"[^\d₹]{0,30}?MRP[^\d₹]{0,12}?"
        r"₹\s?([\d,]+(?:\.\d{1,2})?)(?:\s+\d{2}\b)?"
        r"[^\d₹]{0,20}?(\d{1,3})\s?%",
        re.I,
    )
    match = pattern.search(text)
    if match:
        current = _compose(match.group(1), match.group(2))
        original = _normalize_price(match.group(3))
        discount = int(match.group(4))
        logger.debug(f"Price pattern extracted: current={current}, original={original}, discount={discount}")
        logger.info("Selector succeeded: price regex pattern")
        return current, original, discount

    # fallback order: "MRP ₹2579" ... "₹976" ... "62% off" (MRP mentioned first)
    pattern2 = re.compile(
        r"MRP[^\d₹]{0,12}?₹\s?([\d,]+(?:\.\d{1,2})?)(?:\s+\d{2}\b)?"
        r"[^\d₹]{0,30}?₹\s?([\d,]+(?:\.\d{1,2})?)(?:\s+(\d{2})\b)?"
        r"[^\d₹]{0,20}?(\d{1,3})\s?%",
        re.I,
    )
    match2 = pattern2.search(text)
    if match2:
        original = _normalize_price(match2.group(1))
        current = _compose(match2.group(2), match2.group(3))
        discount = int(match2.group(4))
        logger.debug(f"Price pattern (fallback) extracted: current={current}, original={original}, discount={discount}")
        logger.info("Selector succeeded: price regex pattern (fallback)")
        return current, original, discount

    logger.info("Selector failed: price regex pattern not found")
    return None, None, None


JUNK_PRICE_CONTEXT = (
    "minimum", "club cash", "cashback", "cash back", "shipping", "delivery",
    "emi", "wallet", "earn", "redeem", "reverse pickup", "membership",
    "orders above", "order value", "coupon", "gift card", "loyalty",
    "installment", "installments", "per month", "starting at", "bank offer",
    "instant discount", "instant cashback", "no cost emi",
)


def _find_prices_in_text(soup: BeautifulSoup) -> list[float]:
    """Scan for ₹ amounts, but skip ones sitting inside boilerplate text
    (footer notes like 'minimum ₹99 to place an order', club-cash notes,
    EMI notes, etc.) by checking the *immediate* parent element's text
    rather than the whole page's text blob."""
    prices = []
    for node in soup.find_all(string=re.compile(r"₹")):
        parent = node.parent
        context_parts = [str(node)]
        p = parent
        for _ in range(2):
            if p is None:
                break
            context_parts.append(p.get_text(" ", strip=True))
            p = p.parent
        context = " ".join(context_parts).lower()
        if any(junk in context for junk in JUNK_PRICE_CONTEXT):
            continue
        for match in re.finditer(r"₹\s?([\d,]+(?:\.\d{1,2})?)", str(node)):
            value = _normalize_price(match.group(1))
            if value and value > 10:  # ignore tiny junk amounts (e.g. "₹2 club cash")
                prices.append(value)
    return prices


def _extract_microdata_product(soup: BeautifulSoup) -> dict:
    """Many e-commerce sites embed schema.org microdata via itemprop=
    attributes even when there's no full JSON-LD block. Cheap and reliable
    when present."""
    logger.info("Attempting to extract microdata product info...")
    result: dict = {}

    price_el = soup.select_one("[itemprop='price']")
    if price_el:
        value = price_el.get("content") or price_el.get_text(" ", strip=True)
        price = _normalize_price(value)
        if price:
            result["current_price"] = price
            logger.debug(f"Microdata extracted price: {price}")

    rating_el = soup.select_one("[itemprop='ratingValue']")
    if rating_el:
        value = rating_el.get("content") or rating_el.get_text(" ", strip=True)
        rating = _valid_product_rating(value)
        if rating is not None:
            result["rating"] = rating
            logger.debug(f"Microdata extracted rating: {rating}")

    count_el = soup.select_one("[itemprop='reviewCount'], [itemprop='ratingCount']")
    if count_el:
        value = count_el.get("content") or count_el.get_text(" ", strip=True)
        digits = re.sub(r"[^\d]", "", value or "")
        if digits:
            result["total_ratings"] = int(digits)
            logger.debug(f"Microdata extracted total_ratings: {digits}")

    if result:
        logger.info("Selector succeeded: microdata product info")
    else:
        logger.info("Selector failed: microdata product info not found")
    return result


def _find_rating_in_text(soup: BeautifulSoup) -> float | None:
    text = soup.get_text(" ", strip=True)
    match = re.search(r"\b([0-5](?:\.\d)?)\s*(?:out of|/)\s*5\b", text, re.I)
    if match:
        return _normalize_rating(match.group(1))
    return None


# Keys any embedded state / structured-data blob might use for a product rating.
_RATING_JSON_KEYS = {
    "ratingvalue", "rating", "averagerating", "avgrating", "avg_rating",
    "average_rating", "overallrating", "overall_rating", "productrating",
    "product_rating", "starrating", "star_rating", "ratingscore",
    "rating_score", "ratingsaverage", "ratings_average", "avgstar", "avg_star",
}


def _find_rating_in_embedded_json(html: str) -> float | None:
    """Scan every <script> JSON blob (JSON-LD, __NEXT_DATA__, Redux/`window.*`
    state, etc.) for any rating-like key and return the first plausible value.
    This does not depend on any CSS selector, so it survives DOM/markup changes."""
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script"):
        content = script.string or script.get_text(" ", strip=True) or ""
        if not content or "rating" not in content.lower():
            continue
        payload = _safe_json_loads(content)
        if not payload:
            continue
        for obj in _iter_json_objects(payload):
            if not isinstance(obj, dict):
                continue
            for key, value in obj.items():
                if str(key).lower() not in _RATING_JSON_KEYS:
                    continue
                candidate = value
                if isinstance(value, dict):
                    candidate = value.get("value") or value.get("ratingValue") or value.get("average")
                if isinstance(candidate, (int, float, str)):
                    rating = _valid_product_rating(candidate)
                    if rating is not None:
                        logger.info("Product rating from embedded JSON key '%s': %s", key, rating)
                        return rating
    return None


def _find_rating_in_dom_attributes(soup: BeautifulSoup) -> float | None:
    """Read a rating stored in a data-* attribute (e.g. data-rating='4.2')."""
    for attr in ("data-rating", "data-star", "data-stars", "data-average-rating",
                 "data-avg-rating", "data-rating-value", "data-score"):
        for el in soup.select(f"[{attr}]"):
            rating = _valid_product_rating(el.get(attr))
            if rating is not None:
                logger.info("Product rating from DOM attribute '%s': %s", attr, rating)
                return rating
    return None


def _find_rating_by_star_width(soup: BeautifulSoup) -> float | None:
    """Derive a rating from a star-fill width percentage (100% width = 5 stars),
    a very common way of rendering fractional stars."""
    for el in soup.select(
        "[class*='star' i] [style*='width' i], [class*='rating' i] [style*='width' i], "
        "[style*='width' i][class*='fill' i], [style*='width' i][class*='star' i]"
    ):
        style = el.get("style") or ""
        match = re.search(r"width\s*:\s*([\d.]+)\s*%", style, re.I)
        if not match:
            continue
        rating = _valid_product_rating(round(float(match.group(1)) / 20.0, 1))
        if rating is not None:
            logger.info("Product rating from star-fill width %s%%: %s", match.group(1), rating)
            return rating
    return None


def _find_review_count_in_text(soup: BeautifulSoup) -> int | None:
    text = soup.get_text(" ", strip=True)
    match = re.search(r"([\d,]+)\s*(?:ratings?|reviews?)\b", text, re.I)
    if match:
        digits = re.sub(r"[^\d]", "", match.group(1))
        return int(digits) if digits else None
    return None


def _find_rating_review_counts(soup: BeautifulSoup) -> tuple[int | None, int | None]:
    rating_count = None
    review_count = None
    for el in soup.select("[class*='rating-count' i], [class*='review-count' i], [class*='rating' i], [class*='review' i]"):
        text = _clean_text(el.get_text(" ", strip=True))
        if not text:
            continue
        if re.search(r"\b(?:ratings?|reviews?)\b", text, re.I):
            digits = re.sub(r"[^\d]", "", text)
            if not digits:
                continue
            if "review" in text.lower() and review_count is None:
                review_count = int(digits)
            elif "rating" in text.lower() and rating_count is None:
                rating_count = int(digits)
    if rating_count is None or review_count is None:
        text = soup.get_text(" ", strip=True)
        matches = re.findall(r"([\d,]+)\s*(ratings?|reviews?)", text, re.I)
        if matches:
            for value, label in matches:
                digits = re.sub(r"[^\d]", "", value)
                if not digits:
                    continue
                if label.lower().startswith("review") and review_count is None:
                    review_count = int(digits)
                elif label.lower().startswith("rating") and rating_count is None:
                    rating_count = int(digits)
    return rating_count, review_count


# Unambiguous site-chrome phrases that NEVER appear inside a genuine customer
# review. A single occurrence is enough to reject the text as navigation/footer/
# menu/breadcrumb/related-products content (Issue 2).
_CHROME_PHRASES = (
    "shopping cart", "recently viewed", "stores & preschools", "stores and preschools",
    "my account", "track order", "download app", "download the app", "privacy policy",
    "terms of service", "terms & conditions", "sort by", "price low to high",
    "price high to low", "add to cart", "buy now", "add to wishlist", "sign in",
    "log in", "customer care", "return policy", "gift card", "club cash", "bank offer",
    "similar products", "related products", "you may also like", "recommended for you",
    "product description", "product specifications", "frequently bought",
    "recently searched", "browse categories", "all categories", "site map", "sitemap",
    "newsletter", "follow us", "back to top", "view all", "no cost emi", "become a seller",
    "help center", "help centre", "corporate", "franchise", "investor",
)


def _looks_like_review_text(text: str) -> bool:
    cleaned = _clean_text(text)
    if not cleaned:
        return False
    lowered = cleaned.lower()
    # Hard reject: any unambiguous site-chrome phrase means this is not a review.
    for phrase in _CHROME_PHRASES:
        if phrase in lowered:
            logger.debug("Filtered review text (site-chrome phrase '%s'): %s", phrase, cleaned[:80])
            return False
    banned = [
        "ratings & reviews",
        "tap on the stars to rate this product",
        "write a review",
        "be the first to review",
        "product description",
        "similar products",
        "review this product",
        "add a review",
        "all reviews",
        "customer reviews",
        "review section",
        "navigation",
        "menu",
        "home",
        "cart",
        "wishlist",
        "my account",
        "sign in",
        "signin",
        "login",
        "logout",
        "register",
        "footer",
        "copyright",
        "privacy policy",
        "terms of service",
        "contact us",
        "about us",
        "category",
        "categories",
        "brands",
        "offers",
        "deals",
        "subscribe",
        "newsletter",
        "follow us",
        "social media",
        "facebook",
        "twitter",
        "instagram",
        "youtube",
        "download app",
        "mobile app",
        "track order",
        "support",
        "help",
        "faq",
        "returns",
        "shipping",
        "delivery",
        "payment",
        "secure payment",
        "cash on delivery",
        "emi",
        "bank offer",
        "coupon",
        "promo code",
        "gift card",
        "loyalty",
        "membership",
        "club cash",
        "firstcry",
        "baby kids",
        "search results",
        "filter",
        "sort by",
        "relevance",
        "price low to high",
        "price high to low",
        "newest first",
        "popularity",
        "discount",
        "view details",
        "buy now",
        "add to cart",
        "out of stock",
        "in stock",
        "sold out",
        "limited stock",
        "exclusive",
        "bestseller",
        "trending",
        "new arrival",
        "top rated",
        "featured",
        "recommended",
        "sponsored",
        "advertisement",
        "ad",
    ]
    banned_hits = [token for token in banned if token in lowered]
    # Multiple chrome keywords, or a single one in a short line, means this is a
    # menu/footer/category block rather than a genuine review.
    if len(banned_hits) >= 2 or (banned_hits and len(cleaned.split()) <= 8):
        logger.debug("Filtered review text (chrome keywords %s): %s", banned_hits[:3], cleaned[:80])
        return False
    if any(token in lowered for token in ("button", "placeholder", "label", "heading", "title", "nav", "footer", "header")):
        logger.debug(f"Filtered review text (UI element): {cleaned[:100]}...")
        return False
    # Check if text is too short or lacks meaningful content
    meaningful_words = re.findall(r"[A-Za-z]{3,}", cleaned)
    if len(meaningful_words) < 5:
        logger.debug(f"Filtered review text (too short): {cleaned[:100]}...")
        return False
    # Check if text is mostly numbers or special characters
    alpha_ratio = sum(c.isalpha() for c in cleaned) / len(cleaned) if cleaned else 0
    if alpha_ratio < 0.5:
        logger.debug(f"Filtered review text (low alpha ratio): {cleaned[:100]}...")
        return False
    return True


def _extract_card_rating(card) -> int:
    """Extract a per-review star rating from a review card. Checks (in order):
    explicit accessibility attributes (aria-label/title/data-rating like
    'Rated 4 out of 5'), a rating-labelled element with numeric text, then a
    count of filled star elements. Returns 0 when no rating is present."""
    # 1) accessibility / data attributes anywhere in the card - require an
    #    explicit "/5", "out of 5" or "star(s)" qualifier so we never mistake an
    #    unrelated number (e.g. "3 people found this helpful") for a rating.
    for el in card.find_all(True):
        for attr in ("data-rating", "aria-label", "title"):
            val = el.get(attr)
            if not val:
                continue
            match = re.search(r"([0-5](?:\.\d)?)\s*(?:/\s*5|out of\s*5|stars?)", str(val), re.I)
            if match:
                rating = _normalize_rating(match.group(1))
                if 0 < rating <= 5:
                    return int(round(rating))

    # 2) a rating-labelled element with bare numeric text (e.g. <div class="review-rating">5</div>)
    rating_el = card.select_one("[class*='review-rating' i], [class*='rating' i], [data-rating]")
    if rating_el:
        rating = _normalize_rating(rating_el.get_text(" ", strip=True))
        if 0 < rating <= 5:
            return int(round(rating))

    # 3) count filled/active star icons
    filled = card.select(
        "[class*='star' i][class*='fill' i], [class*='star' i][class*='active' i], "
        "[class*='star' i][class*='selected' i], svg[class*='fill' i]"
    )
    if 0 < len(filled) <= 5:
        return len(filled)
    return 0


# Ancestor id/class tokens that mark site chrome (never the review section).
_CHROME_ANCESTOR_TOKENS = (
    "nav", "menu", "footer", "header", "breadcrumb", "cart", "recently",
    "category", "categories", "sidebar", "related", "recommend", "similar",
    "banner", "advertis", "sponsor", "megamenu", "topbar", "subheader",
    "store", "preschool", "wishlist", "you-may", "youmay", "suggest",
)


def _is_in_site_chrome(el) -> bool:
    """True when the element lives inside site chrome (nav/header/footer/menu/
    breadcrumb/recently-viewed/related), i.e. NOT the customer-review section."""
    depth = 0
    for parent in el.parents:
        depth += 1
        if depth > 8:
            break
        if parent.name in ("nav", "header", "footer"):
            return True
        ident = " ".join(
            filter(None, [str(parent.get("id") or ""), " ".join(parent.get("class") or [])])
        ).lower()
        if any(token in ident for token in _CHROME_ANCESTOR_TOKENS):
            return True
    return False


def _looks_like_review_card(card) -> bool:
    """A genuine review card is not inside site chrome, is not link-dense (menus
    are), and carries a review signal (a rating/reviewer/date element) or an
    explicit review-item class. This is what keeps navigation/footer/menu blocks
    out of the review list (Issue 2)."""
    if _is_in_site_chrome(card):
        return False
    if len(card.find_all("a")) > 2:  # menus/footers are link-dense; reviews are not
        return False
    ident = (" ".join(card.get("class") or []) + " " + str(card.get("id") or "")).lower()
    strong_class = any(
        token in ident
        for token in (
            "review-card", "reviewcard", "customer-review", "customerreview",
            "review-item", "reviewitem", "user-review", "userreview", "review-box",
            "rating-review", "ratingreview",
        )
    )
    has_signal = bool(
        card.select_one(
            "[class*='review-rating' i], [class*='star' i], [class*='rating' i], "
            "[class*='reviewer' i], [class*='author' i], [class*='user-name' i], "
            "[class*='username' i], time, [class*='review-date' i], [class*='posted' i], "
            "[class*='verified' i]"
        )
    )
    return strong_class or has_signal


def _extract_review_text(card) -> str:
    for selector in [
        "[class*='review-text' i]",
        "[class*='review-body' i]",
        "[class*='review-content' i]",
        "[class*='reviewdescription' i]",
        "[class*='review-desc' i]",
        ".review-text",
        ".review-body",
        ".review-content",
        ".comment",
        ".message",
    ]:
        text_el = card.select_one(selector)
        if text_el:
            text = _clean_text(text_el.get_text(" ", strip=True))
            if text:
                return text
    # get_text fallback ONLY for a single review item - never for a container that
    # wraps multiple reviews (that would concatenate them into one giant "review").
    if card.select_one("[class*='review-card' i], [class*='review-item' i], [class*='customer-review' i]"):
        return ""
    return _clean_text(card.get_text(" ", strip=True))


def extract_reviews_from_html(html: str, max_reviews: int = 10) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    reviews = []
    seen = set()

    for script in soup.select('script[type="application/ld+json"]'):
        payload = _safe_json_loads(script.string or "")
        if not payload:
            continue
        for obj in _iter_json_objects(payload):
            if not isinstance(obj, dict):
                continue
            raw_reviews = obj.get("review") or obj.get("reviews") or []
            if isinstance(raw_reviews, dict):
                raw_reviews = [raw_reviews]
            for review in raw_reviews:
                if not isinstance(review, dict):
                    continue
                text = _clean_text(review.get("reviewBody") or review.get("description") or review.get("comment") or review.get("text"))
                if not text or not _looks_like_review_text(text):
                    continue
                author = review.get("author")
                reviewer_name = author.get("name") if isinstance(author, dict) else (author or "")
                rating_value = review.get("reviewRating") or review.get("rating") or {}
                rating = int(_normalize_rating(rating_value.get("ratingValue") if isinstance(rating_value, dict) else rating_value)) if _normalize_rating(rating_value.get("ratingValue") if isinstance(rating_value, dict) else rating_value) else 0
                signature = (text.lower(), _clean_text(reviewer_name).lower(), str(rating))
                if signature in seen:
                    continue
                seen.add(signature)
                reviews.append({
                    "review_text": text,
                    "rating": rating,
                    "review_rating": rating,
                    "reviewer_name": _clean_text(reviewer_name),
                    "review_date": _clean_text(review.get("datePublished") or review.get("date")),
                    "verified_purchase": bool(review.get("verified") or review.get("verifiedPurchase")),
                    "platform": "firstcry",
                })
                if len(reviews) >= max_reviews:
                    return reviews

    # IMPORTANT: only look inside review-oriented containers. The previous
    # `article, li` catch-all matched every navigation/footer/menu list item,
    # which is how page chrome leaked in as "reviews" (Issue 2).
    review_blocks = soup.select(
        "[class*='review-card' i], [class*='reviewcard' i], [class*='customer-review' i], "
        "[class*='customerreview' i], [class*='rating-review' i], [class*='ratingreview' i], "
        "[class*='review-item' i], [class*='reviewitem' i], [class*='user-review' i], "
        "[class*='userreview' i], [class*='review-box' i], [class*='review' i], [id*='review' i]"
    )
    for card in review_blocks:
        classes = " ".join(card.get("class", []) or []).lower()
        # skip review sub-fields (they are extracted from within the card)
        if any(token in classes for token in ("review-text", "review-rating", "reviewer-name", "review-date", "author-name", "user-name", "name")):
            continue
        # skip anything that is not structurally a genuine review card
        if not _looks_like_review_card(card):
            continue
        text = _extract_review_text(card)
        if not _looks_like_review_text(text):
            continue
        if text.lower() in {"ratings & reviews", "write a review", "be the first to review"}:
            continue
        rating = _extract_card_rating(card)
        reviewer_el = card.select_one("[class*='reviewer' i], [class*='author' i], [class*='user' i], [class*='name' i]")
        review_date_el = card.select_one("time, [class*='date' i], [class*='posted' i]")
        reviewer_name = _clean_text(reviewer_el.get_text(" ", strip=True)) if reviewer_el else ""
        signature = (text.lower(), reviewer_name.lower(), str(rating))
        if signature in seen:
            continue
        seen.add(signature)
        verified_purchase = "verified" in card.get_text(" ", strip=True).lower()
        reviews.append({
            "review_text": text,
            "rating": rating,
            "review_rating": rating,
            "reviewer_name": reviewer_name,
            "review_date": _clean_text(review_date_el.get_text(" ", strip=True)) if review_date_el else "",
            "verified_purchase": verified_purchase,
            "platform": "firstcry",
        })
        if len(reviews) >= max_reviews:
            break
    return reviews


# ----------------------------------------------------------------------------
# Product link selection from a search-results page
# ----------------------------------------------------------------------------
def _score_title_match(title: str, query: str) -> int:
    title_tokens = set(re.findall(r"[a-z0-9]+", title.lower()))
    query_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    return len(title_tokens & query_tokens)


# Generic descriptors that appear across many baby-product titles - they are not
# distinctive enough to decide *what kind* of product it is.
_MATCH_STOPWORDS = {
    "baby", "babies", "kids", "kid", "for", "the", "and", "with", "new", "born",
    "newborn", "infant", "infants", "toddler", "boys", "girls", "boy", "girl",
    "unisex", "pack", "of", "set", "piece", "pieces", "pcs", "size", "a", "an",
    "combo", "multicolor", "multicolour", "assorted", "premium", "soft",
}


def _normalize_for_match(text: str) -> str:
    """Lowercase and strip case/spacing/hyphens/special characters so the search
    keyword and a product title can be compared fairly."""
    normalized = re.sub(r"[^a-z0-9]+", " ", (text or "").lower())
    return re.sub(r"\s+", " ", normalized).strip()


def _token_in(token: str, token_set: set[str]) -> bool:
    """Membership test tolerant of simple singular/plural forms
    (diaper/diapers, bottle/bottles)."""
    if token in token_set:
        return True
    base = token.rstrip("s")
    return any(existing.rstrip("s") == base for existing in token_set)


def _title_matches_query(title: str, query: str) -> bool:
    """Verify a product title actually matches the searched keyword.

    Rule: the query's HEAD noun (its last distinctive token, e.g. shirt / soap /
    bottle / diapers) must be present in the title, and at least half of the
    distinctive query tokens must appear. This lets 'baby t shirt' match
    'Baby Boys T Shirt' while rejecting 'Intelliskill Toys'."""
    query_tokens = _normalize_for_match(query).split()
    title_tokens = set(_normalize_for_match(title).split())
    if not query_tokens:
        return True
    content = [w for w in query_tokens if w not in _MATCH_STOPWORDS and len(w) >= 2]
    if not content:  # query was only generic words (e.g. just "baby") - fall back
        content = [w for w in query_tokens if len(w) >= 2] or query_tokens
    head = content[-1]
    if not _token_in(head, title_tokens):
        return False
    matched = sum(1 for w in content if _token_in(w, title_tokens))
    return matched >= max(1, (len(content) + 1) // 2)


# The main search-results grid on FirstCry wraps every product in one of these
# card containers. Recommendation carousels ("You may also like", "Recently
# viewed", bestseller sliders) live OUTSIDE these, so scoping to them removes the
# carousel products that otherwise appear first in DOM order and get mistaken for
# the "first search result".
_GRID_CARD_SELECTOR = ".li_inner_block, .list_block, li[class*='product' i], div[class*='product-card' i]"


def _collect_product_anchors(anchors, query: str, seen_hrefs: set) -> tuple[list, list]:
    """Scan anchors (in DOM order) and split real products into keyword-matched
    and other (both preserve DOM order). Brand/category listings and invalid
    titles are dropped."""
    matched: list[tuple[str, str]] = []
    other: list[tuple[str, str]] = []
    for anchor in anchors:
        href = (anchor.get("href") or "").strip()
        if not href or href in seen_hrefs:
            continue
        # must be a real product-detail link (never a brand/category listing)
        if not _is_product_link(href):
            continue
        # Title = anchor title/text; for an image-only product link (common on
        # FirstCry cards) fall back to the product image's alt text.
        text = _clean_text(anchor.get("title") or anchor.get_text(" ", strip=True))
        if not text:
            img = anchor.find("img")
            if img is not None:
                text = _clean_text(img.get("alt") or img.get("title") or "")
        # NOTE: only mark this href 'seen' once we have a usable title, so a
        # title-less image anchor doesn't block its sibling title anchor.
        if not text or not _looks_like_valid_title(text):
            continue
        seen_hrefs.add(href)
        full_url = href if href.startswith("http") else urljoin(BASE_URL, href)
        if _title_matches_query(text, query):
            matched.append((text, full_url))
        else:
            other.append((text, full_url))
    return matched, other


def _rank_product_candidates(soup: BeautifulSoup, query: str) -> list[tuple[str, str]]:
    """Return real product cards for the search, in the order they appear on the
    page (first = first product on FirstCry's results grid). Recommendation
    carousels and brand/category listings are excluded. Keyword-matching products
    come first; if the grid's leading product doesn't match the keyword we still
    keep it as a fallback so the FIRST real product is never dropped to N/A."""
    seen_hrefs: set[str] = set()

    # 1) Prefer the MAIN results grid so carousels/recommendations can't jump the
    #    queue. Scan grid cards in DOM order.
    grid_cards = soup.select(_GRID_CARD_SELECTOR)
    grid_anchors: list = []
    for card in grid_cards:
        grid_anchors.extend(card.select("a[href]"))
    matched, other = _collect_product_anchors(grid_anchors, query, seen_hrefs)

    # 2) If the grid wasn't found (page markup changed), fall back to the whole
    #    page - still in DOM order.
    if not matched and not other:
        matched, other = _collect_product_anchors(soup.select("a[href]"), query, seen_hrefs)
        source = "whole-page"
    else:
        source = "results-grid"

    logger.info(
        "Search scan (%s): %s keyword-matched + %s other product(s) for %r; first match=%r",
        source, len(matched), len(other), query, matched[0][0] if matched else None,
    )
    # matched first (DOM order) so we never open an unrelated product; `other`
    # (DOM order) is a fallback so an all-non-matching grid still yields its first
    # real product instead of failing.
    return matched + other


def _select_best_product_link(soup: BeautifulSoup, query: str) -> tuple[str | None, str | None]:
    """Return the best product whose TITLE actually matches the search keyword.
    Returns (None, None) when no result matches - the scraper must never open an
    unrelated product (e.g. a toy for a 'baby t-shirt' search)."""
    matches = _rank_product_candidates(soup, query)
    if not matches:
        logger.warning("No product on the search page matched the keyword %r - not opening any product", query)
        return None, None
    best_title, best_url = matches[0]
    logger.info("Selected product: %r -> %s", best_title, best_url)
    return best_url, best_title


# ----------------------------------------------------------------------------
# Product page extraction (combines JSON-LD -> selectors -> raw text scan)
# ----------------------------------------------------------------------------
def extract_product_details(html: str, query: str | None = None) -> dict:
    logger.info("=== Starting product details extraction ===")
    soup = BeautifulSoup(html, "html.parser")

    jsonld = _extract_product_jsonld(html)
    embedded = _extract_embedded_json_payload(html)
    microdata = _extract_microdata_product(soup)

    merged = dict(jsonld)
    if embedded:
        for key, value in embedded.items():
            if value not in (None, "", [], {}):
                if key not in merged or merged.get(key) in (None, "", [], {}):
                    merged[key] = value

    # FirstCry-specific product name selectors - avoid navigation/footer text
    product_name = (
        merged.get("product_name")
        or jsonld.get("product_name")
        or _clean_text((soup.select_one("meta[property='og:title']") or {}).get("content", "") if soup.select_one("meta[property='og:title']") else "")
        or _clean_text((soup.select_one("meta[property='og:title']") or {}).get("content", "") if soup.select_one("meta[property='og:title']") else "")
    )
    if not product_name:
        for selector in ["h1", "h2", "[class*='title' i]", "[class*='product-name' i]", "[class*='productTitle' i]"]:
            candidate = soup.select_one(selector)
            if not candidate:
                continue
            text = _clean_text(candidate.get_text(" ", strip=True))
            if _looks_like_valid_title(text):
                product_name = text
                break
    
    # If still invalid, try FirstCry-specific selectors only
    if not _looks_like_valid_title(product_name):
        logger.debug("Product name from primary selectors invalid, trying FirstCry-specific selectors...")
        firstcry_selectors = [
            ".product-title",
            ".prod-title",
            "h1[class*='product' i]",
            "[class*='product-name' i]",
            "[class*='productTitle' i]",
            ".pdp-product-title",
            ".product-detail-title",
        ]
        for selector in firstcry_selectors:
            candidate = soup.select_one(selector)
            if not candidate:
                continue
            text = _clean_text(candidate.get_text(" ", strip=True))
            if _looks_like_valid_title(text):
                product_name = text
                logger.debug(f"Product name found via FirstCry selector '{selector}': {text}")
                break
    
    # Final fallback to query if still invalid
    if not _looks_like_valid_title(product_name):
        logger.debug("Product name still invalid, using query as fallback")
        product_name = (query or "").strip()
    logger.info(f"Final product name: {product_name}")

    # FirstCry-specific image selectors
    product_image = merged.get("product_image") or jsonld.get("product_image")
    if not product_image:
        logger.debug("Product image from JSON not found, trying FirstCry-specific selectors...")
        firstcry_image_selectors = [
            "meta[property='og:image']",
            "img[class*='product' i]",
            "img[class*='main' i]",
            "img[class*='primary' i]",
            ".product-image img",
            ".pdp-product-img img",
            "[id*='product' i][id*='image' i]",
            "img[id*='product' i]",
            "img[src]",
        ]
        for selector in firstcry_image_selectors:
            image_els = soup.select(selector)
            if not image_els:
                continue
            for image_el in image_els:
                src = image_el.get("content") or image_el.get("src") or image_el.get("data-src")
                if not src:
                    continue
                alt = _clean_text(image_el.get("alt") or "")
                if any(token in alt.lower() for token in ("logo", "icon", "sprite", "banner", "ad")):
                    continue
                if any(token in str(src).lower() for token in ("logo", "icon", "sprite", "banner", "ad")):
                    continue
                product_image = src
                logger.debug(f"Product image found via selector '{selector}': {src}")
                break
            if product_image:
                break
    logger.info(f"Product image: {product_image}")

    current_price = merged.get("current_price") or microdata.get("current_price")
    original_price = merged.get("original_price") or microdata.get("original_price")
    discount_percentage = merged.get("discount_percentage")
    logger.debug(f"Initial prices from JSON - current: {current_price}, original: {original_price}, discount: {discount_percentage}")

    pattern_current, pattern_original, pattern_discount = _find_price_mrp_discount_pattern(soup)

    # The "₹X MRP: ₹Y Z% OFF" line is the single most reliable price source on a
    # FirstCry product page. Embedded JSON blobs frequently belong to a *different*
    # product (a "similar products" / deal widget), so when the canonical price
    # line is present AND internally consistent (MRP > selling, and the stated
    # discount matches the computed one), trust it over the JSON values.
    def _price_line_is_consistent(cur, orig, disc):
        if cur is None or orig is None or disc is None:
            return False
        if not (orig > cur > 0):
            return False
        computed = (orig - cur) / orig * 100
        return abs(computed - disc) <= 3  # allow rounding / dropped-paise slack

    if _price_line_is_consistent(pattern_current, pattern_original, pattern_discount):
        if (current_price, original_price, discount_percentage) != (
            pattern_current, pattern_original, pattern_discount
        ):
            logger.info(
                "Overriding JSON prices (%s/%s/%s%%) with canonical price line (%s/%s/%s%%)",
                current_price, original_price, discount_percentage,
                pattern_current, pattern_original, pattern_discount,
            )
        current_price = pattern_current
        original_price = pattern_original
        discount_percentage = pattern_discount
    elif current_price is None and pattern_current is not None:
        current_price = pattern_current
        original_price = pattern_original
        discount_percentage = pattern_discount
    elif current_price is None:
        logger.info("Selector failed: price regex pattern")

    if current_price is None:
        logger.debug("Current price still None, trying element selectors...")
        price_els = soup.select(
            "[class*='selling-price' i], [class*='offer-price' i], [class*='final-price' i], [class*='current-price' i], .price, .finalPrice"
        )
        for el in price_els:
            value = _normalize_price(el.get_text(" ", strip=True))
            if value and value > 10:
                current_price = value
                logger.info(f"Selector succeeded: price element selector found {value}")
                break
        if current_price is None:
            logger.info("Selector failed: price element selector")

    if original_price is None:
        logger.debug("Original price still None, trying element selectors...")
        mrp_els = soup.select("[class*='mrp' i], [class*='strike' i], [class*='original-price' i]")
        # Also try del and s tags separately to avoid CSS parsing issues
        for tag in soup.find_all(['del', 's']):
            mrp_els.append(tag)
        for el in mrp_els:
            value = _normalize_price(el.get_text(" ", strip=True))
            if value and value > 10 and (current_price is None or value != current_price):
                original_price = value
                logger.info(f"Selector succeeded: original price element selector found {value}")
                break
        if original_price is None:
            logger.info("Selector failed: original price element selector")

    prices_in_text = _find_prices_in_text(soup)
    if current_price is None and prices_in_text:
        current_price = min(prices_in_text)
        logger.info(f"Current price from text scan: {current_price}")
    if original_price is None and prices_in_text and len(set(prices_in_text)) > 1:
        higher = max(p for p in prices_in_text if current_price is None or p >= current_price)
        if current_price and higher > current_price:
            original_price = higher
            logger.info(f"Original price from text scan: {original_price}")

    # --- Price validation (Issue 2) -------------------------------------
    # Guarantee the *selling* price is the lower figure and the MRP the higher
    # one. FirstCry renders the crossed-out MRP next to the discounted price;
    # if extraction picked them up in the wrong order, swap so the MRP is never
    # returned as the selling price when a real selling price exists.
    if current_price is not None and original_price is not None and current_price > original_price:
        logger.info("Correcting price/MRP order: selling %s > MRP %s -> swapping", current_price, original_price)
        current_price, original_price = original_price, current_price
    if current_price is not None and current_price <= 0:
        logger.info("Discarding invalid (non-positive) selling price: %s", current_price)
        current_price = None
    logger.info("Validated selling price: %s | MRP: %s", current_price, original_price)

    if discount_percentage is None:
        if current_price and original_price and original_price > current_price:
            discount_percentage = int(((original_price - current_price) / original_price) * 100)
            logger.info(f"Calculated discount percentage: {discount_percentage}%")
        else:
            disc_match = re.search(r"(\d{1,3})\s*%\s*off", soup.get_text(" ", strip=True), re.I)
            if disc_match:
                discount_percentage = int(disc_match.group(1))
                logger.info(f"Discount percentage from text: {discount_percentage}%")

    # --- Product rating extraction (audited, multi-source, strict) ----------
    # Priority: JSON-LD/embedded aggregateRating -> microdata itemprop ->
    # schema/OG meta tags -> "X out of 5" text -> visible rating elements.
    # Every candidate passes _valid_product_rating so a review COUNT or an
    # out-of-range/zero value can never be returned as the rating.
    logger.info(
        "Raw product rating candidates - jsonld/embedded=%r, microdata=%r",
        merged.get("rating"),
        microdata.get("rating"),
    )
    rating = _valid_product_rating(merged.get("rating")) or _valid_product_rating(microdata.get("rating"))

    # Any embedded JSON blob (JSON-LD aggregateRating, __NEXT_DATA__, window
    # state) - selector-independent, so most robust to markup changes.
    if rating is None:
        rating = _find_rating_in_embedded_json(html)

    if rating is None:
        for meta_selector in [
            "meta[itemprop='ratingValue']",
            "[itemprop='ratingValue']",
            "meta[property='product:rating']",
            "meta[property='og:rating']",
            "meta[name='rating']",
        ]:
            meta_el = soup.select_one(meta_selector)
            if not meta_el:
                continue
            rating = _valid_product_rating(meta_el.get("content") or meta_el.get_text(" ", strip=True))
            if rating is not None:
                logger.info("Product rating from meta/itemprop '%s': %s", meta_selector, rating)
                break

    if rating is None:
        rating = _find_rating_in_dom_attributes(soup)

    if rating is None:
        rating = _valid_product_rating(_find_rating_in_text(soup))
        if rating is not None:
            logger.info("Product rating from 'out of 5' text: %s", rating)

    if rating is None:
        rating = _find_rating_by_star_width(soup)

    if rating is None:
        logger.debug("Rating not found, trying FirstCry-specific visible selectors...")
        firstcry_rating_selectors = [
            "[class*='rating' i] [class*='value' i]",
            "[class*='rating' i] .rating-value",
            "[class*='star' i] [class*='rating' i]",
            ".rating-score",
            ".avg-rating",
            "[class*='product-rating' i]",
            "[class*='rating' i]",
        ]
        for selector in firstcry_rating_selectors:
            for rating_el in soup.select(selector):
                if not rating_el:
                    continue
                # never read a rating/review COUNT element as the rating
                if any(token in str(rating_el.get("class") or "").lower() for token in ("count", "review", "total")):
                    continue
                raw_text = rating_el.get("content") or rating_el.get("data-rating") or rating_el.get_text(" ", strip=True)
                candidate = _valid_product_rating(raw_text)
                if candidate is not None:
                    rating = candidate
                    logger.info("Product rating from visible selector '%s': %s", selector, rating)
                    break
            if rating is not None:
                break

    if rating is None:
        logger.info("Final extracted product rating: None (page truly exposes no rating)")
    else:
        logger.info(f"Final extracted product rating: {rating}")
    
    # FirstCry-specific total ratings extraction
    rating_counts, review_counts = _find_rating_review_counts(soup)
    total_ratings = merged.get("total_ratings") or microdata.get("total_ratings") or rating_counts
    if total_ratings is None:
        # Try FirstCry-specific rating count selectors
        logger.debug("Total ratings not found, trying FirstCry-specific selectors...")
        firstcry_count_selectors = [
            "[class*='rating' i] [class*='count' i]",
            "[class*='review' i] [class*='count' i]",
            ".rating-count",
            ".review-count",
            "[class*='total-ratings' i]",
        ]
        for selector in firstcry_count_selectors:
            count_el = soup.select_one(selector)
            if not count_el:
                continue
            value = count_el.get("content") or count_el.get_text(" ", strip=True)
            digits = re.sub(r"[^\d]", "", value or "")
            if digits:
                total_ratings = int(digits)
                logger.debug(f"Total ratings found via FirstCry selector '{selector}': {digits}")
                break
    
    if total_ratings is None:
        logger.info("Total ratings extraction failed (all methods)")
    else:
        logger.info(f"Total ratings extracted: {total_ratings}")
    
    total_reviews = merged.get("total_reviews") or review_counts
    if total_reviews is None:
        logger.info("Total reviews extraction failed (all methods)")
    else:
        logger.info(f"Total reviews extracted: {total_reviews}")

    description = merged.get("description")
    if not description:
        firstcry_description_selectors = [
            "meta[name='description']",
            "meta[property='og:description']",
            "[class*='description' i]",
            "[class*='product-description' i]",
            "[id*='description' i]",
            "[id*='product-description' i]",
        ]
        for selector in firstcry_description_selectors:
            desc_el = soup.select_one(selector)
            if not desc_el:
                continue
            value = desc_el.get("content") or desc_el.get_text(" ", strip=True)
            description = _clean_text(value)
            if description:
                break
        logger.debug(f"Description from meta/selector: {description[:100] if description else ''}...")

    canonical = soup.select_one("link[rel='canonical']")
    product_url = canonical["href"] if canonical and canonical.get("href") else None
    logger.info(f"Product URL: {product_url}")

    logger.info("=== Product details extraction complete ===")
    
    # Validation: Ensure all fields belong to the same product
    logger.info("=== Validation Check ===")
    logger.info(f"Product Name: {_clean_text(product_name)}")
    logger.info(f"Product Price: {current_price}")
    logger.info(f"Product Rating: {rating}")
    logger.info(f"Total Ratings: {total_ratings}")
    logger.info(f"Product Image: {product_image}")
    logger.info(f"Product URL: {product_url}")
    
    # If product name looks invalid (too short or contains navigation text), retry with query
    if not _looks_like_valid_title(product_name) and query:
        logger.warning(f"Product name '{product_name}' appears invalid, using query: {query}")
        product_name = query
    
    return {
        "product_name": _clean_text(product_name) or (query or "").strip(),
        "current_price": current_price,
        "original_price": original_price,
        "discount_percentage": discount_percentage,
        "rating": rating,
        "total_ratings": total_ratings,
        "total_reviews": total_reviews,
        "product_image": product_image,
        "product_url": product_url,
        "description": description,
        "product_price": _format_inr(current_price),
        "reviews_from_jsonld": merged.get("reviews", []),
    }


def extract_firstcry_product_details(html: str, query: str | None = None) -> dict:
    return extract_product_details(html, query=query)


def extract_firstcry_product_metadata(html: str) -> dict:
    details = extract_firstcry_product_details(html)
    return {
        "product_name": details.get("product_name"),
        "product_image": details.get("product_image"),
        "product_price": details.get("product_price"),
        "product_rating": details.get("rating"),
        "total_ratings": details.get("total_ratings"),
        "total_reviews": details.get("total_reviews"),
        "current_price": details.get("current_price"),
        "original_price": details.get("original_price"),
        "discount_percentage": details.get("discount_percentage"),
        "description": details.get("description"),
        "product_url": details.get("product_url"),
    }


def _dedupe_reviews(reviews: list[dict]) -> list[dict]:
    """Remove duplicate reviews (same text + reviewer) while preserving order."""
    seen: set[tuple] = set()
    unique: list[dict] = []
    for review in reviews:
        key = (
            (review.get("review_text") or "").strip().lower(),
            (review.get("reviewer_name") or "").strip().lower(),
        )
        if not key[0] or key in seen:
            continue
        seen.add(key)
        unique.append(review)
    return unique


def _click_load_more_reviews(driver: webdriver.Chrome) -> bool:
    """Click a 'Load more / View all / Show more reviews' control if present.
    Uses a JS click (avoids 'element click intercepted') and returns True when a
    control was actually clicked so the caller knows more content may have loaded."""
    lower = "translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')"
    xpaths = [
        f"//*[self::a or self::button or self::span or self::div][contains({lower}, 'more review')]",
        f"//*[self::a or self::button or self::span or self::div][contains({lower}, 'load more')]",
        f"//*[self::a or self::button or self::span or self::div][contains({lower}, 'view all review')]",
        f"//*[self::a or self::button or self::span or self::div][contains({lower}, 'show more')]",
        f"//*[self::a or self::button or self::span or self::div][contains({lower}, 'read more review')]",
    ]
    for xp in xpaths:
        try:
            for el in driver.find_elements(By.XPATH, xp):
                try:
                    if el.is_displayed() and el.is_enabled():
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                        driver.execute_script("arguments[0].click();", el)
                        logger.info("Clicked review load-more control: %s", (el.text or "").strip()[:40])
                        time.sleep(0.6)
                        return True
                except Exception:
                    continue
        except Exception:
            continue
    return False


def extract_reviews_from_page(driver: webdriver.Chrome, max_reviews: int, deadline: float | None = None) -> list[dict]:
    """Open the reviews section, then repeatedly scroll + click 'load more' to
    pull *all* available reviews (not just the first page), de-duplicating across
    rounds. Bounded by REVIEW_LOAD_MORE_ROUNDS and the wall-clock `deadline` so it
    can never hang (Issues 5, 7, 8)."""
    try:
        buttons = driver.find_elements(
            By.CSS_SELECTOR,
            "a[href*='review' i], button[id*='review' i], button[class*='review' i], "
            "[data-tab*='review' i], [data-target*='review' i]",
        )
        for button in buttons[:3]:
            try:
                if button.is_displayed() and button.is_enabled():
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", button)
                    driver.execute_script("arguments[0].click();", button)
                    time.sleep(0.6)
                    break
            except Exception:
                continue
    except Exception:
        pass

    _wait_for_any_selector(driver, ["[class*='review' i]", "[id*='review' i]"], timeout=4)

    collected: dict[tuple, dict] = {}
    stagnant_rounds = 0
    for round_index in range(REVIEW_LOAD_MORE_ROUNDS):
        if deadline is not None and time.time() >= deadline:
            logger.info("Review collection stopped: wall-clock deadline reached")
            break

        _scroll_to_bottom(driver, steps=3, pause=0.4)
        clicked = _click_load_more_reviews(driver)

        html = driver.page_source
        jsonld = _extract_product_jsonld(html)
        batch = jsonld.get("reviews") or extract_reviews_from_html(html, max_reviews=max_reviews)

        before = len(collected)
        for review in batch:
            key = (
                (review.get("review_text") or "").strip().lower(),
                (review.get("reviewer_name") or "").strip().lower(),
            )
            if key[0] and key not in collected:
                collected[key] = review
        logger.info("Review round %s: %s total unique reviews collected", round_index + 1, len(collected))

        if len(collected) >= max_reviews:
            break
        # stop once neither scrolling nor a load-more click yields new reviews
        if len(collected) == before:
            stagnant_rounds += 1
            if stagnant_rounds >= 2 or not clicked:
                break
        else:
            stagnant_rounds = 0

    return list(collected.values())[:max_reviews]


# ----------------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------------
def scrape_firstcry_reviews(product_name: str, max_reviews: int = 10, return_metadata: bool = False, headless: bool = True):
    start_time = time.time()
    deadline = start_time + HARD_DEADLINE_SECONDS  # absolute wall-clock cap (Issue 1)
    logger.info(f"=== Starting FirstCry Scraping ===")
    logger.info(f"Query: {product_name}")
    logger.info(f"Max Reviews: {max_reviews}")
    logger.info(f"Hard deadline: {HARD_DEADLINE_SECONDS}s")
    
    meta: dict = {
        "platform": "firstcry",
        "search_url": "",
        "product_url": "",
        "html_length": 0,
        "blocked": False,
        "success": False,
        "message": "",
        "review_blocks_detected": 0,
        "extracted_reviews_count": 0,
        "elapsed_seconds": 0,
        "retry_count": 0,
        "product_name": None,
        "product_image": None,
        "current_price": None,
        "rating": None,
        "total_ratings": None,
    }
    reviews: list[dict] = []
    query = (product_name or "").strip()
    search_url = f"{BASE_URL}/search?q={quote(query)}"
    meta["search_url"] = search_url

    driver: webdriver.Chrome | None = None
    last_error = None
    
    try:
        for attempt in range(MAX_RETRIES):
            if time.time() >= deadline:
                logger.warning("Hard deadline reached before attempt %s; stopping retries", attempt + 1)
                meta["message"] = meta.get("message") or "Scraping stopped: time budget exceeded."
                break
            meta["retry_count"] = attempt
            logger.info(f"=== Scraping attempt {attempt + 1}/{MAX_RETRIES} for query: {query} ===")
            
# 1) get product link — use Selenium first for robust search-page
            #    parsing, then fall back to plain requests if Selenium is unavailable.
            product_link, matched_title = None, None
            product_candidates: list[tuple[str, str]] = []
            if driver is None:
                logger.info("Building Selenium driver for search page")
                driver = _build_driver(headless=headless)
            if driver is not None:
                logger.info("STEP: Search page opened -> %s", search_url)
                try:
                    driver.get(search_url)
                    _wait_body(driver)
                    _wait_for_page_ready(driver, PAGE_TIMEOUT_SECONDS)
                    # Explicitly wait for product cards to render instead of a
                    # fixed short timeout, so the very first (cold) load succeeds.
                    cards_ready = _wait_for_product_cards(driver, SEARCH_RESULTS_TIMEOUT)
                    logger.info("STEP: Search results loaded (product cards present=%s)", cards_ready)
                    html = driver.page_source
                    meta["html_length"] = len(html)
                    if _looks_like_blocked_page(html):
                        meta["blocked"] = True
                        meta["message"] = "FirstCry search page looked blocked (captcha/robot check)."
                        logger.warning("Search page appears blocked via Selenium")
                        if attempt < MAX_RETRIES - 1:
                            logger.info("Retrying search after brief pause...")
                            time.sleep(1)
                            continue
                        return {"reviews": [], "meta": meta} if return_metadata else []
                    search_soup = BeautifulSoup(html, "html.parser")
                    product_candidates = _rank_product_candidates(search_soup, query)
                    if product_candidates:
                        matched_title, product_link = product_candidates[0]
                    logger.info(
                        "STEP: Search completed -> %s keyword-matching candidate(s); top=%r",
                        len(product_candidates),
                        matched_title,
                    )
                except Exception as exc:
                    logger.info(f"Selenium search-page fetch failed: {exc}")

            if not product_link:
                try:
                    logger.info(f"Fetching search page via requests: {search_url}")
                    resp = requests.get(search_url, headers=HEADERS, timeout=8)
                    search_soup = BeautifulSoup(resp.text, "html.parser")
                    meta["html_length"] = len(resp.text)
                    if _looks_like_blocked_page(resp.text):
                        meta["blocked"] = True
                        logger.warning("Search page appears blocked (captcha/robot check)")
                    if not product_candidates:
                        product_candidates = _rank_product_candidates(search_soup, query)
                    if product_candidates and not product_link:
                        matched_title, product_link = product_candidates[0]
                except Exception as exc:
                    logger.info(f"requests-based search fetch failed: {exc}")

            if not product_link and driver is None:
                meta["message"] = "Could not start Chrome driver."
                logger.error("Failed to build Chrome driver")
                return {"reviews": [], "meta": meta} if return_metadata else []

            if not product_link:
                meta["message"] = "Could not find a matching product link on the search results page."
                logger.error("No product link found on search results page")
                if attempt < MAX_RETRIES - 1:
                    logger.info("Retrying search (results may not have finished rendering)...")
                    time.sleep(1)
                    continue
                return {"reviews": [], "meta": meta} if return_metadata else []

            meta["product_url"] = product_link
            logger.info("STEP: Product selected -> %s", product_link)

            # 3) load the product-detail page with selenium (it's JS-rendered on
            #    firstcry — plain requests returns an empty shell for this page)
            if driver is None:
                logger.info("Building new Selenium driver for product page")
                driver = _build_driver(headless=headless)
                if driver is None:
                    meta["message"] = "Could not start Chrome driver for product page."
                    logger.error("Failed to build Chrome driver for product page")
                    return {"reviews": [], "meta": meta} if return_metadata else []

            logger.info("STEP: Loading product page -> %s", product_link)
            try:
                driver.get(product_link)
            except TimeoutException:
                logger.warning("Product page load hit page-load timeout (eager); continuing with current DOM")
            _wait_body(driver)
            _wait_for_page_ready(driver, PAGE_TIMEOUT_SECONDS)
            content_ready = _wait_for_product_content(driver, PRODUCT_CONTENT_TIMEOUT)
            logger.info("STEP: Product page loaded (dynamic content ready=%s)", content_ready)

            product_html = driver.page_source
            meta["html_length"] = len(product_html)
            if _looks_like_blocked_page(product_html):
                meta["blocked"] = True
                meta["message"] = "FirstCry product page looked blocked (captcha/robot check)."
                logger.warning("Product page appears blocked")
                if attempt < MAX_RETRIES - 1:
                    logger.info("Retrying product page after brief pause...")
                    time.sleep(1)
                    continue
                return {"reviews": [], "meta": meta} if return_metadata else []

            # --- Extract with DOM validation + retry (no partial N/A) --------
            # Re-locate and re-extract until the mandatory fields are present or
            # the bounded retry budget / deadline is reached. This recovers from
            # AJAX/lazy-loaded content that isn't in the DOM on the first read.
            details: dict = {}
            for extract_round in range(EXTRACTION_RETRY_ROUNDS):
                product_html = driver.page_source
                meta["html_length"] = len(product_html)
                details = extract_product_details(product_html, query=query)

                # Product name resolution: the search-card title is tied to the
                # exact product we chose (never a neighbour); the detail page's
                # own title is preferred only when valid AND more complete.
                extracted_name = details.get("product_name")
                detail_name_is_real = (
                    _looks_like_valid_title(extracted_name)
                    and _clean_text(extracted_name).lower() != query.lower()
                )
                if matched_title and _looks_like_valid_title(matched_title):
                    if (not detail_name_is_real) or len(matched_title) >= len(extracted_name or ""):
                        details["product_name"] = matched_title

                if _has_mandatory_fields(details, product_link):
                    logger.info("STEP: Mandatory fields validated on extraction round %s", extract_round + 1)
                    break

                logger.info(
                    "Mandatory fields incomplete (round %s/%s): name=%r image=%s price=%s - waiting for lazy content...",
                    extract_round + 1,
                    EXTRACTION_RETRY_ROUNDS,
                    details.get("product_name"),
                    bool(details.get("product_image")),
                    details.get("current_price"),
                )
                if time.time() >= deadline:
                    break
                # nudge lazy-loading (images/price often load on scroll) then wait
                _scroll_to_bottom(driver, steps=2, pause=0.4)
                _wait_for_any_selector(driver, ["[class*='price' i]", "h1", "img[src]"], timeout=4)

            # --- Product-page validation (never scrape the wrong product) -----
            # The opened product's title must STILL match the search keyword. If
            # not, open the next keyword-matching candidate instead.
            if product_candidates and not _title_matches_query(details.get("product_name"), query):
                logger.warning(
                    "Opened product %r does NOT match keyword %r - trying next matching candidate",
                    details.get("product_name"),
                    query,
                )
                for alt_title, alt_url in product_candidates[1:MAX_PRODUCT_CANDIDATES]:
                    if time.time() >= deadline:
                        break
                    logger.info("Trying next matching product: %r -> %s", alt_title, alt_url)
                    try:
                        driver.get(alt_url)
                    except TimeoutException:
                        logger.warning("Next-candidate page load timed out (eager); continuing")
                    _wait_body(driver)
                    _wait_for_page_ready(driver, PAGE_TIMEOUT_SECONDS)
                    _wait_for_product_content(driver, PRODUCT_CONTENT_TIMEOUT)
                    alt_details = extract_product_details(driver.page_source, query=query)
                    if alt_title and _looks_like_valid_title(alt_title):
                        alt_details["product_name"] = alt_title
                    if _title_matches_query(alt_details.get("product_name"), query):
                        details = alt_details
                        product_link = alt_url
                        matched_title = alt_title
                        meta["product_url"] = product_link
                        logger.info("STEP: Switched to matching product -> %r (%s)", alt_title, alt_url)
                        break
                    logger.info("Skipped %r: still not a keyword match", alt_details.get("product_name"))

            validated_match = _title_matches_query(details.get("product_name"), query)
            logger.info(
                "STEP: Product page validation -> title=%r matches keyword %r ? %s",
                details.get("product_name"),
                query,
                validated_match,
            )
            meta["title_matches_keyword"] = validated_match

            mandatory_ok = _has_mandatory_fields(details, product_link)
            # Do NOT declare success on partial data: reload the whole page for a
            # fresh attempt if mandatory fields are still missing and we have
            # budget. Only after the final attempt do we accept whatever the page
            # genuinely exposes (real N/A, not a loading race).
            if not mandatory_ok:
                missing = [
                    field
                    for field, present in (
                        ("product_name", bool(details.get("product_name") and _looks_like_valid_title(details.get("product_name")))),
                        ("product_image", bool(details.get("product_image"))),
                        ("current_price", details.get("current_price") is not None),
                    )
                    if not present
                ]
                logger.warning("Mandatory fields still missing after extraction retries: %s", missing)
                if attempt < MAX_RETRIES - 1 and time.time() < deadline:
                    logger.info("Reloading product page for a fresh attempt (avoiding partial N/A)...")
                    time.sleep(1)
                    continue
                logger.info("Final attempt: proceeding with fields the page genuinely exposes: missing=%s", missing)

            meta.update({k: v for k, v in details.items() if k != "reviews_from_jsonld" and v not in (None, "")})
            logger.info("STEP: Title extracted -> %r", details.get("product_name"))
            logger.info("STEP: Image extracted -> %s", details.get("product_image"))
            logger.info("STEP: Price extracted -> current=%s, original=%s, discount=%s", details.get("current_price"), details.get("original_price"), details.get("discount_percentage"))
            logger.info("STEP: Rating extracted -> %s", details.get("rating"))
            logger.info("STEP: Review count extracted -> reviews=%s, ratings=%s", details.get("total_reviews"), details.get("total_ratings"))

            # Update meta with extracted product details
            meta["product_name"] = details.get("product_name")
            meta["product_image"] = details.get("product_image")
            meta["current_price"] = details.get("current_price")
            meta["rating"] = details.get("rating")
            meta["total_ratings"] = details.get("total_ratings")
            meta["mandatory_fields_complete"] = mandatory_ok

            # 4) reviews: JSON-LD first (already inside `details`), then live-page
            #    scan that loads *all* available reviews within the time budget.
            reviews = list(details.get("reviews_from_jsonld") or [])
            logger.info(f"Found {len(reviews)} reviews from JSON-LD")
            if len(reviews) < max_reviews and time.time() < deadline:
                logger.info(f"Extracting additional reviews from page (need {max_reviews - len(reviews)} more)...")
                page_reviews = extract_reviews_from_page(driver, max_reviews - len(reviews), deadline=deadline)
                logger.info(f"Extracted {len(page_reviews)} additional reviews from page")
                reviews.extend(page_reviews)
            # De-duplicate the merged JSON-LD + live-page reviews (Issue 8).
            reviews = _dedupe_reviews(reviews)
            logger.info(f"Total unique reviews after merge/dedupe: {len(reviews)}")

            # If the page never exposed an aggregate rating (no JSON-LD, no
            # microdata, no "X out of 5" text), estimate one from the sample of
            # reviews we did manage to pull, and say so clearly - this is NOT
            # the same as the site's real aggregate rating.
            if not meta.get("rating") and reviews:
                sample_ratings = [r["rating"] for r in reviews if r.get("rating")]
                if sample_ratings:
                    meta["rating"] = round(sum(sample_ratings) / len(sample_ratings), 1)
                    meta["rating_source"] = "estimated_from_sample_reviews"
                    logger.info(f"Estimated rating from sample reviews (page exposed no aggregate): {meta['rating']}")

            logger.info("STEP: Reviews extracted -> %s", len(reviews))
            meta["review_blocks_detected"] = len(reviews)
            meta["extracted_reviews_count"] = len(reviews)

            # Success is validated against the real product, never assumed: we
            # must at least have a valid name plus a price or image (a real
            # product), otherwise this was a failed/partial load.
            has_core_product = bool(
                details.get("product_name")
                and _looks_like_valid_title(details.get("product_name"))
                and (details.get("current_price") is not None or details.get("product_image"))
            )
            meta["success"] = has_core_product
            if not has_core_product:
                meta["message"] = "Could not extract core product details (name/price/image) from the page."
                logger.warning("Attempt %s produced no core product data", attempt + 1)
                if attempt < MAX_RETRIES - 1 and time.time() < deadline:
                    time.sleep(1)
                    continue
            else:
                meta["message"] = (
                    "Scraping completed successfully."
                    if reviews
                    else "Product details were found, but no reviews were extracted."
                )
            logger.info(
                "STEP: Analysis completed on attempt %s (success=%s, mandatory_complete=%s)",
                attempt + 1,
                meta["success"],
                meta.get("mandatory_fields_complete"),
            )
            return {"reviews": reviews[:max_reviews], "meta": meta} if return_metadata else reviews[:max_reviews]

        # All retries exhausted
        logger.error(f"All {MAX_RETRIES} retry attempts exhausted. Last error: {last_error}")
        meta["message"] = f"Failed after {MAX_RETRIES} attempts. Last error: {last_error}"
        return {"reviews": reviews[:max_reviews], "meta": meta} if return_metadata else reviews[:max_reviews]

    except (TimeoutException, WebDriverException) as exc:
        last_error = exc
        meta["message"] = f"Selenium error: {exc}"
        logger.error(f"Selenium error: {exc}")
        return {"reviews": reviews[:max_reviews], "meta": meta} if return_metadata else reviews[:max_reviews]
    except Exception as exc:
        last_error = exc
        logger.exception(f"Unexpected scraping failure")
        meta["message"] = f"Unexpected error: {exc}"
        return {"reviews": reviews[:max_reviews], "meta": meta} if return_metadata else reviews[:max_reviews]
    finally:
        meta["elapsed_seconds"] = round(time.time() - start_time, 1)
        if driver:
            try:
                logger.info("Quitting Selenium driver")
                driver.quit()
            except Exception:
                pass


def PRODUCT_LINK_TOKENS_AS_CSS() -> list[str]:
    return [f"a[href*='{token}' i]" for token in PRODUCT_LINK_TOKENS]


if __name__ == "__main__":
    result = scrape_firstcry_reviews("baby shampoo", max_reviews=5, return_metadata=True, headless=True)
    print(json.dumps(result, indent=2, ensure_ascii=False))