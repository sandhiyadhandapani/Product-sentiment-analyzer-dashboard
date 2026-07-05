from __future__ import annotations

import logging
import os
import re
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

PAGE_TIMEOUT_SECONDS = 20
ELEMENT_TIMEOUT_SECONDS = 15
MAX_PAGES = 2

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
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("prefs", {"profile.default_content_setting_values.images": 2})
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


def _wait_for_page(driver: webdriver.Chrome, selector: str | None = None) -> None:
    if selector:
        WebDriverWait(driver, ELEMENT_TIMEOUT_SECONDS).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
    else:
        WebDriverWait(driver, ELEMENT_TIMEOUT_SECONDS).until(EC.presence_of_element_located((By.TAG_NAME, "body")))


def _get_text_from_elements(elements) -> str:
    if not elements:
        return ""
    text = " ".join(element.get_text(" ", strip=True) for element in elements if element.get_text(" ", strip=True))
    return " ".join(text.split())


def _clean_review_text(raw_text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (raw_text or "")).strip()
    return cleaned if len(cleaned) >= 10 else ""


def _normalize_rating(raw_value: str | int | float | None) -> int:
    if raw_value is None:
        return 0
    if isinstance(raw_value, (int, float)):
        return int(round(float(raw_value)))

    text = str(raw_value)
    match = re.search(r"(\d(?:\.\d)?)", text)
    if not match:
        return 0
    rating = float(match.group(1))
    if rating > 5:
        rating = round(rating / 10, 1)
    return int(round(rating))


def _looks_like_blocked_page(soup: BeautifulSoup) -> bool:
    text = " ".join(soup.stripped_strings).lower()
    blocked_markers = ["captcha", "verify you are human", "robot", "access denied", "try again later"]
    return any(marker in text for marker in blocked_markers)


def _looks_like_valid_product_title(text: str | None) -> bool:
    if not text:
        return False
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return False
    lowered = cleaned.lower()
    if len(cleaned) < 3 or any(token in lowered for token in ["search results", "results", "firstcry", "logo", "sign in", "signin", "cart"]):
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


def _extract_firstcry_card_metadata(soup: BeautifulSoup) -> dict:
    cards = soup.select(".product-card, .product-item, [class*='product']")
    for card in cards:
        title = None
        for selector in ["h2 a", "h3 a", "a[title]", "a"]:
            for element in card.select(selector):
                text = element.get_text(" ", strip=True)
                if _looks_like_valid_product_title(text):
                    title = re.sub(r"\s+", " ", text).strip()
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
                text = element.get_text(" ", strip=True)
                if text:
                    price = text
                    break

        rating = None
        for selector in [".rating", "[class*='rating']", "[class*='star']"]:
            element = card.select_one(selector)
            if element:
                text = element.get_text(" ", strip=True)
                match = re.search(r"(\d+(?:\.\d+)?)", text)
                if match:
                    rating_value = float(match.group(1))
                    if rating_value > 5:
                        rating_value = round(rating_value / 10, 1)
                    rating = rating_value
                    break

        return {
            "product_name": title,
            "product_image": image,
            "product_price": price,
            "product_rating": rating,
        }

    return {}


def extract_firstcry_product_metadata(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    card_metadata = _extract_firstcry_card_metadata(soup)

    product_name = card_metadata.get("product_name")
    product_image = card_metadata.get("product_image")
    product_price = card_metadata.get("product_price")
    product_rating = card_metadata.get("product_rating")

    if not product_name:
        for selector in ["h1", "meta[property='og:title']"]:
            element = soup.select_one(selector)
            if element:
                value = element.get("content") if element.name == "meta" else element.get_text(" ", strip=True)
                if _looks_like_valid_product_title(value):
                    product_name = re.sub(r"\s+", " ", value).strip()
                    break

    if not product_image:
        for selector in ["meta[property='og:image']", "img[src]"]:
            element = soup.select_one(selector)
            if element:
                value = element.get("content") if element.name == "meta" else element.get("src")
                normalized = _normalize_image_url(value)
                if normalized:
                    product_image = normalized
                    break

    if not product_price:
        for selector in [".price", "span.price", "div.price", "[class*='price']"]:
            element = soup.select_one(selector)
            if element:
                value = element.get_text(" ", strip=True)
                if value:
                    product_price = value
                    break

    if product_rating is None:
        for selector in [".rating", "[class*='rating']", "[class*='star']"]:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(" ", strip=True)
                match = re.search(r"(\d+(?:\.\d+)?)", text)
                if match:
                    product_rating = float(match.group(1))
                    break

    total_ratings = None
    for selector in [".review-count", "span[class*='rating']", "[class*='review']"]:
        element = soup.select_one(selector)
        if element:
            text = element.get_text(" ", strip=True)
            match = re.search(r"(\d[\d,]*)", text.replace(",", ""))
            if match:
                total_ratings = int(match.group(1))
                break

    return {
        "product_name": product_name,
        "product_image": product_image,
        "product_price": product_price,
        "product_rating": product_rating,
        "total_ratings": total_ratings,
    }


def _extract_firstcry_review_text(card) -> str:
    selectors = [".review-text", "div[class*='review']", "p", "span"]
    for selector in selectors:
        text = _get_text_from_elements(card.select(selector))
        if text and len(text) > 20:
            return _clean_review_text(text)
    return ""


def _extract_firstcry_review_rating(card) -> int:
    selectors = [".rating", "[class*='rating']", "span"]
    for selector in selectors:
        text = _get_text_from_elements(card.select(selector))
        rating = _normalize_rating(text)
        if rating:
            return rating
    return 0


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
    }
    driver: webdriver.Chrome | None = None

    try:
        driver = _build_driver(visible=True)
        if driver is None:
            meta.update({"blocked": True, "message": "No real reviews found or scraping blocked"})
            return {"reviews": [], "meta": meta} if return_metadata else []

        driver.set_page_load_timeout(PAGE_TIMEOUT_SECONDS)
        driver.set_script_timeout(PAGE_TIMEOUT_SECONDS)

        search_query = (product_name or "").strip()
        search_url = f"https://www.firstcry.com/search?q={quote(search_query)}"
        meta["search_url"] = search_url
        driver.get(search_url)
        _wait_for_page(driver)
        meta["page_title"] = driver.title
        meta["html_length"] = len(driver.page_source)

        metadata = extract_firstcry_product_metadata(driver.page_source)
        meta.update({k: v for k, v in metadata.items() if v is not None})

        soup = BeautifulSoup(driver.page_source, "html.parser")
        if _looks_like_blocked_page(soup):
            meta.update({"blocked": True, "message": "No real reviews found or scraping blocked"})
            return {"reviews": [], "meta": meta} if return_metadata else []

        product_link = None
        for selector in ["a[href*='/p/']", "a[href*='/product/']", ".product-card a"]:
            try:
                element = WebDriverWait(driver, ELEMENT_TIMEOUT_SECONDS).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                href = element.get_attribute("href") or ""
                if href:
                    product_link = href
                    break
            except Exception:
                continue

        if product_link:
            if not product_link.startswith("http"):
                product_link = f"https://www.firstcry.com{product_link}"
            meta["product_url"] = product_link
            driver.get(product_link)
            _wait_for_page(driver, "body")
            meta["page_title"] = driver.title
            meta["html_length"] = len(driver.page_source)

        for _ in range(MAX_PAGES):
            soup = BeautifulSoup(driver.page_source, "html.parser")
            if _looks_like_blocked_page(soup):
                meta.update({"blocked": True, "message": "No real reviews found or scraping blocked"})
                return {"reviews": [], "meta": meta} if return_metadata else []

            review_cards = soup.select(".review-card, .review-item, [class*='review']")
            meta["review_blocks_detected"] = len(review_cards)

            for card in review_cards[:max_reviews]:
                review_text = _extract_firstcry_review_text(card)
                rating = _extract_firstcry_review_rating(card)
                if review_text:
                    reviews.append({"review_text": review_text, "rating": rating or 0, "platform": "firstcry"})

            meta["extracted_reviews_count"] = len(reviews)
            if reviews:
                break

            next_page = None
            for link in soup.select("a[href]"):
                href = link.get("href") or ""
                if "page" in href.lower() and "review" in href.lower():
                    next_page = href
                    break

            if not next_page:
                break

            if not next_page.startswith("http"):
                next_page = f"https://www.firstcry.com{next_page}"
            driver.get(next_page)
            _wait_for_page(driver, "body")
            meta["page_title"] = driver.title
            meta["html_length"] = len(driver.page_source)
    except (TimeoutException, WebDriverException, Exception) as exc:
        logger.warning("FirstCry scraping failed: %s", exc)
        meta.update({"blocked": True, "message": "No real reviews found or scraping blocked"})
        return {"reviews": [], "meta": meta} if return_metadata else []
    finally:
        if driver:
            driver.quit()

    if not reviews:
        meta.update({"blocked": True, "message": "No real reviews found or scraping blocked"})

    return {"reviews": reviews[:max_reviews], "meta": meta} if return_metadata else reviews[:max_reviews]


if __name__ == "__main__":
    reviews = scrape_firstcry_reviews("iphone 15")
    print("Count:", len(reviews))
    print(reviews[:3])
