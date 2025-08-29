from __future__ import annotations

import time
from typing import Dict, List, Optional

import requests

from app.db.database import insert_mentions, upsert_app_profile

ITUNES_SEARCH = "https://itunes.apple.com/search"
REVIEWS_RSS = "https://itunes.apple.com/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json?l=en&cc=us"


def _search_apps(company_name: str, limit: int = 5) -> List[Dict]:
    try:
        resp = requests.get(
            ITUNES_SEARCH,
            params={"term": company_name, "entity": "software", "limit": limit},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])
    except Exception:
        return []


def _fetch_reviews_for_app(app_id: int, max_reviews: int = 500) -> List[Dict]:
    reviews: List[Dict] = []
    
    # Try multiple regions to find reviews
    regions = ['us', 'in', 'gb']  # US, India, UK
    
    for region in regions:
        print(f"🔍 Trying to fetch reviews from {region.upper()} store...")
        page = 1
        region_reviews = []
        
        while len(region_reviews) < max_reviews and page <= 10:  # Hard limit: 10 pages x 50 = 500
            try:
                # Use region-specific RSS URL
                url = f"https://itunes.apple.com/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json?l=en&cc={region}"
                resp = requests.get(url, timeout=15)
                if resp.status_code != 200:
                    break
                data = resp.json()
                entries = data.get("feed", {}).get("entry", [])
                
                # If no entries, try next page or region
                if not entries:
                    if page == 1:  # No reviews in this region at all
                        break
                    page += 1
                    continue
                
                # First entry is app metadata; skip if it is a dict with 'im:name'
                if entries and isinstance(entries[0], dict) and entries[0].get("im:name"):
                    entries = entries[1:]
                    
                if not entries:  # No actual reviews after filtering
                    break
                
                for e in entries:
                    content = e.get("content", {}).get("label")
                    author = e.get("author", {}).get("name", {}).get("label")
                    date = e.get("updated", {}).get("label")
                    rating = e.get("im:rating", {}).get("label")
                    region_reviews.append(
                        {
                            "content": content,
                            "author": author,
                            "date": date,
                            "rating": float(rating) if rating else None,
                        }
                    )
                page += 1
                time.sleep(0.5)
            except Exception as e:
                print(f"⚠️ Error fetching from {region.upper()} store: {e}")
                break
        
        # If we found reviews in this region, use them
        if region_reviews:
            print(f"✅ Found {len(region_reviews)} reviews from {region.upper()} store")
            reviews = region_reviews
            break
        else:
            print(f"❌ No reviews found in {region.upper()} store")
    
    return reviews[:max_reviews]


def harvest_apple_app_store(connection, company_id: int, company_name: str, app_ids: Optional[List[str]] = None) -> int:
    """
    Harvest Apple App Store reviews for a company
    
    Args:
        connection: Database connection
        company_id: Company ID in database
        company_name: Company name for search
        app_ids: Optional list of specific Apple App Store IDs to target
        
    Returns:
        Number of reviews inserted
    """
    total_inserted = 0
    
    # If specific app IDs are provided (from website analysis), use them directly
    if app_ids:
        print(f"🎯 Using provided Apple App Store IDs: {app_ids}")
        target_apps = []
        
        # Fetch app details for each provided ID
        for app_id in app_ids:
            try:
                app_data = None
                # Try multiple regions to find the app
                regions = ['us', 'in', 'gb']  # US, India, UK
                
                for region in regions:
                    try:
                        resp = requests.get(
                            "https://itunes.apple.com/lookup",
                            params={"id": app_id, "country": region},
                            timeout=15
                        )
                        resp.raise_for_status()
                        data = resp.json()
                        results = data.get("results", [])
                        
                        if results:
                            app_data = results[0]
                            country_name = {"us": "US", "in": "India", "gb": "UK"}.get(region, region.upper())
                            print(f"✅ Found app: {app_data.get('trackName')} by {app_data.get('artistName')} (Available in {country_name})")
                            break
                    except Exception as region_error:
                        print(f"⚠️ Could not fetch from {region.upper()} store: {region_error}")
                        continue
                
                # If not found in regional stores, try without region
                if not app_data:
                    try:
                        resp = requests.get(
                            "https://itunes.apple.com/lookup",
                            params={"id": app_id},
                            timeout=15
                        )
                        resp.raise_for_status()
                        data = resp.json()
                        results = data.get("results", [])
                        
                        if results:
                            app_data = results[0]
                            print(f"✅ Found app: {app_data.get('trackName')} by {app_data.get('artistName')}")
                    except Exception as global_error:
                        print(f"⚠️ Could not fetch from global store: {global_error}")
                
                if app_data:
                    target_apps.append({
                        "trackId": int(app_id),
                        "trackName": app_data.get("trackName"),
                        "averageUserRating": app_data.get("averageUserRating"),
                        "userRatingCount": app_data.get("userRatingCount"),
                        "artistName": app_data.get("artistName")
                    })
                else:
                    print(f"❌ No app found for ID: {app_id} in any region")
                    
            except Exception as e:
                print(f"❌ Error fetching app details for ID {app_id}: {e}")
                continue
    else:
        # Fallback to search-based discovery
        print(f"🔍 Searching for apps by company name: {company_name}")
        target_apps = _search_apps(company_name, limit=5)
    
    if not target_apps:
        print(f"❌ No Apple App Store apps found for {company_name}")
        return 0
    
    print(f"📱 Found {len(target_apps)} Apple App Store app(s)")
    
    # Process each app
    for app in target_apps:
        app_id = app.get("trackId")
        if not app_id:
            continue
            
        print(f"📥 Fetching reviews for app ID: {app_id}")
        
        # Store app profile information
        title = app.get("trackName")
        rating = app.get("averageUserRating")
        ratings_count = app.get("userRatingCount")
        upsert_app_profile(
            connection,
            company_id,
            platform="Apple App Store",
            app_id=str(app_id),
            title=title,
            rating=float(rating) if rating is not None else None,
            ratings_count=int(ratings_count) if ratings_count is not None else None,
            url=f"https://apps.apple.com/app/id{app_id}",
        )

        rows: List[Dict] = []
        for r in _fetch_reviews_for_app(int(app_id), max_reviews=500):
            rows.append(
                {
                    "source": "Apple App Store",
                    "source_ref": str(app_id),
                    "content": r.get("content"),
                    "author": r.get("author"),
                    "date": r.get("date"),
                    "rating": r.get("rating"),
                    "url": f"https://apps.apple.com/app/id{app_id}",
                }
            )
        inserted = insert_mentions(connection, company_id, rows)
        total_inserted += inserted
        print(f"✅ Inserted {inserted} reviews for {title}")
        
    return total_inserted 