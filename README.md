# Product-sentiment-analyzer-dashboard

A web-based application for scraping FirstCry product reviews, performing NLP-based sentiment analysis, and visualizing insights through an interactive dashboard.

## What it does
- Scrapes product data and review content from FirstCry
- Analyzes reviews with a lightweight sentiment pipeline
- Displays product-level sentiment summaries and review insights in a React dashboard

## Backend
- FastAPI app in the backend directory
- Main entry point: backend/main.py
- Review analysis logic: backend/sentiment/analyzer.py
- FirstCry scraper: backend/scraper/firstcry_scraper.py

## Frontend
- React app in the frontend directory
- Main pages include search, product details, dashboard, and informational pages

## Run locally
1. Start the backend API from the backend folder
2. Start the frontend from the frontend folder
3. Open the app in your browser and search for a product on FirstCry

