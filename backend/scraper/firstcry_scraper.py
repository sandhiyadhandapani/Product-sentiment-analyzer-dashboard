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
PAGE_TIMEOUT_SECONDS = 15
ELEMENT_TIMEOUT_SECONDS = 8
TOTAL_TIME_BUDGET_SECONDS = 20   # soft budget - we try to stay under this
MAX_RETRIES = 1                 # keep it low so we don't blow the time budget

BASE_URL = "https://www.firstcry.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Real firstcry product-detail URLs look like:
#   /<brand>/<slug>/<numeric-id>/product-detail?sterm=...
PRODUCT_LINK_TOKENS = ("/product-detail", "/p/", "/product/")

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
    return driver


def _wait_body(driver: webdriver.Chrome, timeout: int = ELEMENT_TIMEOUT_SECONDS) -> None:
    try:
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except Exception:
        pass


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
    banned = ["search results", "firstcry", "sign in", "signin", "cart", "wishlist", "my account"]
    return not any(tok in lowered for tok in banned)


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


def _extract_product_jsonld(html: str) -> dict:
    """Look for schema.org Product markup: name, image, offers.price, aggregateRating."""
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.select('script[type="application/ld+json"]'):
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
                "original_price": _normalize_price(offers.get("price") if isinstance(offers.get("price"), (int, float)) else None),
                "rating": _normalize_rating(aggregate.get("ratingValue")) if aggregate else None,
                "total_ratings": int(aggregate["ratingCount"]) if aggregate.get("ratingCount") else None,
                "total_reviews": int(aggregate["reviewCount"]) if aggregate.get("reviewCount") else None,
            }
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
                    "platform": "firstcry",
                })
            result["reviews"] = reviews
            logger.info("Selector succeeded: JSON-LD product data")
            return {k: v for k, v in result.items() if v not in (None, "", [])}
    return {}


def _extract_embedded_json_payload(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script"):
        content = script.string or script.get_text(" ", strip=True) or ""
        if not content:
            continue
        payload = _safe_json_loads(content)
        if not payload:
            continue
        for obj in _iter_json_objects(payload):
            if not isinstance(obj, dict):
                continue
            obj_type = obj.get("@type")
            type_matches = obj_type == "Product" or (isinstance(obj_type, list) and "Product" in obj_type)
            if not type_matches:
                if not any(
                    key in obj
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
                "product_name": _clean_text(obj.get("name") or obj.get("productName") or obj.get("title")),
                "product_image": obj.get("image") if isinstance(obj.get("image"), str) else (obj.get("image") or [None])[0],
                "description": _clean_text(obj.get("description")),
                "current_price": _normalize_price(obj.get("price") or obj.get("current_price") or obj.get("salePrice") or obj.get("sellingPrice")),
                "original_price": _normalize_price(obj.get("originalPrice") or obj.get("original_price") or obj.get("mrp") or obj.get("strikethroughPrice")),
                "discount_percentage": int(obj.get("discountPercentage")) if isinstance(obj.get("discountPercentage"), int) else None,
                "rating": _normalize_rating(obj.get("rating") or obj.get("ratingValue") or obj.get("averageRating") or obj.get("productRating")),
                "total_ratings": int(re.sub(r"[^\d]", "", str(obj.get("ratings") or obj.get("ratingCount") or obj.get("totalRatings") or ""))) if re.search(r"\d", str(obj.get("ratings") or obj.get("ratingCount") or obj.get("totalRatings") or "")) else None,
                "total_reviews": int(re.sub(r"[^\d]", "", str(obj.get("reviews") or obj.get("reviewCount") or obj.get("totalReviews") or ""))) if re.search(r"\d", str(obj.get("reviews") or obj.get("reviewCount") or obj.get("totalReviews") or "")) else None,
            }
            if result.get("product_name") or result.get("current_price") or result.get("rating"):
                logger.info("Selector succeeded: embedded JSON payload")
                return {k: v for k, v in result.items() if v not in (None, "", [])}
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
    text = soup.get_text(" ", strip=True)
    pattern = re.compile(
        r"₹\s?([\d,]+(?:\.\d{1,2})?)\D{0,30}?MRP\D{0,10}?₹\s?([\d,]+(?:\.\d{1,2})?)\D{0,20}?(\d{1,3})\s?%",
        re.I,
    )
    match = pattern.search(text)
    if match:
        current = _normalize_price(match.group(1))
        original = _normalize_price(match.group(2))
        discount = int(match.group(3))
        return current, original, discount

    # fallback order: "MRP ₹2579" ... "₹976" ... "62% off" (MRP mentioned first)
    pattern2 = re.compile(
        r"MRP\D{0,10}?₹\s?([\d,]+(?:\.\d{1,2})?)\D{0,30}?₹\s?([\d,]+(?:\.\d{1,2})?)\D{0,20}?(\d{1,3})\s?%",
        re.I,
    )
    match2 = pattern2.search(text)
    if match2:
        original = _normalize_price(match2.group(1))
        current = _normalize_price(match2.group(2))
        discount = int(match2.group(3))
        return current, original, discount

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
    result: dict = {}

    price_el = soup.select_one("[itemprop='price']")
    if price_el:
        value = price_el.get("content") or price_el.get_text(" ", strip=True)
        price = _normalize_price(value)
        if price:
            result["current_price"] = price

    rating_el = soup.select_one("[itemprop='ratingValue']")
    if rating_el:
        value = rating_el.get("content") or rating_el.get_text(" ", strip=True)
        rating = _normalize_rating(value)
        if rating:
            result["rating"] = rating

    count_el = soup.select_one("[itemprop='reviewCount'], [itemprop='ratingCount']")
    if count_el:
        value = count_el.get("content") or count_el.get_text(" ", strip=True)
        digits = re.sub(r"[^\d]", "", value or "")
        if digits:
            result["total_ratings"] = int(digits)

    return result


def _find_rating_in_text(soup: BeautifulSoup) -> float | None:
    text = soup.get_text(" ", strip=True)
    match = re.search(r"\b([0-5](?:\.\d)?)\s*(?:out of|/)\s*5\b", text, re.I)
    if match:
        return _normalize_rating(match.group(1))
    return None


def _find_review_count_in_text(soup: BeautifulSoup) -> int | None:
    text = soup.get_text(" ", strip=True)
    match = re.search(r"([\d,]+)\s*(?:ratings?|reviews?)\b", text, re.I)
    if match:
        digits = re.sub(r"[^\d]", "", match.group(1))
        return int(digits) if digits else None
    return None


def _looks_like_review_text(text: str) -> bool:
    cleaned = _clean_text(text)
    if not cleaned:
        return False
    lowered = cleaned.lower()
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
    ]
    if any(token in lowered for token in banned) and len(cleaned.split()) <= 6:
        return False
    if any(token in lowered for token in ("button", "placeholder", "label", "heading", "title")):
        return False
    meaningful_words = re.findall(r"[A-Za-z]{2,}", cleaned)
    return len(meaningful_words) >= 5


def _extract_review_text(card) -> str:
    for selector in [
        ".review-text",
        ".review-body",
        ".review-content",
        ".comment",
        ".content",
        ".message",
        ".description",
        ".text",
    ]:
        text_el = card.select_one(selector)
        if text_el:
            text = _clean_text(text_el.get_text(" ", strip=True))
            if text:
                return text
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
                    "platform": "firstcry",
                })
                if len(reviews) >= max_reviews:
                    return reviews

    review_blocks = soup.select(
        "[class*='review' i], [id*='review' i], [class*='rating-review' i], [class*='customer-review' i], article, li"
    )
    for card in review_blocks:
        text = _extract_review_text(card)
        if not _looks_like_review_text(text):
            continue
        rating = 0
        rating_el = card.select_one("[class*='star' i], [class*='rating' i], [data-rating]")
        if rating_el:
            rating = int(_normalize_rating(rating_el.get_text(" ", strip=True)))
        reviewer_el = card.select_one("[class*='reviewer' i], [class*='author' i], [class*='user' i], [class*='name' i]")
        review_date_el = card.select_one("time, [class*='date' i], [class*='posted' i]")
        reviewer_name = _clean_text(reviewer_el.get_text(" ", strip=True)) if reviewer_el else ""
        signature = (text.lower(), reviewer_name.lower(), str(rating))
        if signature in seen:
            continue
        seen.add(signature)
        reviews.append({
            "review_text": text,
            "rating": rating,
            "review_rating": rating,
            "reviewer_name": reviewer_name,
            "review_date": _clean_text(review_date_el.get_text(" ", strip=True)) if review_date_el else "",
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


def _select_best_product_link(soup: BeautifulSoup, query: str) -> tuple[str | None, str | None]:
    candidates: list[tuple[int, str, str]] = []
    seen_hrefs = set()
    for anchor in soup.select("a[href]"):
        href = (anchor.get("href") or "").strip()
        text = _clean_text(anchor.get("title") or anchor.get_text(" ", strip=True))
        if not href or href in seen_hrefs:
            continue
        if not any(token in href.lower() for token in PRODUCT_LINK_TOKENS):
            continue
        if not text or not _looks_like_valid_title(text):
            continue
        seen_hrefs.add(href)
        score = _score_title_match(text, query)
        candidates.append((score, text, href))

    if not candidates:
        return None, None

    candidates.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
    best_score, best_title, best_href = candidates[0]
    full_url = best_href if best_href.startswith("http") else urljoin(BASE_URL, best_href)
    return full_url, best_title


# ----------------------------------------------------------------------------
# Product page extraction (combines JSON-LD -> selectors -> raw text scan)
# ----------------------------------------------------------------------------
def extract_product_details(html: str, query: str | None = None) -> dict:
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

    product_name = (
        merged.get("product_name")
        or jsonld.get("product_name")
        or _clean_text((soup.select_one("meta[property='og:title']") or {}).get("content", "") if soup.select_one("meta[property='og:title']") else "")
        or _clean_text(soup.find("h1").get_text(" ", strip=True)) if soup.find("h1") else ""
    )
    if not _looks_like_valid_title(product_name):
        for selector in [".product-card h2", ".product-card h1", ".product-card a", "[class*='product' i] h2", "[class*='product' i] h1", "h2", "h3"]:
            candidate = soup.select_one(selector)
            if not candidate:
                continue
            text = _clean_text(candidate.get_text(" ", strip=True))
            if _looks_like_valid_title(text):
                product_name = text
                break
    if not _looks_like_valid_title(product_name):
        product_name = (query or "").strip()

    product_image = merged.get("product_image") or jsonld.get("product_image")
    if not product_image:
        for selector in ["meta[property='og:image']", ".product-card img", "img#productImage", "img[alt*='product' i]", "img[src]"]:
            image_el = soup.select_one(selector)
            if not image_el:
                continue
            src = image_el.get("content") or image_el.get("src") or image_el.get("data-src")
            if not src:
                continue
            alt = _clean_text(image_el.get("alt") or "")
            if any(token in alt.lower() for token in ("logo", "icon", "sprite")):
                continue
            if any(token in str(src).lower() for token in ("logo", "icon", "sprite")):
                continue
            product_image = src
            break

    current_price = merged.get("current_price") or microdata.get("current_price")
    original_price = merged.get("original_price") or microdata.get("original_price")
    discount_percentage = merged.get("discount_percentage")

    pattern_current, pattern_original, pattern_discount = _find_price_mrp_discount_pattern(soup)
    if current_price is None and pattern_current is not None:
        current_price = pattern_current
        original_price = pattern_original
        discount_percentage = pattern_discount
        logger.info("Selector succeeded: price regex pattern")
    elif current_price is None:
        logger.info("Selector failed: price regex pattern")

    if current_price is None:
        price_els = soup.select(
            "[class*='selling-price' i], [class*='offer-price' i], [class*='final-price' i], [class*='current-price' i], .price, .finalPrice"
        )
        for el in price_els:
            value = _normalize_price(el.get_text(" ", strip=True))
            if value and value > 10:
                current_price = value
                logger.info("Selector succeeded: price element selector")
                break
        if current_price is None:
            logger.info("Selector failed: price element selector")

    if original_price is None:
        mrp_els = soup.select("[class*='mrp' i], [class*='strike' i], [class*='original-price' i], del, s")
        for el in mrp_els:
            value = _normalize_price(el.get_text(" ", strip=True))
            if value and value > 10 and (current_price is None or value != current_price):
                original_price = value
                logger.info("Selector succeeded: original price element selector")
                break
        if original_price is None:
            logger.info("Selector failed: original price element selector")

    prices_in_text = _find_prices_in_text(soup)
    if current_price is None and prices_in_text:
        current_price = min(prices_in_text)
    if original_price is None and prices_in_text and len(set(prices_in_text)) > 1:
        higher = max(p for p in prices_in_text if current_price is None or p >= current_price)
        if current_price and higher > current_price:
            original_price = higher

    if discount_percentage is None:
        if current_price and original_price and original_price > current_price:
            discount_percentage = int(((original_price - current_price) / original_price) * 100)
        else:
            disc_match = re.search(r"(\d{1,3})\s*%\s*off", soup.get_text(" ", strip=True), re.I)
            if disc_match:
                discount_percentage = int(disc_match.group(1))

    rating = merged.get("rating") or microdata.get("rating") or _find_rating_in_text(soup)
    total_ratings = merged.get("total_ratings") or microdata.get("total_ratings") or _find_review_count_in_text(soup)
    total_reviews = merged.get("total_reviews")

    description = merged.get("description")
    if not description:
        meta_desc = soup.select_one("meta[name='description']")
        description = _clean_text(meta_desc["content"]) if meta_desc and meta_desc.get("content") else ""

    canonical = soup.select_one("link[rel='canonical']")
    product_url = canonical["href"] if canonical and canonical.get("href") else None

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


def extract_reviews_from_page(driver: webdriver.Chrome, max_reviews: int) -> list[dict]:
    """Try clicking a reviews tab, scroll to load lazy content, then extract."""
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
                    button.click()
                    time.sleep(0.8)
                    break
            except Exception:
                continue
    except Exception:
        pass

    _scroll_to_bottom(driver, steps=5, pause=0.5)
    _wait_for_any_selector(driver, ["[class*='review' i]", "[id*='review' i]"], timeout=4)

    html = driver.page_source
    jsonld = _extract_product_jsonld(html)
    if jsonld.get("reviews"):
        return jsonld["reviews"][:max_reviews]

    return extract_reviews_from_html(html, max_reviews=max_reviews)


# ----------------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------------
def scrape_firstcry_reviews(product_name: str, max_reviews: int = 10, return_metadata: bool = False, headless: bool = True):
    start_time = time.time()
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
    }
    reviews: list[dict] = []
    query = (product_name or "").strip()
    search_url = f"{BASE_URL}/search?q={quote(query)}"
    meta["search_url"] = search_url

    driver: webdriver.Chrome | None = None
    try:
        # 1) get product link — try plain requests first (search page is
        #    largely server-rendered on firstcry, so this is fast and cheap)
        product_link, matched_title = None, None
        try:
            resp = requests.get(search_url, headers=HEADERS, timeout=8)
            search_soup = BeautifulSoup(resp.text, "html.parser")
            meta["html_length"] = len(resp.text)
            if _looks_like_blocked_page(resp.text):
                meta["blocked"] = True
            product_link, matched_title = _select_best_product_link(search_soup, query)
            if product_link and matched_title:
                title_score = _score_title_match(matched_title, query)
                if title_score <= 0 and query:
                    product_link, matched_title = None, None
        except Exception as exc:
            logger.info("requests-based search fetch failed: %s", exc)

        # 2) if requests didn't find a link (JS-rendered / blocked), fall back
        #    to selenium for the search page too
        if not product_link:
            driver = _build_driver(headless=headless)
            if driver is None:
                meta["message"] = "Could not start Chrome driver."
                return {"reviews": [], "meta": meta} if return_metadata else []
            driver.get(search_url)
            _wait_body(driver)
            _wait_for_any_selector(driver, PRODUCT_LINK_TOKENS_AS_CSS(), timeout=6)
            html = driver.page_source
            meta["html_length"] = len(html)
            if _looks_like_blocked_page(html):
                meta["blocked"] = True
                meta["message"] = "FirstCry search page looked blocked (captcha/robot check)."
                return {"reviews": [], "meta": meta} if return_metadata else []
            search_soup = BeautifulSoup(html, "html.parser")
            product_link, matched_title = _select_best_product_link(search_soup, query)

        if not product_link:
            meta["message"] = "Could not find a matching product link on the search results page."
            return {"reviews": [], "meta": meta} if return_metadata else []

        meta["product_url"] = product_link

        # 3) load the product-detail page with selenium (it's JS-rendered on
        #    firstcry — plain requests returns an empty shell for this page)
        if driver is None:
            driver = _build_driver(headless=headless)
            if driver is None:
                meta["message"] = "Could not start Chrome driver for product page."
                return {"reviews": [], "meta": meta} if return_metadata else []

        driver.get(product_link)
        _wait_body(driver)
        _wait_for_any_selector(driver, ["[class*='price' i]", "h1", "[class*='rating' i]"], timeout=8)
        product_html = driver.page_source
        meta["html_length"] = len(product_html)

        if _looks_like_blocked_page(product_html):
            meta["blocked"] = True
            meta["message"] = "FirstCry product page looked blocked (captcha/robot check)."
            return {"reviews": [], "meta": meta} if return_metadata else []

        details = extract_product_details(product_html, query=query)
        if matched_title and _looks_like_valid_title(matched_title):
            details["product_name"] = matched_title
        meta.update({k: v for k, v in details.items() if k != "reviews_from_jsonld" and v not in (None, "")})

        # 4) reviews: JSON-LD first (already inside `details`), then live-page scan
        reviews = details.get("reviews_from_jsonld") or []
        if len(reviews) < max_reviews and time.time() - start_time < TOTAL_TIME_BUDGET_SECONDS:
            page_reviews = extract_reviews_from_page(driver, max_reviews - len(reviews))
            reviews.extend(page_reviews)

        # If the page never exposed an aggregate rating (no JSON-LD, no
        # microdata, no "X out of 5" text), estimate one from the sample of
        # reviews we did manage to pull, and say so clearly - this is NOT
        # the same as the site's real aggregate rating.
        if meta.get("rating") is None and reviews:
            sample_ratings = [r["rating"] for r in reviews if r.get("rating")]
            if sample_ratings:
                meta["rating"] = round(sum(sample_ratings) / len(sample_ratings), 1)
                meta["rating_source"] = "estimated_from_sample_reviews"

        meta["review_blocks_detected"] = len(reviews)
        meta["extracted_reviews_count"] = len(reviews)
        meta["success"] = True
        meta["message"] = (
            "Scraping completed successfully."
            if reviews
            else "Product details were found, but no reviews were extracted."
        )
        return {"reviews": reviews[:max_reviews], "meta": meta} if return_metadata else reviews[:max_reviews]

    except (TimeoutException, WebDriverException) as exc:
        meta["message"] = f"Selenium error: {exc}"
        return {"reviews": reviews[:max_reviews], "meta": meta} if return_metadata else reviews[:max_reviews]
    except Exception as exc:
        logger.exception("Unexpected scraping failure")
        meta["message"] = f"Unexpected error: {exc}"
        return {"reviews": reviews[:max_reviews], "meta": meta} if return_metadata else reviews[:max_reviews]
    finally:
        meta["elapsed_seconds"] = round(time.time() - start_time, 1)
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def PRODUCT_LINK_TOKENS_AS_CSS() -> list[str]:
    return [f"a[href*='{token}' i]" for token in PRODUCT_LINK_TOKENS]


if __name__ == "__main__":
    result = scrape_firstcry_reviews("baby shampoo", max_reviews=5, return_metadata=True, headless=True)
    print(json.dumps(result, indent=2, ensure_ascii=False))