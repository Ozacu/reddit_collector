"""
Reddit Vancouver — Sentiment Pipeline
=======================================
Runs VADER sentiment analysis on post titles,
engineers features, and produces analysis-ready dataset.

Input:  data/raw/posts_raw.csv
Output: data/processed/posts_sentiment.csv
        data/processed/topic_summary.csv
        data/processed/daily_sentiment.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR  = BASE_DIR / "data" / "raw"
PROC_DIR = BASE_DIR / "data" / "processed"
PROC_DIR.mkdir(parents=True, exist_ok=True)

analyzer = SentimentIntensityAnalyzer()


def score_sentiment(text: str) -> dict:
    """Run VADER on a text string. Returns compound + labels."""
    if not text or str(text).strip() == "":
        return {"compound": 0.0, "pos": 0.0, "neu": 1.0, "neg": 0.0, "label": "neutral"}

    scores = analyzer.polarity_scores(str(text))
    compound = scores["compound"]

    if compound >= 0.05:
        label = "positive"
    elif compound <= -0.05:
        label = "negative"
    else:
        label = "neutral"

    return {
        "compound": round(compound, 4),
        "pos":      round(scores["pos"], 3),
        "neu":      round(scores["neu"], 3),
        "neg":      round(scores["neg"], 3),
        "label":    label,
    }


def run_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    """Apply VADER to title + text combined."""
    print("Running VADER sentiment analysis...")

    def score_row(row):
        combined = f"{row['title']} {row.get('text', '')}".strip()
        return score_sentiment(combined)

    scores = df.apply(score_row, axis=1, result_type="expand")
    df = pd.concat([df, scores.add_prefix("sentiment_")], axis=1)

    # Rename for convenience
    df.rename(columns={
        "sentiment_compound": "sentiment_score",
        "sentiment_label":    "sentiment",
    }, inplace=True)

    print(f"  Sentiment distribution:\n{df['sentiment'].value_counts().to_string()}")
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add engagement and derived fields."""
    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
    df["week"]         = df["created_date"].dt.to_period("W").astype(str)
    df["month"]        = df["created_date"].dt.to_period("M").astype(str)

    # Engagement score: weighted combo of score + comments
    df["engagement"] = (
        np.log1p(df["score"]) * 0.6 +
        np.log1p(df["num_comments"]) * 0.4
    ).round(3)

    # Controversy proxy: high comments but low score
    df["is_controversial"] = (
        (df["num_comments"] > df["num_comments"].quantile(0.75)) &
        (df["upvote_ratio"] < 0.7)
    ).astype(int)

    # Viral flag
    df["is_viral"] = (df["score"] > df["score"].quantile(0.9)).astype(int)

    return df


def build_topic_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate sentiment and engagement by topic."""
    grp = df.groupby("topic").agg(
        post_count        = ("post_id", "count"),
        avg_sentiment     = ("sentiment_score", "mean"),
        pct_positive      = ("sentiment", lambda x: (x == "positive").mean() * 100),
        pct_negative      = ("sentiment", lambda x: (x == "negative").mean() * 100),
        avg_score         = ("score", "mean"),
        avg_comments      = ("num_comments", "mean"),
        avg_engagement    = ("engagement", "mean"),
        controversial_pct = ("is_controversial", "mean"),
    ).reset_index()

    grp["avg_sentiment"]     = grp["avg_sentiment"].round(3)
    grp["pct_positive"]      = grp["pct_positive"].round(1)
    grp["pct_negative"]      = grp["pct_negative"].round(1)
    grp["avg_score"]         = grp["avg_score"].round(1)
    grp["avg_engagement"]    = grp["avg_engagement"].round(3)
    grp["controversial_pct"] = (grp["controversial_pct"] * 100).round(1)

    grp = grp.sort_values("avg_sentiment")
    return grp


def build_daily_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    """Daily sentiment trend."""
    daily = df.groupby("created_date").agg(
        posts         = ("post_id", "count"),
        avg_sentiment = ("sentiment_score", "mean"),
        pct_positive  = ("sentiment", lambda x: (x == "positive").mean() * 100),
        pct_negative  = ("sentiment", lambda x: (x == "negative").mean() * 100),
        avg_score     = ("score", "mean"),
    ).reset_index()

    daily["avg_sentiment"] = daily["avg_sentiment"].round(3)
    daily["pct_positive"]  = daily["pct_positive"].round(1)
    daily["pct_negative"]  = daily["pct_negative"].round(1)
    daily = daily.sort_values("created_date")

    # 7-day rolling average
    daily["sentiment_7d"] = daily["avg_sentiment"].rolling(7, min_periods=1).mean().round(3)
    return daily


def run_pipeline() -> dict:
    path = RAW_DIR / "posts_raw.csv"
    if not path.exists():
        print("⚠ No raw data found. Run collector.py first.")
        return {}

    df = pd.read_csv(path)
    print(f"Loaded {len(df)} raw posts")

    df = run_sentiment(df)
    df = engineer_features(df)
    df.to_csv(PROC_DIR / "posts_sentiment.csv", index=False)

    topic_summary = build_topic_summary(df)
    topic_summary.to_csv(PROC_DIR / "topic_summary.csv", index=False)

    daily = build_daily_sentiment(df)
    daily.to_csv(PROC_DIR / "daily_sentiment.csv", index=False)

    print(f"\n✓ Pipeline complete")
    print(f"  posts_sentiment.csv  → {len(df)} rows")
    print(f"  topic_summary.csv    → {len(topic_summary)} topics")
    print(f"  daily_sentiment.csv  → {len(daily)} days")

    return {"posts": df, "topics": topic_summary, "daily": daily}


if __name__ == "__main__":
    results = run_pipeline()
    if results:
        print("\n── Topic Sentiment (most negative first) ──")
        print(results["topics"][["topic","post_count","avg_sentiment","pct_positive","pct_negative"]].to_string(index=False))
