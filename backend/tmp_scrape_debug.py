from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re


def build_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.page_load_strategy = 'eager'
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

for site, url in [
    ('firstcry', 'https://www.firstcry.com/search?q=iphone+15'),
]:
    print('SITE', site)
    driver = build_driver()
    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        print('title', driver.title)
        html = driver.page_source
        print('len', len(html))
        soup = BeautifulSoup(html, 'html.parser')
        print('contains review?', 'review' in html.lower())
        print('contains product-reviews?', 'product-reviews' in html.lower())
        for marker in ['review', 'reviews', 'rating', 'captcha', 'verify']:
            if marker in html.lower():
                print('marker', marker, 'found')
        if site == 'firstcry':
            for selector in ['div[data-hook="review"]', 'span[data-hook="review-body"]', 'a[data-hook="see-all-reviews-link-foot"]', 'a[href*="product-reviews"]']:
                try:
                    elem = driver.find_element(By.CSS_SELECTOR, selector)
                    print('selector found', selector, '->', elem.get_attribute('href') or elem.text[:80])
                except Exception as exc:
                    print('selector missing', selector, exc)
        else:
            for selector in ['a[href*="/p/"]', 'a.CGtC98', 'a.VJA3rP', 'span', 'div[class*="review"]']:
                try:
                    elems = driver.find_elements(By.CSS_SELECTOR, selector)
                    print('selector count', selector, len(elems))
                    for e in elems[:5]:
                        txt = (e.text or '').strip().replace('\n',' ')
                        if txt:
                            print(' ', txt[:160])
                            break
                except Exception as exc:
                    print('selector error', selector, exc)
    finally:
        driver.quit()
