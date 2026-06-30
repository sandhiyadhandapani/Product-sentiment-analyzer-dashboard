import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth


# ──────────────────────────────────────────────
#  DRIVER SETUP
# ──────────────────────────────────────────────

def create_driver():
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)

    stealth(
        driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    return driver


def random_delay(min_sec=1.5, max_sec=3.5):
    time.sleep(random.uniform(min_sec, max_sec))


# ──────────────────────────────────────────────
#  AMAZON SCRAPER
# ──────────────────────────────────────────────

def scrape_amazon(product_name, max_reviews=20):
    driver = create_driver()
    results = {
        "source": "Amazon",
        "product_name": product_name,
        "product_info": {},
        "reviews": []
    }

    try:
        # Step 1: Search product
        driver.get("https://www.amazon.in")
        random_delay()

        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "twotabsearchtextbox"))
        )
        search_box.clear()
        search_box.send_keys(product_name)
        search_box.send_keys(Keys.RETURN)
        random_delay()

        # Step 2: Click first product
        first_product = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-component-type='s-search-result'] h2 a"))
        )
        first_product.click()
        random_delay()

        # Step 3: Get product info
        try:
            title = driver.find_element(By.ID, "productTitle").text.strip()
        except:
            title = product_name

        try:
            rating = driver.find_element(By.CSS_SELECTOR, "span.a-icon-alt").text.strip()
        except:
            rating = "N/A"

        try:
            num_ratings = driver.find_element(By.ID, "acrCustomerReviewText").text.strip()
        except:
            num_ratings = "N/A"

        try:
            price = driver.find_element(By.CSS_SELECTOR, "span.a-price-whole").text.strip()
            price = "₹" + price
        except:
            price = "N/A"

        results["product_info"] = {
            "title": title,
            "overall_rating": rating,
            "total_ratings": num_ratings,
            "price": price
        }

        # Step 4: Go to reviews page
        try:
            see_all = driver.find_element(By.CSS_SELECTOR, "a[data-hook='see-all-reviews-link-foot']")
            see_all.click()
            random_delay()
        except:
            pass

        # Step 5: Scrape reviews (paginated)
        page = 1
        while len(results["reviews"]) < max_reviews:
            review_blocks = driver.find_elements(By.CSS_SELECTOR, "div[data-hook='review']")

            for block in review_blocks:
                if len(results["reviews"]) >= max_reviews:
                    break
                try:
                    review_title = block.find_element(By.CSS_SELECTOR, "a[data-hook='review-title'] span").text.strip()
                except:
                    review_title = "N/A"

                try:
                    review_rating = block.find_element(By.CSS_SELECTOR, "i[data-hook='review-star-rating'] span").text.strip()
                except:
                    review_rating = "N/A"

                try:
                    review_body = block.find_element(By.CSS_SELECTOR, "span[data-hook='review-body'] span").text.strip()
                except:
                    review_body = "N/A"

                try:
                    review_date = block.find_element(By.CSS_SELECTOR, "span[data-hook='review-date']").text.strip()
                except:
                    review_date = "N/A"

                results["reviews"].append({
                    "title": review_title,
                    "rating": review_rating,
                    "body": review_body,
                    "date": review_date
                })

            # Next page
            try:
                next_btn = driver.find_element(By.CSS_SELECTOR, "li.a-last a")
                next_btn.click()
                random_delay()
                page += 1
            except:
                break  # No more pages

    except Exception as e:
        results["error"] = str(e)

    finally:
        driver.quit()

    return results


# ──────────────────────────────────────────────
#  FLIPKART SCRAPER
# ──────────────────────────────────────────────

def scrape_flipkart(product_name, max_reviews=20):
    driver = create_driver()
    results = {
        "source": "Flipkart",
        "product_name": product_name,
        "product_info": {},
        "reviews": []
    }

    try:
        # Step 1: Search product
        driver.get("https://www.flipkart.com")
        random_delay()

        # Close login popup if appears
        try:
            close_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button._2KpZ6l._2doB4z"))
            )
            close_btn.click()
        except:
            pass

        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "q"))
        )
        search_box.clear()
        search_box.send_keys(product_name)
        search_box.send_keys(Keys.RETURN)
        random_delay()

        # Step 2: Click first product
        first_product = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div._1AtVbE a"))
        )
        first_product.click()
        random_delay()

        # Switch to new tab if opened
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[1])
            random_delay()

        # Step 3: Get product info
        try:
            title = driver.find_element(By.CSS_SELECTOR, "span.B_NuCI").text.strip()
        except:
            title = product_name

        try:
            rating = driver.find_element(By.CSS_SELECTOR, "div._3LWZlK").text.strip()
        except:
            rating = "N/A"

        try:
            num_ratings = driver.find_element(By.CSS_SELECTOR, "span._2_R_DZ span").text.strip()
        except:
            num_ratings = "N/A"

        try:
            price = driver.find_element(By.CSS_SELECTOR, "div._30jeq3").text.strip()
        except:
            price = "N/A"

        results["product_info"] = {
            "title": title,
            "overall_rating": rating,
            "total_ratings": num_ratings,
            "price": price
        }

        # Step 4: Go to all reviews
        try:
            all_reviews_btn = driver.find_element(By.CSS_SELECTOR, "div._3UAT2v a")
            all_reviews_btn.click()
            random_delay()
        except:
            pass

        # Step 5: Scrape reviews (paginated)
        while len(results["reviews"]) < max_reviews:
            review_blocks = driver.find_elements(By.CSS_SELECTOR, "div._1BSgM9")

            for block in review_blocks:
                if len(results["reviews"]) >= max_reviews:
                    break
                try:
                    review_rating = block.find_element(By.CSS_SELECTOR, "div._3LWZlK").text.strip()
                except:
                    review_rating = "N/A"

                try:
                    review_title = block.find_element(By.CSS_SELECTOR, "p._2-N8zT").text.strip()
                except:
                    review_title = "N/A"

                try:
                    review_body = block.find_element(By.CSS_SELECTOR, "div.t-ZTKy div div").text.strip()
                except:
                    review_body = "N/A"

                try:
                    review_date = block.find_element(By.CSS_SELECTOR, "p._2sc7ZR").text.strip()
                except:
                    review_date = "N/A"

                results["reviews"].append({
                    "title": review_title,
                    "rating": review_rating,
                    "body": review_body,
                    "date": review_date
                })

            # Next page
            try:
                next_btn = driver.find_element(By.CSS_SELECTOR, "a._1LKTO3[class*='_3paLqX']")
                next_btn.click()
                random_delay()
            except:
                break

    except Exception as e:
        results["error"] = str(e)

    finally:
        driver.quit()

    return results


# ──────────────────────────────────────────────
#  MAIN SCRAPE FUNCTION (called by Flask)
# ──────────────────────────────────────────────

def scrape_product(product_name, source="both", max_reviews=20):
    """
    Called by Flask API.
    source: 'amazon', 'flipkart', or 'both'
    Returns a dict with scraped data.
    """
    data = {}

    if source in ("amazon", "both"):
        print(f"[Scraper] Scraping Amazon for: {product_name}")
        data["amazon"] = scrape_amazon(product_name, max_reviews)

    if source in ("flipkart", "both"):
        print(f"[Scraper] Scraping Flipkart for: {product_name}")
        data["flipkart"] = scrape_flipkart(product_name, max_reviews)

    return data


# ──────────────────────────────────────────────
#  TEST (run directly)
# ──────────────────────────────────────────────

if __name__ == "__main__":
    product = input("Enter product name to test: ")
    result = scrape_product(product, source="both", max_reviews=5)

    for source, data in result.items():
        print(f"\n{'='*40}")
        print(f"Source: {source.upper()}")
        print(f"Product Info: {data.get('product_info')}")
        print(f"Total Reviews Scraped: {len(data.get('reviews', []))}")
        for i, r in enumerate(data.get("reviews", []), 1):
            print(f"\nReview {i}:")
            print(f"  Title : {r['title']}")
            print(f"  Rating: {r['rating']}")
            print(f"  Date  : {r['date']}")
            print(f"  Body  : {r['body'][:100]}...")