from scraper.firstcry_scraper import scrape_firstcry_reviews

if __name__ == '__main__':
    result = scrape_firstcry_reviews('baby stroller', max_reviews=5, return_metadata=True)
    print(result)
