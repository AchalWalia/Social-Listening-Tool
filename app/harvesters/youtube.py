from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Dict, List, Optional

from googleapiclient.discovery import build

from app.config import BASE_DIR, YOUTUBE_API_KEY
from app.db.database import insert_mentions

QUOTA_FILE = BASE_DIR / ".youtube_quota.json"
DAILY_LIMIT = 10000
COST_SEARCH = 100
COST_COMMENT_THREADS = 1


def _load_quota_state() -> Dict:
    if QUOTA_FILE.exists():
        try:
            return json.loads(QUOTA_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_quota_state(state: Dict) -> None:
    try:
        QUOTA_FILE.write_text(json.dumps(state))
    except Exception:
        pass


def _remaining_quota() -> int:
    state = _load_quota_state()
    today = dt.date.today().isoformat()
    if state.get("date") != today:
        state = {"date": today, "used": 0}
        _save_quota_state(state)
        return DAILY_LIMIT
    return max(0, DAILY_LIMIT - int(state.get("used", 0)))


def _consume_quota(cost: int) -> bool:
    state = _load_quota_state()
    today = dt.date.today().isoformat()
    if state.get("date") != today:
        state = {"date": today, "used": 0}
    if int(state.get("used", 0)) + cost > DAILY_LIMIT:
        return False
    state["used"] = int(state.get("used", 0)) + cost
    _save_quota_state(state)
    return True


def harvest_youtube(connection, company_id: int, company_name: str, max_videos: int = 10) -> int:
    if not YOUTUBE_API_KEY:
        return 0

    if _remaining_quota() < COST_SEARCH or not _consume_quota(COST_SEARCH):
        # Over quota for the day
        return 0

    yt = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    search_resp = yt.search().list(
        q=company_name,
        type="video",
        part="id,snippet",
        maxResults=min(10, max_videos),
    ).execute()

    video_ids = [item["id"]["videoId"] for item in search_resp.get("items", [])]

    total_inserted = 0
    rows: List[Dict] = []
    for vid in video_ids:
        # Fetch top-level comments
        page_token: Optional[str] = None
        while True:
            if _remaining_quota() < COST_COMMENT_THREADS or not _consume_quota(COST_COMMENT_THREADS):
                break
            resp = yt.commentThreads().list(
                part="snippet",
                videoId=vid,
                maxResults=100,
                pageToken=page_token,
                textFormat="plainText",
                order="relevance",
            ).execute()
            for item in resp.get("items", []):
                snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                rows.append(
                    {
                        "source": "YouTube",
                        "source_ref": vid,
                        "content": snippet.get("textDisplay"),
                        "author": snippet.get("authorDisplayName"),
                        "date": snippet.get("publishedAt"),
                        "rating": None,
                        "url": f"https://www.youtube.com/watch?v={vid}",
                    }
                )
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
    total_inserted += insert_mentions(connection, company_id, rows)
    return total_inserted 