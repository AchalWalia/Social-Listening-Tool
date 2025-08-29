from __future__ import annotations

from typing import Dict, List, Optional

import praw

from app.config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
from app.db.database import insert_mentions


def _get_reddit_client() -> Optional[praw.Reddit]:
    if not (REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET and REDDIT_USER_AGENT):
        return None
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
        check_for_async=False,
    )


def _find_relevant_subreddit(reddit: praw.Reddit, company_name: str) -> Optional[str]:
    candidates = [
        company_name,
        company_name.replace(" ", ""),
        f"{company_name}app",
        f"{company_name}official",
    ]
    for name in candidates:
        try:
            sub = reddit.subreddit(name)
            _ = sub.subscribers
            return sub.display_name
        except Exception:
            continue
    # Fallback: search by keywords and pick the largest
    try:
        best = None
        best_subs = 0
        for sub in reddit.subreddits.search(company_name, limit=10):
            try:
                subs = int(getattr(sub, "subscribers", 0) or 0)
            except Exception:
                subs = 0
            if subs > best_subs:
                best_subs = subs
                best = sub.display_name
        return best
    except Exception:
        return None


def harvest_reddit(connection, company_id: int, company_name: str, max_posts: int = 200) -> int:
    reddit = _get_reddit_client()
    if reddit is None:
        return 0

    subreddit_name = _find_relevant_subreddit(reddit, company_name)
    if not subreddit_name:
        return 0

    sub = reddit.subreddit(subreddit_name)

    def _collect_posts(listing, limit):
        posts = []
        try:
            for post in listing(limit=limit):
                posts.append(post)
        except Exception:
            pass
        return posts

    hot_posts = _collect_posts(sub.hot, max_posts // 2)
    new_posts = _collect_posts(sub.new, max_posts // 2)

    rows: List[Dict] = []
    for post in hot_posts + new_posts:
        try:
            post.comments.replace_more(limit=0)
            comments = post.comments.list()
        except Exception:
            comments = []
        rows.append(
            {
                "source": "Reddit",
                "source_ref": subreddit_name,
                "content": f"[POST] {post.title}\n\n{post.selftext}",
                "author": str(post.author) if post.author else None,
                "date": str(post.created_utc),
                "rating": None,
                "url": f"https://www.reddit.com{post.permalink}",
            }
        )
        for c in comments:
            rows.append(
                {
                    "source": "Reddit",
                    "source_ref": subreddit_name,
                    "content": str(c.body),
                    "author": str(c.author) if c.author else None,
                    "date": str(c.created_utc),
                    "rating": None,
                    "url": f"https://www.reddit.com{post.permalink}",
                }
            )

    return insert_mentions(connection, company_id, rows) 