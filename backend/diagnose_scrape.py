"""Standalone scraper diagnostic - shows EXACTLY where a FirstCry search fails.

Run it from the backend folder:

    cd backend
    python diagnose_scrape.py "baby powder"

It prints every stage, and writes the raw search-results HTML to
`search_dump.html` so the real product-card selectors can be confirmed.
Nothing here touches the API/DB/frontend - it only calls the scraper.
"""
from __future__ import annotations

import logging
import sys
import time
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from bs4 import BeautifulSoup  # noqa: E402

from scraper.firstcry_scraper import (  # noqa: E402
    BASE_URL,
    PRODUCT_LINK_TOKENS,
    _PRODUCT_URL_ID_RE,
    _build_driver,
    _clean_text,
    _looks_like_valid_title,
    _rank_product_candidates,
    _title_matches_query,
    scrape_firstcry_reviews,
)


def _line(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def main() -> None:
    query = sys.argv[1] if len(sys.argv) > 1 else "baby powder"

    _line(f"1) FULL SCRAPE for: {query!r}")
    result = scrape_firstcry_reviews(query, max_reviews=5, return_metadata=True, headless=True)
    meta = result.get("meta", {})
    for key in (
        "success", "blocked", "message", "search_url", "product_url",
        "product_name", "product_image", "current_price", "rating",
        "total_ratings", "total_reviews", "html_length", "retry_count",
        "elapsed_seconds", "mandatory_fields_complete", "title_matches_keyword",
    ):
        print(f"  {key:24}: {meta.get(key)}")
    print(f"  reviews extracted        : {len(result.get('reviews', []))}")

    _line("2) DIRECT SEARCH-PAGE INSPECTION")
    driver = _build_driver(headless=True)
    if driver is None:
        print("  !! Chrome driver could NOT be built. Selenium/Chrome is the problem.")
        print("     -> install/repair Chrome, or `pip install --upgrade selenium webdriver-manager`")
        return

    search_url = f"{BASE_URL}/search?q={quote(query)}"
    print(f"  opening: {search_url}")
    try:
        driver.get(search_url)
    except Exception as exc:
        print(f"  !! driver.get failed: {exc}")
        driver.quit()
        return

    time.sleep(7)  # give JS time to render results
    html = driver.page_source
    try:
        with open("search_dump.html", "w", encoding="utf-8") as handle:
            handle.write(html)
        print("  raw search HTML saved to: search_dump.html")
    except Exception as exc:
        print(f"  (could not save HTML: {exc})")

    print(f"  search HTML length       : {len(html)}")
    lowered = html.lower()
    for marker in ("captcha", "verify you are human", "access denied", "are you a robot"):
        if marker in lowered:
            print(f"  !! BLOCK MARKER FOUND     : {marker!r}  (FirstCry is blocking the bot)")

    soup = BeautifulSoup(html, "html.parser")
    anchors = soup.select("a[href]")
    print(f"  total <a href> on page   : {len(anchors)}")

    raw_products = []
    for anchor in anchors:
        href = (anchor.get("href") or "").strip()
        text = _clean_text(anchor.get("title") or anchor.get_text(" ", strip=True))
        if not href:
            continue
        is_product = any(t in href.lower() for t in PRODUCT_LINK_TOKENS) or bool(_PRODUCT_URL_ID_RE.search(href))
        if is_product:
            raw_products.append((text, href))
    print(f"  product-looking links    : {len(raw_products)}")
    print("  --- first 15 product links (title | valid? | keyword-match?) ---")
    for text, href in raw_products[:15]:
        print(f"    {text[:55]!r:57} | valid={_looks_like_valid_title(text)} | match={_title_matches_query(text, query)}")

    matches = _rank_product_candidates(soup, query)
    print(f"\n  KEYWORD-MATCHING candidates: {len(matches)}")
    for title, url in matches[:5]:
        print(f"    - {title}")

    driver.quit()

    _line("CONCLUSION")
    if not raw_products:
        print("  No product links in the HTML -> results didn't render (JS/block/timeout)")
        print("  Share search_dump.html so the real card selector can be added.")
    elif not matches:
        print("  Product links exist but NONE matched the keyword -> matcher too strict OR")
        print("  titles live in a child element (anchor text empty). Check the list above.")
    else:
        print("  Matches found -> selection is OK; failure is later (product page load).")


if __name__ == "__main__":
    main()
