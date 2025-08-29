# Aura: Open-Source Brand Intelligence Platform

This repository contains a Streamlit-based web application that aggregates public conversations about a brand and surfaces actionable insights.

## Features
- Phase 1 (MVP):
  - Company validation and selection
  - Harvesters: Google Play reviews and Reddit posts/comments
  - Sentiment analysis using `siebert/sentiment-roberta-large-english`
  - Dashboard with high-level metrics, "What's Working / What's Not Working" themes, and a Source Data Explorer
- Phase 2:
  - Apple App Store reviews (up to 500 most recent per app) with in-UI disclaimer
  - YouTube comments via the YouTube Data API (with daily quota awareness and graceful disable)
  - Google Trends (pytrends) time-series in a Brand Interest section

## Quickstart
1. Create and activate a virtual environment (recommended):
   - macOS/Linux:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     python -m venv .venv
     .venv\\Scripts\\Activate.ps1
     ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables by copying `.env.example` to `.env` and filling values as needed:
   - `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`
   - `YOUTUBE_API_KEY` (Phase 2)
   - Optional: `THECOMPANIESAPI_KEY` or `ABSTRACT_API_KEY` for company validation. If unavailable, a free fallback (Clearbit autocomplete) is used.
4. Run the app:
   ```bash
   streamlit run app/app.py
   ```

## Notes
- The first run will download an ML model, which can take a few minutes.
- SQLite database (`aura.db`) is created in the project root.
- Apple App Store integration relies on public JSON RSS; availability can vary by region.
- YouTube usage respects the free daily quota. If exhausted, the feature disables itself for the day.

## Project Structure
```
app/
  app.py
  config.py
  analysis/
    sentiment.py
    themes.py
  db/
    database.py
  harvesters/
    google_play.py
    reddit.py
    apple_app_store.py
    youtube.py
  services/
    company_validation.py
  ui/
    components.py
``` 