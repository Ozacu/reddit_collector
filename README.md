# Vancouver Reddit Sentiment Tracker

An end-to-end NLP pipeline that collects posts from Vancouver-focused subreddits, scores them with VADER sentiment analysis, and visualizes the results in an interactive dashboard. Covers **600+ posts** across **3 subreddits** and **8 topic categories**, with daily sentiment trends, engagement metrics, and controversy detection.

**[Live Dashboard →](https://ozacu.github.io/reddit_collector/reddit_sentiment_dashboard.html)**

---

## Pipeline Overview

```
Reddit Public JSON API
(r/vancouver · r/britishcolumbia · r/vancouverhousing)
              │
    reddit_collector.py
    (requests — paginate, parse, classify by topic)
              │
       data/raw/posts_raw.csv
              │
  reddit_sentiment_pipeline.py
  (VADER NLP — compound score, labels, feature engineering)
              │
       data/processed/
       ├── posts_sentiment.csv
       ├── topic_summary.csv
       └── daily_sentiment.csv
              │
  reddit_sentiment_dashboard.html
  (Chart.js — 10 interactive charts)
```

## Features

- **Auth-free collection** — hits Reddit's public JSON API with polite 2-second delays; no OAuth credentials required
- **Topic classification** — keyword-based classifier assigns each post to one of 8 categories (housing, transit, crime, cost of living, weather, community, development, general) on ingest
- **VADER sentiment scoring** — compound score from −1.0 to +1.0 per post, with positive/neutral/negative labels at the ±0.05 threshold
- **Feature engineering** — log-weighted engagement score, controversy proxy (high comments × low upvote ratio), viral flag (top 10% by score)
- **Aggregate exports** — daily sentiment trend with 7-day rolling average, and per-topic summaries with engagement and controversy metrics
- **Self-contained dashboard** — 10 Chart.js charts in a single HTML file; zero build step, zero backend

## Project Structure

```
├── reddit_collector.py           # Scrape Reddit public API, classify topics, export CSV
├── reddit_sentiment_pipeline.py  # VADER NLP, feature engineering, aggregate outputs
├── reddit_sentiment_dashboard.html  # Interactive Chart.js dashboard
├── data/
│   ├── raw/                      # Output of collector (gitignored)
│   └── processed/                # Output of pipeline (gitignored)
└── requirements.txt
```

## Getting Started

### Prerequisites

```bash
pip install -r requirements.txt
```

Dependencies: `pandas`, `numpy`, `requests`, `vaderSentiment`

### Run the pipeline

```bash
# 1. Collect posts from Reddit (live mode — hits the API)
python reddit_collector.py

# 2. Run VADER sentiment analysis and build aggregates
python reddit_sentiment_pipeline.py

# 3. Open the dashboard
start reddit_sentiment_dashboard.html   # Windows
open  reddit_sentiment_dashboard.html   # macOS
```

To run with synthetic data (no network access needed):

```python
# reddit_collector.py defaults to use_mock=True in __main__
python reddit_collector.py   # generates data/raw/posts_raw.csv with 600 synthetic posts
python reddit_sentiment_pipeline.py
```

## Key Findings

| Metric | Value |
|---|---|
| Total posts analyzed | 600 |
| Subreddits tracked | 3 |
| Avg compound sentiment | +0.065 (slightly positive) |
| Positive posts | 26.2% (157) |
| Neutral posts | 57.5% (345) |
| Negative posts | 16.3% (98) |
| Most negative topic | Crime (−0.158 avg) |
| Most positive topic | General (+0.289 avg) |
| Most controversial topic | Transit (19.5% controversy rate) |
| Most engaging topic | Housing (4.26 avg engagement) |

## Data Sources

- **Reddit Public JSON API** — read-only endpoint at `reddit.com/r/{subreddit}/new.json`; no authentication required
- Subreddits: [r/vancouver](https://www.reddit.com/r/vancouver), [r/britishcolumbia](https://www.reddit.com/r/britishcolumbia), [r/vancouverhousing](https://www.reddit.com/r/vancouverhousing)

Data is used for educational and portfolio purposes only.

## Tech Stack

| Layer | Technology |
|---|---|
| Collection | Python, requests |
| NLP | VADER SentimentIntensityAnalyzer |
| Transformation | pandas, numpy |
| Visualization | Chart.js, vanilla JS |

---

Built by [Oscar Castro](https://portfolio-oz.vercel.app)
