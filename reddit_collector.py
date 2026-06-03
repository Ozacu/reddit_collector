"""
Reddit Vancouver — Data Collector
===================================
Collects posts and comments from r/vancouver using Reddit's
public JSON API (no auth required for read-only access).

Subreddits tracked:
  - r/vancouver       → general city sentiment
  - r/britishcolumbia → provincial context
  - r/vancouverhousing → housing-specific

Output: data/raw/posts_raw.csv
"""

import time
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR  = BASE_DIR / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "VancouverSentimentTracker/1.0 (portfolio project; contact: oscar@example.com)"
}

SUBREDDITS = ["vancouver", "britishcolumbia", "vancouverhousing"]

TOPICS = {
    "housing":     ["rent", "housing", "condo", "eviction", "landlord", "mortgage", "afford"],
    "transit":     ["skytrain", "translink", "bus", "transit", "commute", "bike lane"],
    "weather":     ["rain", "snow", "fog", "sun", "storm", "heat dome", "wildfire"],
    "cost_of_living": ["groceries", "expensive", "cost of living", "inflation", "price"],
    "community":   ["neighbour", "community", "park", "event", "festival", "local"],
    "crime":       ["crime", "theft", "break in", "police", "safe", "unsafe", "downtown eastside"],
    "development": ["development", "construction", "rezoning", "highrise", "tower", "heritage"],
}


def classify_topic(title: str, text: str) -> str:
    combined = (title + " " + text).lower()
    for topic, keywords in TOPICS.items():
        if any(kw in combined for kw in keywords):
            return topic
    return "general"


def fetch_subreddit_posts(subreddit: str, limit: int = 100, after: str = None) -> list[dict]:
    """Fetch posts from a subreddit using the public JSON API."""
    url    = f"https://www.reddit.com/r/{subreddit}/new.json"
    params = {"limit": limit, "raw_json": 1}
    if after:
        params["after"] = after

    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {}).get("children", [])
    except Exception as e:
        print(f"  ✗ Error fetching r/{subreddit}: {e}")
        return []


def parse_post(child: dict, subreddit: str) -> dict:
    """Extract relevant fields from a raw Reddit post object."""
    d = child.get("data", {})
    created_utc = d.get("created_utc", 0)
    created_dt  = datetime.fromtimestamp(created_utc, tz=timezone.utc)

    title    = d.get("title", "")
    selftext = d.get("selftext", "")

    return {
        "post_id":       d.get("id", ""),
        "subreddit":     subreddit,
        "title":         title,
        "text":          selftext[:500],  # truncate long posts
        "author":        d.get("author", "[deleted]"),
        "score":         d.get("score", 0),
        "upvote_ratio":  d.get("upvote_ratio", 0.5),
        "num_comments":  d.get("num_comments", 0),
        "url":           f"https://reddit.com{d.get('permalink', '')}",
        "flair":         d.get("link_flair_text", ""),
        "created_utc":   created_utc,
        "created_date":  created_dt.strftime("%Y-%m-%d"),
        "created_hour":  created_dt.hour,
        "created_dow":   created_dt.strftime("%A"),
        "topic":         classify_topic(title, selftext),
        "collected_at":  datetime.now(tz=timezone.utc).isoformat(),
    }


def collect(pages_per_sub: int = 3, use_mock: bool = False) -> pd.DataFrame:
    """
    Main collection function.

    Args:
        pages_per_sub: How many pages (100 posts each) to fetch per subreddit.
        use_mock:      Generate synthetic data instead of hitting Reddit.
    """
    if use_mock:
        print("⚡ Mock mode — generating synthetic Reddit data")
        return _generate_mock()

    all_posts = []

    for sub in SUBREDDITS:
        print(f"\nCollecting r/{sub}...")
        after = None
        for page in range(pages_per_sub):
            children = fetch_subreddit_posts(sub, limit=100, after=after)
            if not children:
                break
            for child in children:
                all_posts.append(parse_post(child, sub))
            after = children[-1]["data"].get("name")
            print(f"  page {page+1}: {len(children)} posts")
            time.sleep(2)  # Reddit rate limit: ~30 req/min

    if not all_posts:
        print("⚠ No posts collected. Falling back to mock.")
        return _generate_mock()

    df = pd.DataFrame(all_posts).drop_duplicates(subset="post_id")
    path = RAW_DIR / "posts_raw.csv"
    df.to_csv(path, index=False)
    print(f"\n✓ {len(df)} posts saved → {path}")
    return df


def _generate_mock() -> pd.DataFrame:
    """Realistic synthetic Reddit Vancouver posts for demo/portfolio."""
    import random
    random.seed(42)

    topics_pool = list(TOPICS.keys()) + ["general"]
    flairs = ["Discussion", "News", "Photo", "Rant", "Question", "Meta", ""]

    title_templates = {
        "housing":        ["Anyone else's rent going up again?", "Landlord raising rent 25% — legal?",
                           "Just got evicted after 8 years", "Is it even possible to buy in Vancouver?",
                           "New condo building approved for {n} units in {hood}"],
        "transit":        ["SkyTrain delays AGAIN", "New bus lane on Broadway — thoughts?",
                           "Anyone else feel unsafe on transit lately?", "Translink raising fares again"],
        "cost_of_living": ["Groceries are insane right now", "Anyone else considering leaving Vancouver?",
                           "How do people actually afford to live here?", "Vancouver cost of living vs Toronto"],
        "crime":          ["Break-in on my street last night", "Car windows smashed again on {street}",
                           "Downtown Eastside getting worse?", "Feeling unsafe walking at night"],
        "weather":        ["Beautiful day today!", "This rain is never ending",
                           "Snow in April again smh", "Heat dome warnings issued for Metro Vancouver"],
        "community":      ["Best hidden gem restaurants in {hood}?", "Annual {hood} street festival this weekend",
                           "Neighbours organized a cleanup — so wholesome", "Lost cat in {hood} area"],
        "development":    ["Another highrise approved in {hood}", "Heritage building being demolished",
                           "New rezoning proposal for Commercial Drive", "Community meeting about {hood} development"],
        "general":        ["Vancouver is beautiful sometimes", "Random act of kindness today",
                           "What's everyone doing this weekend?", "PSA: farmers market open again"],
    }

    hoods   = ["Kitsilano", "Mount Pleasant", "Commercial Drive", "Gastown",
               "West End", "Fairview", "Strathcona", "East Van", "Burnaby"]
    streets = ["Granville St", "Broadway", "Hastings", "Commercial Dr", "Main St"]

    records = []
    base_ts = 1700000000

    for i in range(600):
        topic    = random.choice(topics_pool)
        titles   = title_templates.get(topic, title_templates["general"])
        title    = random.choice(titles).format(
            n    = random.randint(50, 400),
            hood = random.choice(hoods),
            street = random.choice(streets),
        )
        score    = int(random.expovariate(0.005))  # heavy-tailed like real Reddit
        created  = base_ts + random.randint(0, 60 * 24 * 3600)
        dt       = datetime.fromtimestamp(created, tz=timezone.utc)
        sub      = random.choice(SUBREDDITS)

        records.append({
            "post_id":      f"mock_{i:04d}",
            "subreddit":    sub,
            "title":        title,
            "text":         "",
            "author":       f"user_{random.randint(1000,9999)}",
            "score":        score,
            "upvote_ratio": round(random.uniform(0.5, 0.98), 2),
            "num_comments": random.randint(0, min(score // 3 + 1, 500)),
            "url":          f"https://reddit.com/r/{sub}/comments/mock_{i:04d}",
            "flair":        random.choice(flairs),
            "created_utc":  created,
            "created_date": dt.strftime("%Y-%m-%d"),
            "created_hour": dt.hour,
            "created_dow":  dt.strftime("%A"),
            "topic":        topic,
            "collected_at": datetime.now(tz=timezone.utc).isoformat(),
            "data_source":  "mock",
        })

    df = pd.DataFrame(records)
    path = RAW_DIR / "posts_raw.csv"
    df.to_csv(path, index=False)
    print(f"✓ Generated {len(df)} mock posts → {path}")
    return df


if __name__ == "__main__":
    df = collect(use_mock=True)
    print(f"\nShape: {df.shape}")
    print(df["topic"].value_counts())
