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
        logger.warning("Flipkart driver setup failed: %s", exc)
        try:
            return webdriver.Chrome(options=chrome_options)
        except Exception as fallback_exc:
            logger.warning("Flipkart driver fallback failed: %s", fallback_exc)
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
    if len(cleaned) < 3 or any(token in lowered for token in ["search results", "results", "amazon", "flipkart", "logo", "sign in", "signin", "cart"]):
        return False
    return True


def _looks_like_flipkart_price(text: str | None) -> bool:
    if not text:
        return False
    cleaned = re.sub(r"\s+", "", text).strip()
    return bool(re.fullmatch(r"[₹Rs.]*[0-9,]+(?:\.\d+)?", cleaned)) or bool(re.fullmatch(r"[₹Rs.]+[0-9,]+(?:\.\d+)?", cleaned))


def _looks_like_flipkart_rating(text: str | None) -> bool:
    if not text:
        return False
    cleaned = re.sub(r"\s+", " ", text).strip()
    return bool(re.fullmatch(r"\d+(?:\.\d+)?\s*(?:★|stars?|star|out of 5)?", cleaned, flags=re.IGNORECASE))


def _normalize_image_url(raw_value: str | None, base_url: str = "https://www.flipkart.com") -> str | None:
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
    if any(marker in lowered for marker in ["amazon_logo", "flipkart-logo", "logo", "sprite", "icon", "static"]) and "product" not in lowered:
        return None
    return value if lowered.startswith(("http://", "https://")) else None


def _extract_flipkart_card_metadata(soup: BeautifulSoup) -> dict:
    cards = soup.select("div._1AtVbE, div._2kHMtA, div._4ddWXP, div._13oc-S, div[data-id]")
    for card in cards:
        title = None
        for selector in ["a[title]", "a.VJA3rP[title]", "a[href*='/p/']", "a"]:
            element = card.select_one(selector)
            if not element:
                continue
            title_value = element.get("title") or element.get_text(" ", strip=True)
            if _looks_like_valid_product_title(title_value):
                title = re.sub(r"\s+", " ", title_value).strip()
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
        for selector in ["._30jeq3._16Jk6d", ".\_30jeq3", "div[class*='30jeq3']", "._30jeq3", "div[class*='price']", "span[class*='price']"]:
            element = card.select_one(selector)
            if element:
                text = element.get_text(" ", strip=True)
                if _looks_like_flipkart_price(text):
                    price = text
                    break

        rating = None
        for selector in ["._3LWZlK", "div[class*='_3LWZlK']", "div[class*='LWZlK']", "span[class*='LWZlK']"]:
            element = card.select_one(selector)
            if element:
                text = element.get_text(" ", strip=True)
                if _looks_like_flipkart_rating(text):
                    rating = float(re.search(r"(\d+(?:\.\d+)?)", text).group(1))
                    break

        return {
            "product_name": title,
            "product_image": image,
            "product_price": price,
            "product_rating": rating,
        }

    return {}


def extract_flipkart_product_metadata(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    card_metadata = _extract_flipkart_card_metadata(soup)

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
        for selector in ["._30jeq3._16Jk6d", ".\_30jeq3", "div[class*='30jeq3']", "._30jeq3"]:
            element = soup.select_one(selector)
            if element:
                value = element.get_text(" ", strip=True)
                if value:
                    product_price = value
                    break

    if product_rating is None:
        for selector in ["._3LWZlK", "div[class*='_3LWZlK']"]:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(" ", strip=True)
                match = re.search(r"(\d+(?:\.\d+)?)", text)
                if match:
                    product_rating = float(match.group(1))
                    break

    total_ratings = None
    for selector in ["._2_R_DZ", "span[class*='Ratings']", "div[class*='Ratings']"]:
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


def _extract_flipkart_review_text(card) -> str:
    selectors = ["div.t-ZTKy", "div._6K-7Co", "div._3LWZlK", "div._27M-vq", "div._3UAT2v", "div[class*='review']", "p", "span"]
    for selector in selectors:
        text = _get_text_from_elements(card.select(selector))
        if text and len(text) > 20:
            return _clean_review_text(text)
    return ""


def _extract_flipkart_review_rating(card) -> int:
    selectors = ["div._3LWZlK", "div._1AtVbE", "span"]
    for selector in selectors:
        text = _get_text_from_elements(card.select(selector))
        rating = _normalize_rating(text)
        if rating:
            return rating
    return 0


def scrape_flipkart_reviews(product_name: str, max_reviews: int = 10, return_metadata: bool = False) -> list[dict] | dict:
    reviews: list[dict] = []
    meta: dict[str, object] = {
        "platform": "flipkart",
        "scraper": "scrape_flipkart_reviews",
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
        print(f"[Flipkart] product search query: {search_query}")
        search_url = f"https://www.flipkart.com/search?q={quote(search_query)}"
        meta["search_url"] = search_url
        print(f"[Flipkart] search URL: {search_url}")
        driver.get(search_url)
        _wait_for_page(driver)
        meta["page_title"] = driver.title
        meta["html_length"] = len(driver.page_source)

        metadata = extract_flipkart_product_metadata(driver.page_source)
        meta.update({k: v for k, v in metadata.items() if v is not None})

        try:
            popup_close = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "button._2KpZ6l._2doB4z")))
            popup_close.click()
        except Exception:
            pass

        soup = BeautifulSoup(driver.page_source, "html.parser")
        if _looks_like_blocked_page(soup):
            meta.update({"blocked": True, "message": "No real reviews found or scraping blocked"})
            return {"reviews": [], "meta": meta} if return_metadata else []

        product_link = None
        for selector in ["a.CGtC98", "a.VJA3rP", "a[href*='/p/']"]:
            try:
                element = WebDriverWait(driver, ELEMENT_TIMEOUT_SECONDS).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                href = element.get_attribute("href") or ""
                if href and "/p/" in href:
                    product_link = href
                    break
            except Exception:
                continue

        if product_link:
            if not product_link.startswith("http"):
                product_link = f"https://www.flipkart.com{product_link}"
            meta["product_url"] = product_link
            print(f"[Flipkart] product page URL: {product_link}")
            driver.get(product_link)
            _wait_for_page(driver, "body")
            meta["page_title"] = driver.title
            meta["html_length"] = len(driver.page_source)

        review_link = None
        for selector in ["span", "a[href*='product-reviews']"]:
            try:
                for element in driver.find_elements(By.CSS_SELECTOR, selector):
                    text = (element.text or "").strip().lower()
                    href = element.get_attribute("href") or ""
                    if "all reviews" in text or "product-reviews" in href.lower():
                        review_link = href or review_link
                        break
                if review_link:
                    break
            except Exception:
                continue

        if review_link:
            if not review_link.startswith("http"):
                review_link = f"https://www.flipkart.com{review_link}"
            meta["review_url"] = review_link
            print(f"[Flipkart] review page URL: {review_link}")
            driver.get(review_link)
            _wait_for_page(driver, "body")
            meta["page_title"] = driver.title
            meta["html_length"] = len(driver.page_source)

        for _ in range(MAX_PAGES):
            soup = BeautifulSoup(driver.page_source, "html.parser")
            if _looks_like_blocked_page(soup):
                meta.update({"blocked": True, "message": "No real reviews found or scraping blocked"})
                return {"reviews": [], "meta": meta} if return_metadata else []

            review_cards = soup.select("div.col.EPCmJX") or soup.select("div._27M-vq") or soup.select("div[class*='review']")
            meta["review_blocks_detected"] = len(review_cards)
            print(f"[Flipkart] review blocks detected: {len(review_cards)}")

            for card in review_cards[:max_reviews]:
                review_text = _extract_flipkart_review_text(card)
                rating = _extract_flipkart_review_rating(card)
                if review_text:
                    reviews.append({"review_text": review_text, "rating": rating or 0, "platform": "flipkart"})

            meta["extracted_reviews_count"] = len(reviews)
            print(f"[Flipkart] real reviews extracted: {len(reviews)}")
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
                next_page = f"https://www.flipkart.com{next_page}"
            driver.get(next_page)
            _wait_for_page(driver, "body")
            meta["page_title"] = driver.title
            meta["html_length"] = len(driver.page_source)
    except (TimeoutException, WebDriverException, Exception) as exc:
        logger.warning("Flipkart scraping failed: %s", exc)
        meta.update({"blocked": True, "message": "No real reviews found or scraping blocked"})
        return {"reviews": [], "meta": meta} if return_metadata else []
    finally:
        if driver:
            driver.quit()

    if not reviews:
        meta.update({"blocked": True, "message": "No real reviews found or scraping blocked"})

    return {"reviews": reviews[:max_reviews], "meta": meta} if return_metadata else reviews[:max_reviews]


if __name__ == "__main__":
    reviews = scrape_flipkart_reviews("iphone 15")
    print("Count:", len(reviews))
    print(reviews[:3])
