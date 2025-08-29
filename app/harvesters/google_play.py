from __future__ import annotations

import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from google_play_scraper import app as gp_app, reviews as gp_reviews, search, Sort

from app.db.database import insert_mentions, upsert_app_profile
from app.harvesters.app_mapping import app_mapping_service

# Prefer global coverage for details/review counts
# Try multiple key stores to improve accuracy of ratings and review totals
DEFAULT_COUNTRIES: List[str] = ["us", "ae", "in", "gb", "sa", "kw"]


def _run_with_timeout(target, args: Tuple, kwargs: Dict, timeout_seconds: int):
    result: Dict[str, object] = {"value": None, "error": None}

    def _runner():
        try:
            result["value"] = target(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            result["error"] = e

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join(timeout_seconds)
    if thread.is_alive():
        return None, TimeoutError(f"operation timed out after {timeout_seconds}s")
    return result["value"], result["error"]


def _find_related_app_ids(company_name: str, max_results: int = 5, timeout_seconds: int = 15) -> List[str]:
    """
    Enhanced app discovery using intelligent mapping service.
    """
    app_ids: List[str] = []
    
    # Step 1: Try known package IDs first
    known_packages = app_mapping_service.get_google_play_packages(company_name)
    if known_packages:
        print(f"Found {len(known_packages)} known packages for {company_name}")
        return known_packages[:max_results]
    
    # Step 2: Use intelligent search variations
    search_variations = app_mapping_service.generate_search_variations(company_name)
    known_developers = app_mapping_service.get_developer_names(company_name)
    
    for search_term in search_variations[:3]:  # Limit to top 3 variations
        for country in DEFAULT_COUNTRIES:
            value, _ = _run_with_timeout(
                search,
                args=(search_term,),
                kwargs={"lang": "en", "country": country},
                timeout_seconds=timeout_seconds,
            )
            if not value:
                continue
                
            results = list(value)[:max_results * 2]  # Get more results for filtering
            
            for r in results:
                developer: str = str(r.get("developer", ""))
                title: str = str(r.get("title", ""))
                app_id: str = str(r.get("appId", ""))
                
                # Use intelligent matching
                if app_mapping_service.is_likely_match(company_name, title, developer):
                    if app_id not in app_ids:
                        app_ids.append(app_id)
                        print(f"Matched app: {title} by {developer} ({app_id})")
                
                if len(app_ids) >= max_results:
                    break
            
            if len(app_ids) >= max_results:
                break
        
        if len(app_ids) >= max_results:
            break
    
    # Step 3: Fallback to original method if no intelligent matches
    if not app_ids:
        print(f"No intelligent matches found for {company_name}, falling back to basic search")
        company_lower = company_name.lower()
        for country in DEFAULT_COUNTRIES:
            value, _ = _run_with_timeout(
                search,
                args=(company_name,),
                kwargs={"lang": "en", "country": country},
                timeout_seconds=timeout_seconds,
            )
            if not value:
                continue
            results = list(value)[:max_results]
            for r in results:
                developer: str = str(r.get("developer", ""))
                title: str = str(r.get("title", ""))
                if company_lower in developer.lower() or company_lower in title.lower():
                    app_ids.append(str(r.get("appId")))
            if len(app_ids) >= max_results:
                break
    
    # Remove duplicates while preserving order
    seen = set()
    unique_ids: List[str] = []
    for a in app_ids:
        if a and a not in seen:
            unique_ids.append(a)
            seen.add(a)
    
    return unique_ids[:max_results]


def _fetch_reviews_limited(app_id: str, count: int = 200, timeout_seconds: int = 30) -> List[Dict]:
    for country in DEFAULT_COUNTRIES:
        value, _ = _run_with_timeout(
            gp_reviews,
            args=(app_id,),
            kwargs={"lang": "en", "country": country, "sort": Sort.NEWEST, "count": count},
            timeout_seconds=timeout_seconds,
        )
        if value:
            return [
                {
                    "content": r["content"],
                    "author": r["userName"],
                    "date": r["at"].strftime("%Y-%m-%d") if r["at"] else None,
                    "rating": float(r["score"]) if r["score"] else None,
                    "url": f"https://play.google.com/store/apps/details?id={app_id}",
                }
                for r in value[0]
            ]
    return []


def _fetch_app_details(app_id: str, timeout_seconds: int = 15) -> Optional[Dict]:
    """Fetch app details and prefer the highest ratings_count across regions."""
    best: Optional[Dict] = None
    best_count: int = -1
    for country in DEFAULT_COUNTRIES:
        value, _ = _run_with_timeout(
            gp_app,
            args=(app_id,),
            kwargs={"lang": "en", "country": country},
            timeout_seconds=timeout_seconds,
        )
        if not value:
            continue
        rating = float(value.get("score", 0)) if value.get("score") else None
        ratings_count_raw = value.get("reviews", 0)
        try:
            ratings_count = int(ratings_count_raw or 0)
        except Exception:
            ratings_count = 0
        details = {
            "title": value.get("title"),
            "rating": rating,
            "ratings_count": ratings_count,
            "url": f"https://play.google.com/store/apps/details?id={app_id}",
        }
        if ratings_count > best_count:
            best = details
            best_count = ratings_count
    return best


def harvest_google_play(connection, company_id: int, company_name: str, package_ids: Optional[List[str]] = None) -> int:
    """
    Enhanced Google Play harvester with intelligent app mapping.
    """
    if package_ids:
        # Use provided package IDs directly
        app_ids = package_ids
        print(f"Using provided package IDs: {app_ids}")
    else:
        # Use intelligent app discovery
        print(f"Discovering apps for company: {company_name}")
        app_ids = _find_related_app_ids(company_name, max_results=5)
        
        if not app_ids:
            print(f"No apps found for {company_name}")
            return 0
        
        print(f"Found {len(app_ids)} apps: {app_ids}")

    total_added = 0
    for app_id in app_ids:
        try:
            # Fetch app details for metadata
            app_details = _fetch_app_details(app_id)
            if app_details:
                upsert_app_profile(
                    connection,
                    company_id,
                    "Google Play",
                    app_id,
                    app_details["title"],
                    app_details["rating"],
                    app_details["ratings_count"],
                    app_details["url"],
                )
                print(f"Stored app profile: {app_details['title']} ({app_details['rating']}⭐)")

            # Fetch reviews
            reviews = _fetch_reviews_limited(app_id, count=200)
            if reviews:
                rows = [
                    {
                        "source": "Google Play",
                        "source_ref": app_id,
                        "content": r["content"],
                        "author": r["author"],
                        "date": r["date"],
                        "rating": r["rating"],
                        "url": r["url"],
                    }
                    for r in reviews
                ]
                added = insert_mentions(connection, company_id, rows)
                total_added += added
                print(f"Added {added} reviews from {app_id}")
            else:
                print(f"No reviews found for {app_id}")

        except Exception as e:
            print(f"Error processing app {app_id}: {e}")
            continue

    return total_added 