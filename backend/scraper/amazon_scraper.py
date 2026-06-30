from __future__ import annotations

import logging
from urllib.parse import quote

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
ELEMENT_TIMEOUT_SECONDS = 10
MAX_PAGES = 2

logger = logging.getLogger(__name__)


def _build_driver() -> webdriver.Chrome | None:
    chrome_options = Options()
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
        logger.warning("Amazon driver setup failed: %s", exc)
        try:
            return webdriver.Chrome(options=chrome_options)
        except Exception as fallback_exc:
            logger.warning("Amazon driver fallback failed: %s", fallback_exc)
            return None


def _wait_for_page(driver: webdriver.Chrome) -> None:
    WebDriverWait(driver, ELEMENT_TIMEOUT_SECONDS).until(EC.presence_of_element_located((By.TAG_NAME, "body")))


def _get_text_from_elements(elements) -> str:
    if not elements:
        return ""
    text = " ".join(element.get_text(" ", strip=True) for element in elements if element.get_text(" ", strip=True))
    return " ".join(text.split())


def _extract_amazon_review_text(card) -> str:
    selectors = [
        "span[data-hook='review-body']",
        "span.review-text-content",
        "div.review-text",
        "div.a-expander-content",
        "p",
    ]
    for selector in selectors:
        text = _get_text_from_elements(card.select(selector))
        if text and len(text) > 20:
            return text

    fallback_text = _get_text_from_elements([card])
    return fallback_text if fallback_text and len(fallback_text) > 20 else ""


def _extract_amazon_review_rating(card) -> str:
    selectors = [
        "i[data-hook='review-star-rating']",
        "span.a-icon-alt",
        "span[data-hook='review-star-rating']",
    ]
    for selector in selectors:
        text = _get_text_from_elements(card.select(selector))
        if text:
            return text
    return ""


def scrape_amazon_reviews(product_name: str, max_reviews: int = 10) -> list[dict]:
    reviews: list[dict] = []
    driver: webdriver.Chrome | None = None

    try:
        driver = _build_driver()
        if driver is None:
            return []

        driver.set_page_load_timeout(PAGE_TIMEOUT_SECONDS)
        driver.set_script_timeout(PAGE_TIMEOUT_SECONDS)

        search_url = f"https://www.amazon.in/s?k={quote(product_name)}"
        print(f"[Amazon] search URL: {search_url}")
        try:
            driver.get(search_url)
            _wait_for_page(driver)
        except (TimeoutException, Exception):
            return []

        soup = BeautifulSoup(driver.page_source, "html.parser")
        product_links = [
            link.get("href")
            for link in soup.select("a[href]")
            if link.get("href") and ("/dp/" in link.get("href") or "/gp/product/" in link.get("href"))
        ]

        product_url = None
        if product_links:
            first_link = product_links[0]
            if not first_link.startswith("http"):
                first_link = f"https://www.amazon.in{first_link}"
            product_url = first_link
            print(f"[Amazon] product URL: {product_url}")
            try:
                driver.get(product_url)
                _wait_for_page(driver)
            except Exception:
                return []

        if not product_url:
            return []

        review_link = None
        candidates = [
            element.get_attribute("href") or ""
            for element in driver.find_elements(By.TAG_NAME, "a")
            if (element.get_attribute("href") or "").strip()
        ]
        for href in candidates:
            if "product-reviews" in href or "customer-reviews" in href or "/review/" in href:
                review_link = href
                break

        if review_link:
            if not review_link.startswith("http"):
                review_link = f"https://www.amazon.in{review_link}"
            print(f"[Amazon] review page URL: {review_link}")
            try:
                driver.get(review_link)
                _wait_for_page(driver)
            except (TimeoutException, WebDriverException, Exception):
                pass

        for _ in range(MAX_PAGES):
            soup = BeautifulSoup(driver.page_source, "html.parser")
            review_cards = (
                soup.select("div[data-hook='review']")
                or soup.select("div.review")
                or soup.select("div.a-section.review")
                or soup.select("div.a-row.review")
            )
            print(f"[Amazon] review elements found: {len(review_cards)}")

            for card in review_cards[:max_reviews]:
                review_text = _extract_amazon_review_text(card)
                rating_text = _extract_amazon_review_rating(card)
                if review_text:
                    reviews.append({"review": review_text, "rating": rating_text or "5 stars"})
                if len(reviews) >= max_reviews:
                    break

            if len(reviews) >= max_reviews:
                break

            next_page = None
            for link in soup.select("a[href]"):
                href = link.get("href") or ""
                if "pageNumber" in href and "review" in href:
                    next_page = href
                    break

            if not next_page:
                break

            if not next_page.startswith("http"):
                next_page = f"https://www.amazon.in{next_page}"
            try:
                driver.get(next_page)
                _wait_for_page(driver)
            except Exception:
                break
    except Exception as exc:
        logger.warning("Amazon scraping failed: %s", exc)
        return []
    finally:
        if driver:
            driver.quit()

    return reviews[:max_reviews]
