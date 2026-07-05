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

PAGE_TIMEOUT_SECONDS = 25
ELEMENT_TIMEOUT_SECONDS = 15
MAX_PAGES = 3
MAX_RETRIES = 2

logger = logging.getLogger(__name__)


def _build_driver(visible: bool = True) -> webdriver.Chrome | None:
    chrome_options = Options()
    if not visible or os.getenv("SELENIUM_HEADLESS") == "1":
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-translate")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.images": 2,
        "profile.default_content_setting_values.stylesheets": 2,
        "profile.default_content_setting_values.fonts": 2,
        "profile.default_content_setting_values.notifications": 2,
    })
    chrome_options.page_load_strategy = "eager"

    try:
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    except Exception as exc:
        logger.warning("FirstCry driver setup failed: %s", exc)
        try:
            return webdriver.Chrome(options=chrome_options)
        except Exception as fallback_exc:
            logger.warning("FirstCry driver fallback failed: %s", fallback_exc)
            return None


def _wait_for_page(driver: webdriver.Chrome, selector: str | None = None, timeout: int = ELEMENT_TIMEOUT_SECONDS) -> None:
    if not hasattr(driver, "find_element"):
        return
    if selector:
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
    else:
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.TAG_NAME, "body")))


def _get_text_from_elements(elements) -> str:
    if not elements:
        return ""
    parts = [element.get_text(" ", strip=True) for element in elements if element.get_text(" ", strip=True)]
    return " ".join(" ".join(parts).split())


def _clean_text(raw_value: str | None) -> str:
    cleaned = re.sub(r"\s+", " ", (raw_value or "")).strip()
    return cleaned if len(cleaned) >= 2 else ""


def _normalize_rating(raw_value: str | int | float | None) -> float:
    if raw_value is None:
        return 0.0
    if isinstance(raw_value, (int, float)):
        return round(float(raw_value), 1)

    text = str(raw_value)
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return 0.0

    rating = float(match.group(1))
    if rating > 5:
        rating = round(rating / 10, 1)
    return round(rating, 1)


def _normalize_price(raw_value: str | int | float | None) -> int | float | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, (int, float)):
        return float(raw_value)

    text = str(raw_value)
    match = re.search(r"(\d[\d,\.]*)", text)
    if not match:
        return None

    candidate = match.group(1)
    digits = re.sub(r"[^0-9.]", "", candidate).replace(",", "")
    if not digits:
        return None
    return float(digits)


def _normalize_discount(raw_value: str | int | float | None) -> int | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, (int, float)):
        return int(round(float(raw_value)))

    text = str(raw_value)
    match = re.search(r"(\d{1,3})", text.replace("%", ""))
    if not match:
        return None
    return int(match.group(1))


def _looks_like_blocked_page(soup: BeautifulSoup) -> bool:
    text = " ".join(soup.stripped_strings).lower()
    blocked_markers = ["captcha", "verify you are human", "robot", "access denied", "try again later", "temporarily unavailable"]
    return any(marker in text for marker in blocked_markers)


def _looks_like_valid_product_title(text: str | None) -> bool:
    if not text:
        return False
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return False
    lowered = cleaned.lower()
    if len(cleaned) < 3 or any(token in lowered for token in ["search results", "results", "firstcry", "logo", "sign in", "signin", "cart", "home"]):
        return False
    return True


def _normalize_image_url(raw_value: str | None, base_url: str = "https://www.firstcry.com") -> str | None:
    if not raw_value:
        return None
    value = str(raw_value).strip()
    if not value or value.startswith("data:image"):
        return None
    if value.startswith("//"):
        value = f"https:{value}"
    elif value.startswith("/"):
        value = urljoin(base_url, value)
    lowered = value.lower()
    if any(marker in lowered for marker in ["logo", "sprite", "icon", "static"]) and "product" not in lowered:
        return None
    return value if lowered.startswith(("http://", "https://")) else None


def _format_inr(value: float | int | None) -> str | None:
    if value is None:
        return None
    digits = int(float(value))
    if digits < 1000:
        return f"₹{digits}"

    value_str = str(digits)
    if len(value_str) > 3:
        last_three = value_str[-3:]
        rest = value_str[:-3]
        if len(rest) > 2:
            mid = rest[-2:]
            front = rest[:-2]
            return f"₹{front},{mid},{last_three}"
        return f"₹{rest},{last_three}"
    return f"₹{value_str}"


def _score_title_match(title: str | None, query: str) -> int:
    if not title:
        return 0
    title_tokens = set(re.findall(r"[a-z0-9]+", title.lower()))
    query_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    if not query_tokens:
        return 0
    return len(title_tokens & query_tokens)


def _extract_text_from_candidates(soup: BeautifulSoup, selectors: list[str]) -> str:
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            text = _clean_text(element.get_text(" ", strip=True))
            if text:
                return text
    return ""


def _extract_firstcry_card_metadata(soup: BeautifulSoup) -> dict:
    cards = soup.select(".product-card, .product-item, [class*='product']")
    for card in cards:
        title = None
        for selector in ["h2 a", "h3 a", "a[title]", "a"]:
            for element in card.select(selector):
                text = _clean_text(element.get_text(" ", strip=True))
                if _looks_like_valid_product_title(text):
                    title = text
                    break
            if title:
                break

        if not title:
            continue

        image = None
        for element in card.select("img[src], img[data-src], img[data-image]"):
            raw_value = element.get("src") or element.get("data-src") or element.get("data-image")
            normalized = _normalize_image_url(raw_value)
            if normalized:
                image = normalized
                break

        price = None
        for selector in [".price", "span.price", "div.price", "[class*='price']"]:
            element = card.select_one(selector)
            if element:
                text = _clean_text(element.get_text(" ", strip=True))
                if text:
                    price = text
                    break

        rating = None
        for selector in [".rating", "[class*='rating']", "[class*='star']"]:
            element = card.select_one(selector)
            if element:
                text = _clean_text(element.get_text(" ", strip=True))
                rating_value = _normalize_rating(text)
                if rating_value:
                    rating = rating_value
                    break

        return {
            "product_name": title,
            "product_image": image,
            "product_price": price,
            "product_rating": rating,
        }

    return {}


def extract_firstcry_product_details(html: str, query: str | None = None) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    card_metadata = _extract_firstcry_card_metadata(soup)

    product_name = card_metadata.get("product_name") or _extract_text_from_candidates(
        soup,
        ["meta[property='og:title']", "h1", "h2", "[class*='product-name']"],
    )
    if not _looks_like_valid_product_title(product_name):
        product_name = None

    product_image = None
    for selector in ["meta[property='og:image']", "img[src]", "img[data-src]", "img[data-image]"]:
        for element in soup.select(selector):
            value = element.get("content") if element.name == "meta" else element.get("src") or element.get("data-src") or element.get("data-image")
            normalized = _normalize_image_url(value)
            if normalized:
                product_image = normalized
                break
        if product_image:
            break

    current_price = None
    original_price = None
    price_elements = soup.select(".price, .current-price, .offer-price, .final-price, .mrp, .original-price, [class*='price']")
    for element in price_elements:
        text = _clean_text(element.get_text(" ", strip=True))
        if not text:
            continue
        lower_text = text.lower()
        if any(marker in lower_text for marker in ["rating", "review", "ratings", "reviews"]):
            continue

        if any(marker in lower_text for marker in ["mrp", "original", "strike"]):
            price_value = _normalize_price(text)
            if price_value is not None and original_price is None:
                original_price = float(price_value)
            continue

        price_value = _normalize_price(text)
        if price_value is None:
            continue
        if current_price is None:
            current_price = float(price_value)
            break

    if current_price is None and price_elements:
        for element in price_elements:
            text = _clean_text(element.get_text(" ", strip=True))
            price_value = _normalize_price(text)
            if price_value is not None:
                current_price = price_value
                break

    if original_price is None and current_price is not None:
        fallback_price = None
        for element in price_elements:
            text = _clean_text(element.get_text(" ", strip=True))
            if text and text.lower().startswith("₹"):
                price_value = _normalize_price(text)
                if price_value is not None and price_value != current_price:
                    fallback_price = price_value
                    break
        if fallback_price is not None:
            original_price = fallback_price

    rating = None
    for selector in [".rating", "[class*='rating']", "[class*='star']"]:
        element = soup.select_one(selector)
        if element:
            rating_value = _normalize_rating(element.get_text(" ", strip=True))
            if rating_value:
                rating = rating_value
                break

    total_ratings = None
    for selector in [".rating-count", "[class*='rating-count']", ".ratings", "[class*='ratings']", ".review-count", "[class*='review-count']"]:
        element = soup.select_one(selector)
        if element:
            text = _clean_text(element.get_text(" ", strip=True))
            match = re.search(r"(\d[\d,]*)", text.replace(",", ""))
            if match:
                total_ratings = int(match.group(1))
                break

    total_reviews = None
    for selector in [".review-count", "[class*='review-count']", ".reviews", "[class*='reviews']", ".customer-reviews", "[class*='customer-reviews']"]:
        element = soup.select_one(selector)
        if element:
            text = _clean_text(element.get_text(" ", strip=True))
            match = re.search(r"(\d[\d,]*)", text.replace(",", ""))
            if match:
                total_reviews = int(match.group(1))
                break

    description = _extract_text_from_candidates(
        soup,
        ["meta[name='description']", "meta[property='og:description']", ".product-description", "[class*='description']"],
    )
    if not description:
        description = _clean_text(_extract_text_from_candidates(soup, ["p"]))

    discount_percentage = None
    for selector in [".discount", "[class*='discount']", ".off", "[class*='off']"]:
        element = soup.select_one(selector)
        if element:
            discount_value = _normalize_discount(element.get_text(" ", strip=True))
            if discount_value is not None:
                discount_percentage = discount_value
                break

    if discount_percentage is None and current_price is not None and original_price is not None and original_price > current_price:
        discount_percentage = int(round(((original_price - current_price) / original_price) * 100))

    product_url = None
    for selector in ["meta[property='og:url']", "link[rel='canonical']", "a[href*='/p/']", "a[href*='/product/']"]:
        element = soup.select_one(selector)
        if element:
            value = element.get("content") if element.name == "meta" else element.get("href")
            if value:
                if value.startswith("/"):
                    value = urljoin("https://www.firstcry.com", value)
                product_url = value
                break

    if not product_name and query:
        product_name = query.strip()

    normalized_product_name = _clean_text(product_name)
    if not normalized_product_name and query:
        normalized_product_name = query.strip()

    return {
        "product_name": normalized_product_name,
        "current_price": current_price,
        "original_price": original_price,
        "discount_percentage": discount_percentage,
        "rating": rating,
        "total_ratings": total_ratings,
        "total_reviews": total_reviews,
        "product_image": product_image,
        "product_url": product_url,
        "description": _clean_text(description),
        "product_price": _format_inr(current_price),
    }


def extract_firstcry_product_metadata(html: str) -> dict:
    details = extract_firstcry_product_details(html)
    product_price = details.get("product_price")
    if product_price is None and details.get("current_price") is not None:
        product_price = _format_inr(details['current_price'])
    return {
        "product_name": details.get("product_name"),
        "product_image": details.get("product_image"),
        "product_price": product_price,
        "product_rating": details.get("rating"),
        "total_ratings": details.get("total_ratings"),
        "current_price": details.get("current_price"),
        "original_price": details.get("original_price"),
        "discount_percentage": details.get("discount_percentage"),
        "description": details.get("description"),
        "product_url": details.get("product_url"),
    }


def _extract_reviewer_name(card: BeautifulSoup) -> str:
    for selector in [".reviewer-name", ".user-name", ".author", "[class*='name']", "span"]:
        element = card.select_one(selector)
        if element:
            text = _clean_text(element.get_text(" ", strip=True))
            if text and len(text) < 80:
                return text
    return ""


def _extract_review_date(card: BeautifulSoup) -> str:
    for selector in [".review-date", ".date", ".posted-on", "[class*='date']"]:
        element = card.select_one(selector)
        if element:
            text = _clean_text(element.get_text(" ", strip=True))
            if text:
                return text
    return ""


def _extract_firstcry_review_text(card: BeautifulSoup) -> str:
    selectors = [".review-text", ".comment", ".review-content", "p", "span"]
    for selector in selectors:
        text = _get_text_from_elements(card.select(selector))
        if text and len(text) > 8:
            return _clean_text(text)
    return ""


def _extract_firstcry_review_rating(card: BeautifulSoup) -> int:
    for selector in [".review-rating", ".rating", "[class*='rating']", "span"]:
        text = _get_text_from_elements(card.select(selector))
        rating = _normalize_rating(text)
        if rating:
            return int(rating)
    return 0


def _safe_json_loads(value: str) -> dict | list | None:
    try:
        return json.loads(value)
    except Exception:
        try:
            cleaned = re.sub(r"^\s*window\.[^=]+=", "", value)
            cleaned = re.sub(r";\s*$", "", cleaned)
            return json.loads(cleaned)
        except Exception:
            return None


def _walk_for_review_objects(node: object) -> list[dict]:
    reviews: list[dict] = []
    if isinstance(node, dict):
        if "reviewBody" in node and ("author" in node or "reviewer_name" in node or "user" in node):
            reviews.append(node)
        for value in node.values():
            reviews.extend(_walk_for_review_objects(value))
    elif isinstance(node, list):
        for item in node:
            reviews.extend(_walk_for_review_objects(item))
    return reviews


def _extract_reviews_from_json_ld(html: str, max_reviews: int = 10) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    result: list[dict] = []
    for script in soup.select('script[type="application/ld+json"], script[type="application/json"]'):
        payload = _safe_json_loads(script.string or "")
        if not payload:
            continue
        result.extend(_walk_for_review_objects(payload))
        if len(result) >= max_reviews:
            break
    return result[:max_reviews]


def _extract_reviews_from_embedded_json(html: str, max_reviews: int = 10) -> list[dict]:
    result: list[dict] = []
    patterns = [
        r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});",
        r"window\.__PRELOADED_STATE__\s*=\s*(\{.*?\});",
        r"window\.__SSR_DATA__\s*=\s*(\{.*?\});",
        r"window\.__NEXT_DATA__\s*=\s*(\{.*?\});",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, html, re.S):
            payload = _safe_json_loads(match.group(1))
            if not payload:
                continue
            result.extend(_walk_for_review_objects(payload))
            if len(result) >= max_reviews:
                return result[:max_reviews]
    return result[:max_reviews]


def _extract_review_data_from_json(review: dict) -> dict:
    text = review.get("reviewBody") or review.get("review_text") or review.get("text") or review.get("comment") or ""
    author = review.get("author") or review.get("reviewer_name") or review.get("user") or {}
    if isinstance(author, dict):
        reviewer_name = author.get("name") or author.get("author") or author.get("reviewer_name") or ""
    elif isinstance(author, str):
        reviewer_name = author
    else:
        reviewer_name = ""

    rating = review.get("reviewRating", review.get("rating") or review.get("review_rating") or 0)
    if isinstance(rating, dict):
        rating = rating.get("ratingValue") or rating.get("value") or 0
    return {
        "review_text": _clean_text(text),
        "rating": int(_normalize_rating(rating)),
        "review_rating": int(_normalize_rating(rating)),
        "reviewer_name": _clean_text(reviewer_name),
        "review_date": _clean_text(review.get("datePublished") or review.get("reviewDate") or review.get("date") or ""),
        "platform": "firstcry",
    }


def _load_visible_reviews(driver: webdriver.Chrome, max_attempts: int = 6) -> None:
    for attempt in range(max_attempts):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.6)
        try:
            _wait_for_page(driver, ".review-card, .review-item, .review-block, .review-card__content, .review-section, [class*='review']", timeout=5)
            return
        except Exception:
            continue


def _click_review_tab(driver: webdriver.Chrome) -> bool:
    try:
        buttons = driver.find_elements(
            By.CSS_SELECTOR,
            "a[href*='review'], button[id*='review'], button[class*='review'], [data-tab*='review'], [data-target*='review']",
        )
        for button in buttons:
            try:
                if button.is_displayed() and button.is_enabled():
                    button.click()
                    time.sleep(0.6)
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def _select_best_product_link(soup: BeautifulSoup, query: str) -> tuple[str | None, str | None]:
    candidates: list[tuple[int, str, str]] = []
    for anchor in soup.select("a[href]"):
        href = anchor.get("href") or ""
        text = _clean_text(anchor.get_text(" ", strip=True))
        if not href or not text:
            continue
        if any(marker in href.lower() for marker in ["javascript:", "mailto:", "tel:"]):
            continue
        if "/p/" in href.lower() or "/product/" in href.lower() or "/baby" in href.lower():
            score = _score_title_match(text, query)
            if score > 0 or _looks_like_valid_product_title(text):
                candidates.append((score, text, href))

    if not candidates:
        return None, None
    candidates.sort(key=lambda item: item[0], reverse=True)
    href = candidates[0][2]
    return (href if href.startswith("http") else f"https://www.firstcry.com{href}", candidates[0][1])


def _iter_review_pages(driver: webdriver.Chrome, soup: BeautifulSoup, max_pages: int) -> list[BeautifulSoup]:
    pages = [soup]
    current_page = 1
    while current_page < max_pages:
        next_url = None
        for link in soup.select("a[href]"):
            href = (link.get("href") or "").strip()
            if not href or href.startswith("javascript"):
                continue
            lower_href = href.lower()
            if "review" in lower_href or "page" in lower_href or "next" in lower_href:
                next_url = href
                break
        if not next_url:
            break
        if not next_url.startswith("http"):
            next_url = f"https://www.firstcry.com{next_url}"
        try:
            driver.get(next_url)
            _wait_for_page(driver, "body")
            _load_visible_reviews(driver)
            current_page += 1
            soup = BeautifulSoup(driver.page_source, "html.parser")
            pages.append(soup)
        except Exception as exc:  # pragma: no cover - defensive handling
            logger.warning("FirstCry review pagination failed: %s", exc)
            break
    return pages


def _find_product_id_from_html(html: str) -> str | None:
    m = re.search(r"data-product-id\s*=\s*\"?(\d+)\"?", html)
    if m:
        return m.group(1)
    m = re.search(r"productId\"?\s*[:=]\s*\"?(\d+)\"?", html)
    if m:
        return m.group(1)
    m = re.search(r"product_id\"?\s*[:=]\s*\"?(\d+)\"?", html)
    if m:
        return m.group(1)
    return None


def _find_candidate_review_urls(html: str, base_url: str = "https://www.firstcry.com") -> list[str]:
    urls: list[str] = []
    for match in re.finditer(r'(https?://[^"\s]+|/[^\'">\s]+)', html):
        url = match.group(1)
        lower = url.lower()
        if any(token in lower for token in ["review", "rating", "ratings", "comments", "reviews"]):
            if url.startswith("/"):
                url = urljoin(base_url, url)
            if url not in urls:
                urls.append(url)
    return urls


def _fetch_reviews_via_requests(product_url: str | None, html: str, max_reviews: int = 10) -> list[dict]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/javascript, text/html, */*;q=0.01",
    }
    reviews: list[dict] = []
    json_candidates = _extract_reviews_from_json_ld(html, max_reviews=max_reviews)
    if json_candidates:
        for item in json_candidates:
            parsed = _extract_review_data_from_json(item)
            if parsed["review_text"]:
                reviews.append(parsed)
                if len(reviews) >= max_reviews:
                    return reviews[:max_reviews]

    json_candidates = _extract_reviews_from_embedded_json(html, max_reviews=max_reviews)
    if json_candidates:
        for item in json_candidates:
            parsed = _extract_review_data_from_json(item)
            if parsed["review_text"]:
                reviews.append(parsed)
                if len(reviews) >= max_reviews:
                    return reviews[:max_reviews]

    product_id = _find_product_id_from_html(html)
    candidate_urls = []
    if product_id:
        candidate_urls.extend([
            f"https://www.firstcry.com/mweb/v2/product/ratingReviews?productId={product_id}&page=1",
            f"https://www.firstcry.com/api/product/{product_id}/reviews?page=1",
            f"https://www.firstcry.com/product_reviews/{product_id}?page=1",
        ])

    candidate_urls.extend(_find_candidate_review_urls(html))

    tried = set()
    for url in candidate_urls:
        if len(reviews) >= max_reviews:
            break
        if not url or url in tried:
            continue
        tried.add(url)
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            content_type = resp.headers.get("content-type", "")
            text = resp.text
            if "application/json" in content_type or text.strip().startswith("{") or text.strip().startswith("["):
                payload = _safe_json_loads(text)
                if payload:
                    found = _walk_for_review_objects(payload)
                    for item in found:
                        parsed = _extract_review_data_from_json(item)
                        if parsed["review_text"]:
                            reviews.append(parsed)
                            if len(reviews) >= max_reviews:
                                break
            else:
                soup = BeautifulSoup(text, "html.parser")
                for card in soup.select(".review-card, .review-item, .review-block, [class*='review']"):
                    review_text = _extract_firstcry_review_text(card)
                    rating = _extract_firstcry_review_rating(card)
                    reviewer_name = _extract_reviewer_name(card)
                    review_date = _extract_review_date(card)
                    if review_text:
                        reviews.append(
                            {
                                "review_text": review_text,
                                "rating": rating or 0,
                                "review_rating": rating or 0,
                                "reviewer_name": reviewer_name,
                                "review_date": review_date,
                                "platform": "firstcry",
                            }
                        )
                        if len(reviews) >= max_reviews:
                            break
        except Exception:
            continue

    return reviews[:max_reviews]


def scrape_firstcry_reviews(product_name: str, max_reviews: int = 10, return_metadata: bool = False) -> list[dict] | dict:
    reviews: list[dict] = []
    meta: dict[str, object] = {
        "platform": "firstcry",
        "scraper": "scrape_firstcry_reviews",
        "search_url": "",
        "product_url": "",
        "review_url": "",
        "page_title": "",
        "html_length": 0,
        "review_blocks_detected": 0,
        "extracted_reviews_count": 0,
        "blocked": False,
        "message": "",
        "success": False,
    }
    driver: webdriver.Chrome | None = None

    for attempt in range(MAX_RETRIES):
        try:
            # prepare search URL and try a requests-based fetch first (faster, avoids webdriver)
            search_query = (product_name or "").strip()
            search_url = f"https://www.firstcry.com/search?q={quote(search_query)}"
            meta["search_url"] = search_url

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }

            try:
                resp = requests.get(search_url, headers=headers, timeout=10)
                search_html = resp.text
                meta["page_title"] = ""
                meta["html_length"] = len(search_html)
                search_soup = BeautifulSoup(search_html, "html.parser")
                # find product link from search results
                selected_link, selected_name = _select_best_product_link(search_soup, search_query)
                product_link = selected_link or extract_firstcry_product_metadata(search_html).get("product_url")
                if product_link:
                    # fetch product page HTML via requests and attempt JSON/XHR extraction
                    try:
                        prod_resp = requests.get(product_link, headers=headers, timeout=10)
                        prod_html = prod_resp.text
                        meta.update({k: v for k, v in extract_firstcry_product_metadata(prod_html).items() if v is not None})
                        reviews_via_requests = _fetch_reviews_via_requests(product_link, prod_html, max_reviews=max_reviews)
                        if reviews_via_requests:
                            meta["extracted_reviews_count"] = len(reviews_via_requests)
                            meta.update({"blocked": False, "message": "Scraping completed via requests.", "success": True})
                            return {"reviews": reviews_via_requests[:max_reviews], "meta": meta} if return_metadata else reviews_via_requests[:max_reviews]
                    except Exception:
                        pass
            except Exception:
                # if requests fails, fall back to webdriver below
                pass

            driver = _build_driver(visible=True)
            if driver is None:
                raise RuntimeError("Browser driver unavailable")

            driver.set_page_load_timeout(PAGE_TIMEOUT_SECONDS)
            driver.set_script_timeout(PAGE_TIMEOUT_SECONDS)

            driver.get(search_url)
            _wait_for_page(driver)
            meta["page_title"] = driver.title
            meta["html_length"] = len(driver.page_source)

            soup = BeautifulSoup(driver.page_source, "html.parser")
            if _looks_like_blocked_page(soup):
                raise RuntimeError("FirstCry returned a blocked page")

            metadata = extract_firstcry_product_metadata(driver.page_source)
            meta.update({k: v for k, v in metadata.items() if v is not None})

            selected_link, selected_name = _select_best_product_link(soup, search_query)
            product_link = selected_link or metadata.get("product_url")
            if not product_link:
                product_link = None

            if selected_name:
                current_name = meta.get("product_name")
                current_name_text = str(current_name or "")
                if not current_name_text or current_name_text.lower() == search_query.lower() or current_name_text.lower() in selected_name.lower():
                    meta["product_name"] = selected_name
                else:
                    selected_score = _score_title_match(selected_name, search_query)
                    current_score = _score_title_match(current_name_text, search_query)
                    if selected_score > current_score or (selected_score == current_score and len(selected_name) > len(current_name_text)):
                        meta["product_name"] = selected_name

            if product_link:
                meta["product_url"] = product_link
                driver.get(product_link)
                _wait_for_page(driver, "body")
                meta["page_title"] = driver.title
                meta["html_length"] = len(driver.page_source)
                page_details = extract_firstcry_product_details(driver.page_source, query=search_query)
                meta.update({k: v for k, v in page_details.items() if v is not None})
                if selected_name and _looks_like_valid_product_title(selected_name):
                    meta["product_name"] = selected_name
                else:
                    meta["product_name"] = page_details.get("product_name") or meta.get("product_name")
                meta["product_price"] = page_details.get("product_price") or meta.get("product_price")
                meta["product_image"] = page_details.get("product_image") or meta.get("product_image")

            review_pages = [BeautifulSoup(driver.page_source, "html.parser")]
            if product_link:
                if _click_review_tab(driver):
                    meta["page_title"] = driver.title
                    meta["html_length"] = len(driver.page_source)
                _load_visible_reviews(driver)
                review_pages = _iter_review_pages(driver, review_pages[0], max_pages=MAX_PAGES)

            json_reviews = _extract_reviews_from_json_ld(driver.page_source, max_reviews=max_reviews)
            if not json_reviews:
                json_reviews = _extract_reviews_from_embedded_json(driver.page_source, max_reviews=max_reviews)
            if json_reviews:
                meta["json_review_count"] = len(json_reviews)
                for review_item in json_reviews:
                    parsed = _extract_review_data_from_json(review_item)
                    if parsed["review_text"]:
                        reviews.append(parsed)
                        if len(reviews) >= max_reviews:
                            break

            if len(reviews) < max_reviews:
                for page_soup in review_pages:
                    review_cards = page_soup.select(
                        ".review-card, .review-item, .review-block, .review-card__content, .review-section, [class*='review']"
                    )
                    meta["review_blocks_detected"] = max(meta.get("review_blocks_detected", 0), len(review_cards))
                    for card in review_cards:
                        review_text = _extract_firstcry_review_text(card)
                        rating = _extract_firstcry_review_rating(card)
                        reviewer_name = _extract_reviewer_name(card)
                        review_date = _extract_review_date(card)
                        if review_text:
                            reviews.append(
                                {
                                    "review_text": review_text,
                                    "rating": rating or 0,
                                    "review_rating": rating or 0,
                                    "reviewer_name": reviewer_name,
                                    "review_date": review_date,
                                    "platform": "firstcry",
                                }
                            )
                            if len(reviews) >= max_reviews:
                                break
                    if len(reviews) >= max_reviews:
                        break

            if not reviews:
                logger.warning(
                    "FirstCry review extraction failed: no reviews found after HTML parsing and JSON/LD extraction"
                )

            meta["extracted_reviews_count"] = len(reviews)
            if reviews or metadata.get("product_name"):
                meta.update({"blocked": False, "message": "Scraping completed successfully.", "success": True})
                return {"reviews": reviews[:max_reviews], "meta": meta} if return_metadata else reviews[:max_reviews]

            raise RuntimeError("No usable review or product data found")
        except (TimeoutException, WebDriverException, Exception) as exc:
            logger.warning("FirstCry scraping attempt %s failed: %s", attempt + 1, exc)
            if attempt == MAX_RETRIES - 1:
                meta.update({"blocked": True, "message": "No real reviews found or scraping blocked", "success": False})
                break
            time.sleep(1)
        finally:
            if driver:
                driver.quit()
                driver = None

    return {"reviews": reviews[:max_reviews], "meta": meta} if return_metadata else reviews[:max_reviews]


if __name__ == "__main__":
    result = scrape_firstcry_reviews("iphone 15", max_reviews=5, return_metadata=True)
    print(result)
